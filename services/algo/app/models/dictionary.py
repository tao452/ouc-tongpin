from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.normalization import normalize


class DictionaryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    word: str = Field(min_length=1, max_length=64)
    level: Literal["LOW", "MEDIUM", "HIGH"]
    aliases: list[str] = Field(default_factory=list, max_length=50)
    pinyin: bool = False
    allow_phrases: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("word")
    @classmethod
    def valid_word(cls, word):
        if not normalize(word):
            raise ValueError("Empty normalized word")
        return word

    @field_validator("aliases")
    @classmethod
    def valid_aliases(cls, aliases):
        if any(not normalize(word) or len(word) > 64 for word in aliases):
            raise ValueError("Invalid dictionary alias")
        return aliases

    @model_validator(mode="after")
    def valid_allow_phrases(self):
        variants = [normalize(value) for value in [self.word, *self.aliases]]
        for phrase in self.allow_phrases:
            token = normalize(phrase)
            if (len(phrase) > 128 or not token
                    or not any(variant in token and len(token) > len(variant)
                               for variant in variants)):
                raise ValueError("Allowed phrase must contain a longer context for this entry")
        return self
