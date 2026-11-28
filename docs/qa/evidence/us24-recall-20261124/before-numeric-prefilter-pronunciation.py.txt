"""Phrase-first, finite pronunciation mappings. No Cartesian heteronym expansion."""

import re

from pypinyin import Style, pinyin

MAX_READINGS = 8
MAX_SYLLABLES = 16
MAX_PINYIN_LENGTH = 64


def phrase_readings(word, readings=()):
    """Return bounded whole-phrase paths, never a product of character readings."""
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
    return choices


def numeric_tone_patterns(word, readings=(), tone_readings=()):
    """Respect contextual or explicitly mapped tones without enumerating products."""
    bases = phrase_readings(word, readings)
    paths = [[part[0] for part in pinyin(word, style=Style.TONE3, neutral_tone_with_five=True)]]
    for reading in bases[1:]:
        path = []
        for char, base in zip(word, reading, strict=True):
            choices = pinyin(char, style=Style.TONE3, heteronym=True,
                             neutral_tone_with_five=True)[0]
            path.append(next(t for t in choices if re.sub(r"[1-5]$", "", t) == base))
        paths.append(path)
    for value in tone_readings:
        path = value.split()
        if (len(path) != len(word) or any(not re.fullmatch(r"[a-z]+[1-5]", s) for s in path)
                or [s[:-1] for s in path] not in bases):
            raise ValueError("Explicit tones must map to a validated whole phrase")
        if path not in paths:
            paths.append(path)
    if len(paths) > MAX_READINGS:
        raise ValueError("Too many numeric tone readings")
    return tuple(numeric_tone_pattern(path) for path in paths)


def numeric_tone_pattern(syllables):
    return re.compile(r"(?<![a-z0-9_])" + r"[^\w]{0,8}".join(
        (re.escape(syllable[:-1]) + syllable[-1] + "?" if syllable[-1:] in "12345"
         else re.escape(syllable) + r"[1-5]?")
        for syllable in syllables) + r"(?![a-z0-9_])")


def pronunciation_keys(word, readings=(), aliases=()):
    """Return whole-phrase keys, validating explicitly requested alternative readings."""
    choices = phrase_readings(word, readings)
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
