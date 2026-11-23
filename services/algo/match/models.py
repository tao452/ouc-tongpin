from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

UnitFloat = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)


class Location(StrictModel):
    lat: Annotated[float, Field(ge=-90, le=90)]
    lng: Annotated[float, Field(ge=-180, le=180)]


class TimeSlot(StrictModel):
    # JSON RFC3339 strings are accepted; naive dates have no shared comparison meaning.
    model_config = ConfigDict(extra="forbid", frozen=True)
    start: datetime
    end: datetime

    @field_validator("start", "end", mode="before")
    @classmethod
    def datetime_or_rfc3339(cls, value):
        if not isinstance(value, (str, datetime)):
            raise ValueError("Use timezone-aware RFC3339 timestamps")
        return datetime.fromisoformat(value) if isinstance(value, str) else value

    @model_validator(mode="after")
    def valid_interval(self):
        if (self.start.tzinfo is None or self.end.tzinfo is None
                or self.start.utcoffset() is None or self.end.utcoffset() is None
                or self.end.astimezone(UTC) <= self.start.astimezone(UTC)):
            raise ValueError("Intervals need timezone-aware increasing endpoints")
        return self


class Profile(StrictModel):
    emotion_vector: Annotated[list[UnitFloat], Field(min_length=6, max_length=6)] | None = None
    interests: Annotated[list[Annotated[str, Field(min_length=1, max_length=32)]],
                         Field(max_length=32)] = Field(default_factory=list)
    availability: Annotated[list[TimeSlot], Field(max_length=16)] = Field(default_factory=list)
    location: Location | None = None


class Candidate(Profile):
    id: Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")]


class ScoreRequest(StrictModel):
    query: Profile
    candidate: Candidate | None = None
    candidates: Annotated[list[Candidate], Field(min_length=1, max_length=100)] | None = None

    @model_validator(mode="after")
    def unique_candidates(self):
        if (self.candidate is None) == (self.candidates is None):
            raise ValueError("Provide exactly one candidate or a candidates list")
        rows = self.items()
        if len({row.id for row in rows}) != len(rows):
            raise ValueError("Candidate IDs must be unique")
        return self

    def items(self):
        return self.candidates if self.candidates is not None else [self.candidate]


class Weights(StrictModel):
    emotion: UnitFloat
    interests: UnitFloat
    time: UnitFloat
    distance: UnitFloat

    @model_validator(mode="after")
    def unit_sum(self):
        if abs(sum(self.model_dump().values()) - 1) > 1e-9:
            raise ValueError("Weights must sum to one")
        return self


class ScoreConfig(StrictModel):
    feature_version: Annotated[str, Field(min_length=1, max_length=64)]
    weights_version: Annotated[str, Field(min_length=1, max_length=64)]
    weights: Weights
    distance_scale_m: Annotated[float, Field(gt=0, le=100_000)]
