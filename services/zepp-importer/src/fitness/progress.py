from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ProgressEvent:
    phase: str
    current: int
    total: int | None
    message: str = ""


ProgressCallback = Callable[[ProgressEvent], None]


def emit(on_progress: ProgressCallback | None, event: ProgressEvent) -> None:
    if on_progress is not None:
        on_progress(event)
