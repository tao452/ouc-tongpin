"""Narrow, auditable quotation templates; not general intent or crisis inference."""

import re
import unicodedata

from app.services.normalization import normalize
from app.services.pronunciation import MAX_PINYIN_LENGTH, MAX_SYLLABLES
from app.services.targeted_matching import TARGET_WINDOW, is_target_prefix

MAX_SHORT_QUOTE_LENGTH = 64
# One registered path: letters + tones + eight separators per syllable gap,
# with an optional existing target prefix. This is not an arbitrary text limit.
MAX_PINYIN_QUOTE_LENGTH = (MAX_PINYIN_LENGTH + MAX_SYLLABLES
                           + 8 * (MAX_SYLLABLES - 1) + TARGET_WINDOW)
_LONG_PINYIN_FORM = re.compile(
    rf"(?P<prefix>[\u3400-\u9fff]{{0,{TARGET_WINDOW}}})(?P<body>[a-z0-9][^\n]*)"
)

_QUOTES = (("“", "”"), ("「", "」"), ('"', '"'), ("'", "'"), ("‘", "’"))
_TEMPLATES = (
    (r"(?:举报|有人骂我|有人威胁我)[:：\s]*", r"[,，]?(?:请处理|我该怎么办|让我很害怕)"),
    (r"不要(?:再)?(?:对同学|对别人|对我)说", r""),
    (r"请不要说", r"伤害同学"),
    (r"(?:网络暴力讨论|语言科普)[:：\s]*", r"(?:是侮辱性表达|属于攻击性言论|是攻击表达)"),
)
_PATTERNS = tuple(
    re.compile(prefix + re.escape(left)
               + rf"(?P<quote>[^\n]{{1,{MAX_PINYIN_QUOTE_LENGTH}}}?)" + re.escape(right)
               + suffix)
    for prefix, suffix in _TEMPLATES for left, right in _QUOTES
)
_HELP = re.compile(r"我想(?P<quote>去死)[,，](?:请帮帮我|请陪我聊聊|但我想求助)")
_SELF_DIRECTED = re.compile(
    r"(?:我(?:(?:不|真的|现在)?想|不会|不要)[ \t]*"
    r"|(?<![a-z0-9_])wo3?[^\w]{0,8}xiang3?[^\w]{1,8})"
    r"(?P<quote>[^，,。！？!?;；\n]{1,32}?)[ \t]*[了吧啊呀]{0,2}[ \t]*"
    r"(?=[，,。！？!?;；\n]|$)"
)
_SELF_BLAME = re.compile(
    r"我(?:是不是|是)(?:个)?[ \t]*(?P<quote>[^，,。！？!?;；\n]{1,32}?)[了吧啊呀]{0,2}"
    r"[,，](?:请帮帮我|想找人聊聊|想求助)"
)
_DENIAL = re.compile(r"^我不会(?P<quote>[^，,。！？!?;；\n]{1,32})[。！!?]?$")
_CLAUSE_BREAKS = frozenset(",，。;；:：!?！？、—\r\n")


def context_view(text):
    """Preserve offsets; Latin/numeric internal dots remain syllable separators."""
    def latin(ch):
        return ch.isascii() and ch.isalnum()

    result = []
    for index, ch in enumerate(text):
        category = unicodedata.category(ch)
        if category in {"Zl", "Zp"} or category == "Cc" and ch != "\t":
            ch = "\n"
        elif ch == "." and not (index and index + 1 < len(text)
                                 and latin(text[index - 1]) and latin(text[index + 1])):
            ch = "。"
        result.append(ch)
    return "".join(result)


def has_clause_boundary(text):
    return any(ch in _CLAUSE_BREAKS for ch in context_view(text))


def bounded_long_pinyin(quote):
    """A longer quotation still needs a complete registered token afterward."""
    match = _LONG_PINYIN_FORM.fullmatch(quote)
    if (match is None or len(quote) > MAX_PINYIN_QUOTE_LENGTH
            or match["prefix"] and not is_target_prefix(match["prefix"])):
        return False
    body = match["body"]
    alphanumeric = [ch for ch in body if ch.isalnum()]
    return (len(alphanumeric) <= MAX_PINYIN_LENGTH + MAX_SYLLABLES
            and "_" not in body and all(ch.isascii() for ch in alphanumeric))


def context_spans(canonical, known_variants, known_patterns=(), known_targeted_quote=None,
                  self_directed_quote=None):
    """Only exempt a complete known token inside a finite context template."""
    known_patterns = tuple(known_patterns)
    canonical = context_view(canonical)
    spans = []
    known_cache = {}  # One invocation only; never retain user text between requests.

    def known(quote):
        if quote not in known_cache:
            known_cache[quote] = (
                (len(quote) <= MAX_SHORT_QUOTE_LENGTH or bounded_long_pinyin(quote))
                and (normalize(quote) in known_variants
                     or any(p.fullmatch(quote.strip()) for p in known_patterns)
                     or known_targeted_quote is not None and known_targeted_quote(quote)))
        return known_cache[quote]

    for pattern in (*_PATTERNS, _HELP):
        for match in pattern.finditer(canonical):
            if known(match["quote"]):
                spans.append(match.span("quote"))
    if self_directed_quote is not None:
        for kind, pattern in [("harm", _SELF_DIRECTED), ("blame", _SELF_BLAME),
                              ("denial", _DENIAL)]:
            for match in pattern.finditer(canonical):
                if self_directed_quote(kind, match["quote"].strip()):
                    spans.append(match.span("quote"))
    return spans
