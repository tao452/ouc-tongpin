from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.normalization import normalize


class DictionaryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    word: str = Field(min_length=1, max_length=64)
    level: Literal["LOW", "MEDIUM", "HIGH"]
    aliases: list[str] = Field(default_factory=list, max_length=50)
    pinyin: bool = False

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
