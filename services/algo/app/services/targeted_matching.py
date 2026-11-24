"""Bounded, explicit target grammar; deliberately not general intent inference."""

import re

from pypinyin import Style, pinyin

TARGET_WINDOW = 16
_TARGET = re.compile(
    r"(?:你们?|他们?|她们?|这人|那人|楼主|博主|室友|同学|有些人)"
    r"(?:真|就|是|个|这|种|死|太|纯|小|老|臭|破|还|一|的|只|条|像|简直|就是){0,8}$"
)
_HANZI = re.compile(r"[\u3400-\u9fff]+")


def has_target(text, left):
    return _TARGET.search(text[max(0, left - TARGET_WINDOW):left]) is not None


def latin_boundary(text, left, right, variant):
    """Latin aliases retain English/identifier boundaries before separator removal."""
    def latin(ch):
        return ch.isascii() and (ch.isalnum() or ch == "_")

    return (not (variant[0].isascii() and variant[0].isalnum()
                 and left and latin(text[left - 1]))
            and not (variant[-1].isascii() and variant[-1].isalnum()
                     and right < len(text) and latin(text[right])))


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
