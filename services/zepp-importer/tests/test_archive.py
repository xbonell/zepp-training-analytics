from pathlib import Path

from fitness.archive import RawArchive


def test_write_new_file(tmp_path: Path):
    arc = RawArchive(tmp_path)
    r = arc.write_bytes("heart-rate/2026-01-01.json", b'{"ok":true}')
    assert r.status == "written"
    assert r.path.read_bytes() == b'{"ok":true}'


def test_skip_identical(tmp_path: Path):
    arc = RawArchive(tmp_path)
    payload = b'{"a":1}'
    arc.write_bytes("activity-details/1.json", payload)
    r = arc.write_bytes("activity-details/1.json", payload)
    assert r.status == "skipped"


def test_conflict_sibling(tmp_path: Path):
    arc = RawArchive(tmp_path)
    arc.write_bytes("activity-details/1.json", b'{"a":1}')
    r = arc.write_bytes("activity-details/1.json", b'{"a":2}')
    assert r.status == "conflict"
    assert r.path.name.startswith("1.")
    assert r.path.suffix == ".json"
    assert (tmp_path / "activity-details" / "1.json").read_bytes() == b'{"a":1}'
