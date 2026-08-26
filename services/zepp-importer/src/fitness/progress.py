from __future__ import annotations

import sys
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator


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


PHASE_LABELS_SYNC = {
    "history": "Syncing activity history",
    "details": "Syncing activity details",
    "band_hr": "Syncing band HR",
}
PHASE_LABELS_NORMALIZE = {
    "lists": "Normalizing activities",
    "details": "Normalizing activity details",
    "band": "Normalizing band HR",
}


@contextmanager
def progress_callback(labels: dict[str, str]) -> Iterator[ProgressCallback | None]:
    if not sys.stderr.isatty():
        yield None
        return

    from rich.console import Console
    from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=Console(stderr=True),
    )
    task_ids: dict[str, int] = {}
    with progress:

        def _on_progress(event: ProgressEvent) -> None:
            label = labels.get(event.phase, event.phase)
            if event.phase not in task_ids:
                task_ids[event.phase] = progress.add_task(label, total=event.total)
            progress.update(
                task_ids[event.phase],
                completed=event.current,
                total=event.total,
                description=label,
            )

        yield _on_progress
