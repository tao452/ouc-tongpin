from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    text: str = Field(min_length=1, max_length=2000)

    @field_validator("text")
    @classmethod
    def nonblank(cls, text: str) -> str:
        if not text.strip():
            raise ValueError("text must not be blank")
        return text


class Hit(BaseModel):
    word: str
    level: Literal["LOW", "MEDIUM", "HIGH"]


class ModerationResponse(BaseModel):
    passed: bool
    normalized: str
    hits: list[Hit]
