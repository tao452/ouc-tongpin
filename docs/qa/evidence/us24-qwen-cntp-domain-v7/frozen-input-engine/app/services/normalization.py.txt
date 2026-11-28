import re
import unicodedata

from opencc import OpenCC

_converter = OpenCC("t2s")
_HANZI_RUN = re.compile(r"[\u3400-\u9fff\uf900-\ufaff\U00020000-\U000323af]+")


def canonicalize(text: str) -> str:
    """Keep separators for token boundaries while folding script, width and Latin tones."""
    text = unicodedata.normalize("NFKC", text).casefold()
    if _HANZI_RUN.search(text):
        # t2s keys contain Hanzi only. Keep full phrase context within each run;
        # avoid parse trees for Latin text and repeated runs in this invocation.
        converted = {}

        def convert_run(match):
            run = match.group()
            if run not in converted:
                converted[run] = _converter.convert(run)
            return converted[run]

        text = _HANZI_RUN.sub(convert_run, text)
    characters = []
    for character in text:
        decomposed = unicodedata.normalize("NFD", character)
        if (len(decomposed) > 1 and "a" <= decomposed[0] <= "z"
                and all(unicodedata.category(ch) == "Mn" for ch in decomposed[1:])):
            character = "v" if decomposed[0] == "u" and "\u0308" in decomposed else decomposed[0]
        characters.append(character)
    return "".join(characters)


def normalize(text: str) -> str:
    """Unify variants and ignore inserted punctuation and invisible separators."""
    text = canonicalize(text)
    return "".join(ch for ch in text if unicodedata.category(ch)[0] in {"L", "N"})
