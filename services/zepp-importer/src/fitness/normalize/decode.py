from __future__ import annotations


def decode_heart_rate(series: str) -> list[tuple[int, int]]:
    if not series or not series.strip():
        return []
    by_elapsed: dict[int, int] = {}
    elapsed = 0
    hr: int | None = None
    for raw in series.split(";"):
        seg = raw.strip()
        if not seg:
            continue
        parts = seg.split(",")
        if len(parts) != 2:
            raise ValueError(f"invalid heart_rate segment: {seg!r}")
        try:
            dt = int(parts[0])
            dv = int(parts[1])
        except ValueError as exc:
            raise ValueError(f"invalid heart_rate segment: {seg!r}") from exc
        elapsed += dt
        hr = dv if hr is None else hr + dv
        by_elapsed[elapsed] = hr
    return sorted(by_elapsed.items())
