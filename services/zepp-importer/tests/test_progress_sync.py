from datetime import date
from pathlib import Path

import json

from fitness.archive import RawArchive
from fitness.config import Settings
from fitness.progress import ProgressEvent
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


def test_sync_emits_history_details_band_progress(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("fitness.sync._utc_today", lambda: date(2023, 1, 1))
    settings = Settings(
        zepp_app_token="tok",
        zepp_user_id="uid",
        data_raw_dir=tmp_path,
    )
    events: list[ProgressEvent] = []
    run_sync(
        settings,
        FakeClient(),  # type: ignore[arg-type]
        RawArchive(tmp_path),
        SyncOptions(from_date=date(2023, 1, 1)),
        on_progress=events.append,
    )

    assert events[0] == ProgressEvent("history", 1, None, "start")
    detail_events = [e for e in events if e.phase == "details"]
    assert detail_events == [
        ProgressEvent("details", 1, 1, "1700000000"),
    ]
    band_events = [e for e in events if e.phase == "band_hr"]
    assert len(band_events) == 1
    assert band_events[0] == ProgressEvent("band_hr", 1, 1, "2023-01-01")
