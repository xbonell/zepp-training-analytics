import json
from datetime import date, datetime, timezone
from pathlib import Path

from fitness.archive import RawArchive
from fitness.config import Settings
from fitness.sync import SyncOptions, run_sync


class FakeClient:
    def __init__(self) -> None:
        self.history_calls: list[int | None] = []
        self.detail_calls: list[tuple[str, str]] = []
        self.hr_calls: list[tuple[str, str]] = []

    def get_history(self, from_track_id: int | None = None) -> bytes:
        self.history_calls.append(from_track_id)
        assert from_track_id is None
        return json.dumps(
            {
                "code": 1,
                "message": "success",
                "data": {
                    "next": 0,
                    "summary": [
                        {
                            "trackid": "1700000000",
                            "source": "run.mifit.huami.com",
                            "type": 8,
                        }
                    ],
                },
            }
        ).encode()

    def get_detail(self, track_id: str, source: str) -> bytes:
        self.detail_calls.append((track_id, source))
        return json.dumps({"code": 1, "data": {"trackid": int(track_id)}}).encode()

    def get_heart_rate(self, start: str, end: str) -> bytes:
        self.hr_calls.append((start, end))
        return json.dumps({"date": start, "bpm": [60, 61]}).encode()


def test_sync_archives_list_detail_and_hr(tmp_path: Path):
    settings = Settings(
        zepp_app_token="tok",
        zepp_user_id="uid",
        data_raw_dir=tmp_path,
    )
    client = FakeClient()
    archive = RawArchive(tmp_path)

    report = run_sync(
        settings,
        client,  # type: ignore[arg-type]
        archive,
        SyncOptions(from_date=date(2023, 1, 1), activity_id=None),
    )

    assert (tmp_path / "activity-lists" / "trackid-start.json").exists()
    assert (tmp_path / "activity-details" / "1700000000.json").exists()
    assert (tmp_path / "heart-rate" / "2023-01-01.json").exists()
    assert client.detail_calls == [("1700000000", "run.mifit.huami.com")]
    assert client.hr_calls[0] == ("2023-01-01", "2023-01-01")
    assert archive.read_meta() is not None
    assert report.details_written >= 1


class PaginatedClient(FakeClient):
    def get_history(self, from_track_id: int | None = None) -> bytes:
        self.history_calls.append(from_track_id)
        if from_track_id is None:
            return json.dumps(
                {
                    "data": {
                        "next": 22,
                        "summary": [{"trackid": "11", "source": "first"}],
                    }
                }
            ).encode()
        assert from_track_id == 22
        return json.dumps(
            {
                "data": {
                    "next": 0,
                    "summary": [{"trackid": "22", "source": "second"}],
                }
            }
        ).encode()


def test_sync_paginates_via_next_and_archives_each_raw_page(tmp_path: Path):
    client = PaginatedClient()
    archive = RawArchive(tmp_path)

    run_sync(
        Settings(data_raw_dir=tmp_path),
        client,  # type: ignore[arg-type]
        archive,
        SyncOptions(activity_id="22"),
    )

    assert client.history_calls == [None, 22]
    assert (tmp_path / "activity-lists" / "trackid-start.json").exists()
    assert (tmp_path / "activity-lists" / "trackid-22.json").exists()
    assert client.detail_calls == [("22", "second")]


def test_sync_skips_existing_detail_unless_activity_is_forced(tmp_path: Path):
    archive = RawArchive(tmp_path)
    archive.write_bytes("activity-details/1700000000.json", b"old")
    client = FakeClient()

    report = run_sync(
        Settings(data_raw_dir=tmp_path),
        client,  # type: ignore[arg-type]
        archive,
        SyncOptions(from_date=date(2023, 1, 1)),
    )

    assert client.detail_calls == []
    assert report.details_skipped == 1

    forced_client = FakeClient()
    forced_report = run_sync(
        Settings(data_raw_dir=tmp_path),
        forced_client,  # type: ignore[arg-type]
        archive,
        SyncOptions(from_date=date(2023, 1, 1), activity_id="1700000000"),
    )

    assert forced_client.detail_calls == [("1700000000", "run.mifit.huami.com")]
    assert forced_report.details_conflict == 1


class InvalidHistoryClient(FakeClient):
    def get_history(self, from_track_id: int | None = None) -> bytes:
        self.history_calls.append(from_track_id)
        return b"not-json"


def test_sync_archives_history_before_reporting_parse_error(tmp_path: Path):
    client = InvalidHistoryClient()
    archive = RawArchive(tmp_path)

    report = run_sync(
        Settings(data_raw_dir=tmp_path),
        client,  # type: ignore[arg-type]
        archive,
        SyncOptions(from_date=datetime.now(timezone.utc).date()),
    )

    assert (tmp_path / "activity-lists" / "trackid-start.json").read_bytes() == b"not-json"
    assert report.lists_written == 1
    assert any("history parse failed" in error for error in report.errors)
