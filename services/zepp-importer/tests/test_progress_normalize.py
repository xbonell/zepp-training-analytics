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


def test_normalize_emits_progress_for_unchanged_files_on_second_run(tmp_path: Path):
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
    database = tmp_path / "out.duckdb"
    first_events: list[ProgressEvent] = []
    run_normalize(raw, database, on_progress=first_events.append)
    second_events: list[ProgressEvent] = []

    report = run_normalize(raw, database, on_progress=second_events.append)

    assert report.activities_skipped == 2
    assert second_events == first_events
    assert [event.phase for event in second_events] == ["lists", "lists", "details"]
