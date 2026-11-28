import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.normalization import normalize


class PinyinPhrase(BaseModel):
    """One explicitly selected Hanzi alias, with finite whole-phrase readings."""

    model_config = ConfigDict(extra="forbid", strict=True)
    phrase: str = Field(min_length=2, max_length=16)
    readings: list[str] = Field(default_factory=list, max_length=7)
    tone_readings: list[str] = Field(default_factory=list, max_length=7)

    @field_validator("phrase")
    @classmethod
    def valid_phrase(cls, phrase):
        if not re.fullmatch(r"[\u3400-\u9fff]{2,16}", phrase):
            raise ValueError("Pinyin phrase must be a complete Hanzi alias")
        return phrase

    @field_validator("readings", "tone_readings")
    @classmethod
    def bounded_readings(cls, values):
        if any(not value or len(value) > 128 for value in values):
            raise ValueError("Alias phrase reading is too long or empty")
        return values


class DictionaryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    word: str = Field(min_length=1, max_length=64)
    level: Literal["LOW", "MEDIUM", "HIGH"]
    aliases: list[str] = Field(default_factory=list, max_length=50)
    targeted_aliases: list[str] = Field(default_factory=list, max_length=50)
    target_required: bool = False
    hanzi_homophone: bool = False
    pinyin: bool = False
    pinyin_tone_numbers: bool = False
    pinyin_tone_readings: list[str] = Field(default_factory=list, max_length=7)
    pinyin_readings: list[str] = Field(default_factory=list, max_length=7)
    pinyin_aliases: list[str] = Field(default_factory=list, max_length=6)
    pinyin_phrases: list[PinyinPhrase] = Field(default_factory=list, max_length=6)
    pinyin_allow_phrases: list[str] = Field(default_factory=list, max_length=20)
    allow_phrases: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("word")
    @classmethod
    def valid_word(cls, word):
        if not normalize(word):
            raise ValueError("Empty normalized word")
        return word

    @field_validator("aliases", "targeted_aliases")
    @classmethod
    def valid_aliases(cls, aliases):
        if any(not normalize(word) or len(word) > 64 for word in aliases):
            raise ValueError("Invalid dictionary alias")
        return aliases

    @model_validator(mode="after")
    def valid_allow_phrases(self):
        if ((self.pinyin_readings or self.pinyin_aliases or self.pinyin_allow_phrases
             or self.pinyin_phrases)
                and not self.pinyin):
            raise ValueError("Pinyin mappings require pinyin=true")
        if self.hanzi_homophone and not self.pinyin:
            raise ValueError("Hanzi homophones require pinyin=true")
        if self.pinyin_tone_numbers and not self.pinyin:
            raise ValueError("Numeric tone matching requires pinyin=true")
        if self.pinyin_tone_readings and not self.pinyin_tone_numbers:
            raise ValueError("Explicit tones require numeric tone matching")
        phrase_names = [normalize(value.phrase) for value in self.pinyin_phrases]
        if len(set(phrase_names)) != len(phrase_names):
            raise ValueError("Duplicate pinyin alias phrase")
        for value in self.pinyin_phrases:
            if value.phrase not in self.aliases or normalize(value.phrase) == normalize(self.word):
                raise ValueError("Pinyin phrase must map an existing distinct ordinary alias")
            if value.tone_readings and not self.pinyin_tone_numbers:
                raise ValueError("Alias phrase tones require numeric tone matching")
        targeted = [normalize(v) for v in self.targeted_aliases]
        if (len(set(targeted)) != len(targeted)
                or set(targeted) & {normalize(v) for v in [self.word, *self.aliases]}):
            raise ValueError("Duplicate targeted variant")
        if any(len(value) > 128 for value in self.pinyin_readings):
            raise ValueError("Reading is too long")
        variants = [normalize(value)
                    for value in [self.word, *self.aliases, *self.targeted_aliases]]
        for phrase in self.allow_phrases:
            token = normalize(phrase)
            if (len(phrase) > 128 or not token
                    or not any(variant in token and len(token) > len(variant)
                               for variant in variants)):
                raise ValueError("Allowed phrase must contain a longer context for this entry")
        return self
