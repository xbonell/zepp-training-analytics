"""OTF-style heart-rate zone math.

OTF publishes inclusive % MaxHR bands (Z1 50–60, Z2 61–70, …). This module
implements half-open float cutovers so boundary ties are unambiguous:

- below: pct < 50
- z1: 50 <= pct < 61
- z2: 61 <= pct < 71
- z3: 71 <= pct < 84
- z4: 84 <= pct < 92
- z5: pct >= 92 (including values above 100% MaxHR)
"""

from typing import Literal

ZoneId = Literal["below", "z1", "z2", "z3", "z4", "z5"]

ALL_ZONES: tuple[ZoneId, ...] = ("below", "z1", "z2", "z3", "z4", "z5")

# Published OTF % bands (inclusive ranges); assignment uses half-open cutovers above.
OTF_BANDS: list[tuple[ZoneId, int, int, str]] = [
    ("z1", 50, 60, "gray"),
    ("z2", 61, 70, "blue"),
    ("z3", 71, 83, "green"),
    ("z4", 84, 91, "orange"),
    ("z5", 92, 100, "red"),
]

BELOW_COLOR = "gray"


def assign_zone(hr: int, hrmax: float) -> ZoneId:
    if hrmax <= 0:
        raise ValueError("hrmax must be positive")
    pct = 100.0 * hr / hrmax
    if pct < 50:
        return "below"
    if pct < 61:
        return "z1"
    if pct < 71:
        return "z2"
    if pct < 84:
        return "z3"
    if pct < 92:
        return "z4"
    return "z5"


def bpm_boundaries(hrmax: float) -> dict[ZoneId, tuple[float, float]]:
    if hrmax <= 0:
        raise ValueError("hrmax must be positive")
    return {
        "below": (0.0, hrmax * 50 / 100),
        "z1": (hrmax * 50 / 100, hrmax * 61 / 100),
        "z2": (hrmax * 61 / 100, hrmax * 71 / 100),
        "z3": (hrmax * 71 / 100, hrmax * 84 / 100),
        "z4": (hrmax * 84 / 100, hrmax * 92 / 100),
        "z5": (hrmax * 92 / 100, hrmax),
    }


def suggest_hrmax(samples: list[int], percentile: float = 0.99) -> float | None:
    if not samples:
        return None
    sorted_samples = sorted(samples)
    idx = int(percentile * len(sorted_samples))
    if idx >= len(sorted_samples):
        idx = len(sorted_samples) - 1
    return float(sorted_samples[idx])


def time_in_zones(series: list[tuple[int, int]], hrmax: float) -> dict[ZoneId, float]:
    totals: dict[ZoneId, float] = {zone: 0.0 for zone in ALL_ZONES}
    if not series:
        return totals
    for i in range(len(series) - 1):
        elapsed_s, hr_bpm = series[i]
        duration = series[i + 1][0] - elapsed_s
        if duration <= 0:
            continue
        zone = assign_zone(hr_bpm, hrmax)
        totals[zone] += duration
    return totals


def splat_minutes(time_by_zone: dict[ZoneId, float]) -> float:
    return (time_by_zone.get("z4", 0.0) + time_by_zone.get("z5", 0.0)) / 60.0
