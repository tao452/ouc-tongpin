"""Phrase-first, finite pronunciation mappings. No Cartesian heteronym expansion."""

import re

from pypinyin import Style, pinyin

MAX_READINGS = 8
MAX_SYLLABLES = 16
MAX_PINYIN_LENGTH = 64


def pronunciation_keys(word, readings=(), aliases=()):
    """Return whole-phrase keys, validating explicitly requested alternative readings."""
    if not 1 <= len(word) <= MAX_SYLLABLES:
        raise ValueError("Pinyin phrase exceeds 16 characters")
    primary = [item[0] for item in pinyin(word, style=Style.NORMAL, heteronym=False)]
    choices = [primary]
    for reading in readings:
        syllables = reading.split()
        if len(syllables) != len(word):
            raise ValueError("Reading must map one syllable to each character")
        # Validate each manually selected reading; never enumerate their product.
        for character, syllable in zip(word, syllables, strict=True):
            options = pinyin(character, style=Style.NORMAL, heteronym=True)[0]
            if syllable not in options:
                raise ValueError("Reading is not a pronunciation of this character")
        if syllables not in choices:
            choices.append(syllables)
    if len(choices) > MAX_READINGS:
        raise ValueError("Too many phrase readings")
    keys = {"".join(value) for value in choices}
    # Numeric tones use the contextual whole-phrase reading only.
    keys.add("".join(item[0] for item in pinyin(word, style=Style.TONE3,
                                              neutral_tone_with_five=True)))
    keys.update(aliases)
    if any(not re.fullmatch(r"[a-z0-9]{4,64}", key) for key in keys):
        raise ValueError("Invalid or ambiguous short pinyin key")
    if len(keys) > MAX_READINGS * 2:
        raise ValueError("Too many pinyin keys")
    return tuple(sorted(keys))
