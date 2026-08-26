from pathlib import Path

from fitness.normalize.load import run_normalize
from fitness.progress import ProgressEvent


def test_normalize_emits_lists_and_details_progress(tmp_path: Path):
    raw = tmp_path / "raw"
    (raw / "activity-lists").mkdir(parents=True)
    (raw / "activity-details").mkdir(parents=True)
    fixtures = Path(__file__).parent / "fixtures"
    (raw / "activity-lists" / "trackid-start.json").write_bytes(
        (fixtures / "normalize_list.json").read_bytes()
    )
    (raw / "activity-details" / "1700000100.json").write_bytes(
        (fixtures / "normalize_detail.json").read_bytes()
    )
    events: list[ProgressEvent] = []
    run_normalize(raw, tmp_path / "out.duckdb", on_progress=events.append)

    list_events = [e for e in events if e.phase == "lists"]
    assert list_events == [
        ProgressEvent("lists", 1, 2, "1700000100"),
        ProgressEvent("lists", 2, 2, "1700001000"),
    ]

    detail_events = [e for e in events if e.phase == "details"]
    assert detail_events == [
        ProgressEvent("details", 1, 1, "1700000100"),
    ]
    assert not any(e.phase == "band" for e in events)
