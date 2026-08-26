from __future__ import annotations

# Confirmed against Zepp app labels for this account (2026-08-26).
SPORT_LABELS: dict[int, str] = {
    1: "Outdoor running",
    6: "Walking",
    9: "Outdoor Cycling",
    10: "Indoor Cycling",
    16: "Freestyle",
    22: "Hiking",
    24: "Indoor Fitness",
    40: "Indoor Walk",
}


def sport_label(sport_type: int | None) -> str:
    if sport_type is None:
        return "Unknown"
    return SPORT_LABELS.get(sport_type, f"Sport {sport_type}")
