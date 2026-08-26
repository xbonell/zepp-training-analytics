import json
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
import pytest

from fitness.archive import RawArchive
from fitness.client import ZeppAuthError
from fitness.config import Settings
from fitness.sync import SyncOptions, run_sync


class FakeClient:
    def __init__(self) -> None:
        self.history_calls: list[int | None] = []
        self.detail_calls: list[tuple[str, str]] = []
        self.band_data_calls: list[str] = []

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

    def get_band_data(self, day: str) -> bytes:
        self.band_data_calls.append(day)
        return json.dumps(
            {"code": 1, "message": "success", "data": [{"date_time": day, "data_hr": "QQ=="}]}
        ).encode()


def test_sync_archives_list_detail_and_hr(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("fitness.sync._utc_today", lambda: date(2023, 1, 1))
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
    assert (tmp_path / "band-data" / "2023-01-01.json").exists()
    assert client.detail_calls == [("1700000000", "run.mifit.huami.com")]
    assert client.band_data_calls[0] == "2023-01-01"
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


class AuthFailureClient(FakeClient):
    def get_history(self, from_track_id: int | None = None) -> bytes:
        raise ZeppAuthError("re-extract token")


def test_sync_propagates_auth_errors(tmp_path: Path):
    with pytest.raises(ZeppAuthError, match="re-extract"):
        run_sync(
            Settings(data_raw_dir=tmp_path),
            AuthFailureClient(),  # type: ignore[arg-type]
            RawArchive(tmp_path),
            SyncOptions(),
        )


class RepeatingCursorClient(FakeClient):
    def get_history(self, from_track_id: int | None = None) -> bytes:
        self.history_calls.append(from_track_id)
        return json.dumps(
            {
                "data": {
                    "next": 22,
                    "summary": [{"trackid": "22", "source": "run"}],
                }
            }
        ).encode()


def test_sync_stops_when_history_cursor_repeats(tmp_path: Path):
    client = RepeatingCursorClient()

    report = run_sync(
        Settings(data_raw_dir=tmp_path),
        client,  # type: ignore[arg-type]
        RawArchive(tmp_path),
        SyncOptions(activity_id="missing"),
    )

    assert client.history_calls == [None, 22]
    assert any("cursor repeated" in error for error in report.errors)


class EndlessHistoryClient(FakeClient):
    def get_history(self, from_track_id: int | None = None) -> bytes:
        self.history_calls.append(from_track_id)
        next_cursor = 1 if from_track_id is None else from_track_id + 1
        return json.dumps(
            {
                "data": {
                    "next": next_cursor,
                    "summary": [{"trackid": str(next_cursor), "source": "run"}],
                }
            }
        ).encode()


def test_sync_stops_at_history_page_limit(tmp_path: Path):
    client = EndlessHistoryClient()

    report = run_sync(
        Settings(data_raw_dir=tmp_path),
        client,  # type: ignore[arg-type]
        RawArchive(tmp_path),
        SyncOptions(activity_id="missing"),
    )

    assert len(client.history_calls) == 500
    assert any("page limit reached" in error for error in report.errors)


def test_sync_skips_existing_band_data_without_client_call(
    tmp_path: Path, monkeypatch
):
    monkeypatch.setattr("fitness.sync._utc_today", lambda: date(2023, 1, 1))
    archive = RawArchive(tmp_path)
    archive.write_bytes("band-data/2023-01-01.json", b"existing")
    client = FakeClient()

    report = run_sync(
        Settings(data_raw_dir=tmp_path),
        client,  # type: ignore[arg-type]
        archive,
        SyncOptions(from_date=date(2023, 1, 1), activity_id="missing"),
    )

    assert client.band_data_calls == []
    assert report.heart_rate_skipped == 1


def test_sync_caps_band_data_history_at_90_days(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("fitness.sync._utc_today", lambda: date(2023, 4, 10))
    client = FakeClient()

    run_sync(
        Settings(data_raw_dir=tmp_path),
        client,  # type: ignore[arg-type]
        RawArchive(tmp_path),
        SyncOptions(from_date=date(2020, 1, 1), activity_id="missing"),
    )

    assert len(client.band_data_calls) == 90
    assert client.band_data_calls[0] == "2023-01-11"


class OldHistoryClient(FakeClient):
    def get_history(self, from_track_id: int | None = None) -> bytes:
        self.history_calls.append(from_track_id)
        return json.dumps(
            {
                "data": {
                    "next": 22,
                    "summary": [{"trackid": "11", "source": "run"}],
                }
            }
        ).encode()


def test_sync_stops_history_when_page_is_older_than_from_date(
    tmp_path: Path, monkeypatch
):
    monkeypatch.setattr("fitness.sync._utc_today", lambda: date(2023, 1, 1))
    client = OldHistoryClient()

    run_sync(
        Settings(data_raw_dir=tmp_path),
        client,  # type: ignore[arg-type]
        RawArchive(tmp_path),
        SyncOptions(from_date=date(2023, 1, 1)),
    )

    assert client.history_calls == [None]
    assert (tmp_path / "activity-lists" / "trackid-start.json").exists()


class HttpFailureClient(FakeClient):
    def get_history(self, from_track_id: int | None = None) -> bytes:
        request = httpx.Request("GET", "https://example.test/users/secret/history")
        response = httpx.Response(503, request=request)
        raise httpx.HTTPStatusError(
            "503 for https://example.test/users/secret/history",
            request=request,
            response=response,
        )


def test_sync_metadata_sanitizes_http_error_urls(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("fitness.sync._utc_today", lambda: date(2023, 1, 1))

    report = run_sync(
        Settings(data_raw_dir=tmp_path),
        HttpFailureClient(),  # type: ignore[arg-type]
        RawArchive(tmp_path),
        SyncOptions(from_date=date(2023, 1, 1)),
    )

    assert report.errors == ["HTTP 503 on history"]
    metadata = (tmp_path / "_meta" / "last_sync.json").read_text()
    assert "secret" not in metadata
    assert "example.test" not in metadata
