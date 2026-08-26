from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


@dataclass(frozen=True)
class ArchiveResult:
    path: Path
    status: Literal["written", "skipped", "conflict"]


class RawArchive:
    """Immutable raw payload store.

    Raw payloads are never overwritten when content differs; conflicting writes
    create timestamped sibling files. Only ``_meta/`` files (e.g.
    ``last_sync.json``) may be overwritten via :meth:`write_meta`.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def write_bytes(self, relative: str, data: bytes) -> ArchiveResult:
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if target.read_bytes() == data:
                return ArchiveResult(path=target, status="skipped")
            stem = target.stem
            suffix = target.suffix
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            conflict = target.with_name(f"{stem}.{ts}{suffix}")
            conflict.write_bytes(data)
            return ArchiveResult(path=conflict, status="conflict")
        target.write_bytes(data)
        return ArchiveResult(path=target, status="written")

    def write_json_bytes(self, relative: str, data: bytes) -> ArchiveResult:
        return self.write_bytes(relative, data)

    def count_files(self, subdir: str | None = None) -> int:
        base = self.root if subdir is None else self.root / subdir
        if not base.exists():
            return 0
        return sum(1 for p in base.rglob("*") if p.is_file() and p.name != ".gitkeep")

    def write_meta(self, payload: dict[str, Any]) -> Path:
        path = self.root / "_meta" / "last_sync.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def read_meta(self) -> dict[str, Any] | None:
        path = self.root / "_meta" / "last_sync.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
