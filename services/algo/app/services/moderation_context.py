"""Narrow, auditable quotation templates; not general intent or crisis inference."""

import re

from app.services.normalization import normalize

_QUOTES = (("“", "”"), ("「", "」"), ('"', '"'))
_TEMPLATES = (
    (r"(?:举报|有人骂我|有人威胁我)[:：\s]*", r"[,，]?(?:请处理|我该怎么办|让我很害怕)"),
    (r"不要(?:再)?(?:对同学|对别人|对我)说", r""),
    (r"(?:网络暴力讨论|语言科普)[:：\s]*", r"(?:是侮辱性表达|属于攻击性言论)"),
)
_PATTERNS = tuple(
    re.compile(prefix + re.escape(left) + r"(?P<quote>[^\n]{1,64}?)" + re.escape(right)
               + suffix)
    for prefix, suffix in _TEMPLATES for left, right in _QUOTES
)
_HELP = re.compile(r"我想(?P<quote>去死)[,，](?:请帮帮我|请陪我聊聊|但我想求助)")


def context_spans(canonical, known_variants):
    """Only exempt a complete known token inside a finite context template."""
    spans = []
    for pattern in (*_PATTERNS, _HELP):
        for match in pattern.finditer(canonical):
            if normalize(match["quote"]) in known_variants:
                spans.append(match.span("quote"))
    return spans
