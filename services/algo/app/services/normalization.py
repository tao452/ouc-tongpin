import unicodedata

from opencc import OpenCC

_converter = OpenCC("t2s")


def normalize(text: str) -> str:
    """Unify width/case/script and ignore inserted punctuation and invisible separators."""
    text = _converter.convert(unicodedata.normalize("NFKC", text).casefold())
    return "".join(ch for ch in text if unicodedata.category(ch)[0] in {"L", "N"})
