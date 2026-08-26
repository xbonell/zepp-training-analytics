from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from fitness_api.zones import ZoneId


def _empty_zone_totals() -> dict[ZoneId, float]:
    return {
        "below": 0.0,
        "z1": 0.0,
        "z2": 0.0,
        "z3": 0.0,
        "z4": 0.0,
        "z5": 0.0,
    }


class ActivitySummary(BaseModel):
    activity_id: str
    sport_type: int | None
    sport_label: str
    source: str | None
    started_at: datetime
    ended_at: datetime | None
    duration_s: int | None
    distance_m: float | None
    calories: float | None
    avg_hr: float | None
    max_hr: int | None
    min_hr: int | None
    te: int | None
    exercise_load: int | None
    time_in_zone: dict[ZoneId, float] = Field(default_factory=_empty_zone_totals)
    splat_minutes_estimate: float = Field(
        default=0,
        description="Local estimate based on time in heart-rate zones 4 and 5.",
    )


class HeartRatePoint(BaseModel):
    elapsed_s: int
    hr_bpm: int
    zone: ZoneId | None


class ActivityDetail(ActivitySummary):
    hr_series: list[HeartRatePoint]


class AgeFormulaReferences(BaseModel):
    age: int
    fox_220_minus_age: float
    tanaka_208_minus_0_7_age: float


class ZonesResponse(BaseModel):
    hrmax: float | None
    source: Literal["override", "suggested", "none"]
    boundaries: dict[ZoneId, tuple[float, float]]
    colors: dict[ZoneId, str]
    age_formula_refs: AgeFormulaReferences | None = None


class SportTypeOption(BaseModel):
    sport_type: int
    label: str


class OverviewResponse(BaseModel):
    activity_count: int
    duration_s: int
    zone_mix: dict[ZoneId, float]
    splat_minutes_estimate: float = Field(
        description="Local estimate based on time in heart-rate zones 4 and 5."
    )
    peak_hr_bpm: int | None = Field(
        description="Highest positive workout sample HR in the selected period."
    )
    recent: list[ActivitySummary]
