"""Bounded, explicit target grammar; deliberately not general intent inference."""

import re
import unicodedata

from pypinyin import Style, pinyin

TARGET_WINDOW = 16
_TARGET = re.compile(
    r"(?:你们?|他们?|她们?|这人|那人|楼主|博主|室友|同学|有些人)"
    r"(?:真|就|是|个|这|种|死|太|纯|小|老|臭|破|还|一|的|只|条|像|简直|就是){0,8}$"
)
_HANZI = re.compile(r"[\u3400-\u9fff]+")


def has_target(text, left):
    return _TARGET.search(text[max(0, left - TARGET_WINDOW):left]) is not None


def is_target_prefix(prefix):
    return len(prefix) <= TARGET_WINDOW and _TARGET.fullmatch(prefix) is not None


def _identifier_letter(ch):
    if ch.isascii():
        return ch.isalnum()
    if "\u3400" <= ch <= "\u9fff" or unicodedata.category(ch)[0] not in {"L", "N"}:
        return False
    # Chinese text may adjoin a pinyin token, including extension ideographs.
    return not unicodedata.name(ch, "").startswith(
        ("CJK UNIFIED IDEOGRAPH", "CJK COMPATIBILITY IDEOGRAPH"))


def latin_boundary(text, left, right, variant):
    """Latin and registered visual aliases preserve Unicode identifier boundaries."""
    return (not (_identifier_letter(variant[0]) and left
                 and (text[left - 1] == "_" or _identifier_letter(text[left - 1])))
            and not (_identifier_letter(variant[-1]) and right < len(text)
                     and (text[right] == "_" or _identifier_letter(text[right]))))


def homophone_spans(text, trie, check_budget):
    """One contextual reading per Hanzi; no heteronym products or fuzzy edits.

    Each run has one syllable per character. Traversal is bounded by the compiled
    phrase trie (at most 16 syllables); punctuation never joins separate runs.
    """
    reading_cache = {}  # Request-local: no user text is retained between requests.
    for run in _HANZI.finditer(text):
        check_budget()
        for start in range(len(run.group())):
            if start % 16 == 0:
                check_budget()
            left = run.start() + start
            if not has_target(text, left):
                continue
            # Only read the bounded candidate window, rather than a 2000-Hanzi run.
            window = run.group()[start:start + 16]
            if window not in reading_cache:
                reading_cache[window] = pinyin(window, style=Style.NORMAL, heteronym=False)
            readings = reading_cache[window]
            if len(readings) != len(window):
                continue
            syllables = [r[0] for r in readings]
            node = trie
            for end, syllable in enumerate(syllables):
                node = node.get(syllable)
                if node is None:
                    break
                if "" in node:
                    yield left, left + end + 1, node[""]
