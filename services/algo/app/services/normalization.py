import unicodedata

from opencc import OpenCC

_converter = OpenCC("t2s")


def canonicalize(text: str) -> str:
    """Keep separators for token boundaries while folding script, width and Latin tones."""
    text = _converter.convert(unicodedata.normalize("NFKC", text).casefold())
    characters = []
    for character in text:
        decomposed = unicodedata.normalize("NFD", character)
        if (len(decomposed) > 1 and "a" <= decomposed[0] <= "z"
                and all(unicodedata.category(ch) == "Mn" for ch in decomposed[1:])):
            character = decomposed[0]
        characters.append(character)
    return "".join(characters)


def normalize(text: str) -> str:
    """Unify variants and ignore inserted punctuation and invisible separators."""
    text = canonicalize(text)
    return "".join(ch for ch in text if unicodedata.category(ch)[0] in {"L", "N"})
