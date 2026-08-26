from datetime import date, datetime
from zoneinfo import ZoneInfo

import duckdb
from fastapi.testclient import TestClient

import fitness_api.main as main_module
from fitness_api.config import Settings
from fitness_api.main import create_app
from fitness_api.queries import suggested_hrmax


def seed_database(path):
    with duckdb.connect(str(path)) as conn:
        conn.execute(
            """
            CREATE TABLE activities (
              activity_id VARCHAR PRIMARY KEY,
              sport_type INTEGER,
              source VARCHAR,
              bind_device VARCHAR,
              started_at TIMESTAMPTZ,
              ended_at TIMESTAMPTZ,
              duration_s INTEGER,
              distance_m DOUBLE,
              calories DOUBLE,
              avg_hr DOUBLE,
              max_hr INTEGER,
              min_hr INTEGER,
              te INTEGER,
              exercise_load INTEGER,
              list_raw_file VARCHAR,
              detail_raw_file VARCHAR,
              list_content_sha256 VARCHAR,
              detail_content_sha256 VARCHAR
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE activity_samples (
              activity_id VARCHAR,
              elapsed_s INTEGER,
              hr_bpm INTEGER,
              detail_raw_file VARCHAR,
              detail_content_sha256 VARCHAR,
              PRIMARY KEY (activity_id, elapsed_s)
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO activities VALUES (
              ?, ?, 'zepp', 'watch', ?, ?, ?, ?, ?, ?, ?, ?, 3, 42,
              'list.json', 'detail.json', 'list-sha', 'detail-sha'
            )
            """,
            [
                (
                    "run-1",
                    1,
                    "2026-08-24T06:00:00Z",
                    "2026-08-24T06:02:00Z",
                    120,
                    1000.0,
                    100.0,
                    130.0,
                    150,
                    100,
                ),
                (
                    "ride-1",
                    2,
                    "2026-08-25T18:00:00Z",
                    "2026-08-25T18:03:00Z",
                    180,
                    3000.0,
                    150.0,
                    140.0,
                    160,
                    110,
                ),
            ],
        )
        conn.executemany(
            "INSERT INTO activity_samples VALUES (?, ?, ?, 'detail.json', 'sha')",
            [
                ("run-1", 0, 100),
                ("run-1", 60, 140),
                ("run-1", 120, 150),
                ("ride-1", 0, 110),
                ("ride-1", 60, 150),
                ("ride-1", 120, 160),
                ("ride-1", 180, 160),
            ],
        )


def make_client(tmp_path):
    db_path = tmp_path / "zepp.duckdb"
    seed_database(db_path)
    settings = Settings(
        duckdb_path=db_path,
        profile_path=tmp_path / "profile.json",
        _env_file=None,
    )
    return TestClient(create_app(settings))


def make_client_without_database(tmp_path):
    settings = Settings(
        duckdb_path=tmp_path / "missing.duckdb",
        profile_path=tmp_path / "profile.json",
        _env_file=None,
    )
    return TestClient(create_app(settings))


def test_suggested_hrmax_uses_duckdb_quantile_and_rounds_for_display(tmp_path):
    db_path = tmp_path / "quantile.duckdb"
    with duckdb.connect(str(db_path)) as conn:
        conn.execute("CREATE TABLE activity_samples (hr_bpm INTEGER)")
        conn.executemany(
            "INSERT INTO activity_samples VALUES (?)",
            [(100,), (183,)],
        )

    assert suggested_hrmax(db_path) == 182.2


def test_data_endpoints_return_actionable_503_without_database(tmp_path):
    client = make_client_without_database(tmp_path)

    for path in ("/api/overview", "/api/activities", "/api/activities/run-1"):
        response = client.get(path)
        assert response.status_code == 503
        assert response.json() == {
            "detail": "Activity database unavailable; run `fitness normalize` first"
        }


def test_zones_remains_available_without_database(tmp_path):
    client = make_client_without_database(tmp_path)
    client.put(
        "/api/settings/profile",
        json={"birth_date": "1990-01-01", "theme_preference": "system"},
    )

    response = client.get("/api/zones")

    assert response.status_code == 200
    payload = response.json()
    assert payload["hrmax"] is None
    assert payload["source"] == "none"
    assert payload["boundaries"] == {}
    assert payload["age_formula_refs"] is not None


def test_zones_resolves_suggested_hrmax_and_age_references(tmp_path):
    client = make_client(tmp_path)
    client.put(
        "/api/settings/profile",
        json={"birth_date": "1990-01-01", "theme_preference": "system"},
    )

    payload = client.get("/api/zones").json()

    age = date.today().year - 1990
    assert payload["hrmax"] == 160.0
    assert payload["source"] == "suggested"
    assert payload["boundaries"]["z4"] == [134.4, 147.2]
    assert payload["colors"] == {
        "below": "gray",
        "z1": "gray",
        "z2": "blue",
        "z3": "green",
        "z4": "orange",
        "z5": "red",
    }
    assert payload["age_formula_refs"] == {
        "age": age,
        "fox_220_minus_age": 220 - age,
        "tanaka_208_minus_0_7_age": 208 - 0.7 * age,
    }


def test_zones_rounds_resolved_hrmax_to_one_decimal(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "suggested_hrmax", lambda path: 183.27999999999997)
    client = make_client(tmp_path)

    payload = client.get("/api/zones").json()

    assert payload["hrmax"] == 183.3


def test_zones_uses_madrid_date_for_age(tmp_path, monkeypatch):
    client = make_client(tmp_path)

    class UtcDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 8, 26)

    class MadridDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            assert tz == ZoneInfo("Europe/Madrid")
            return cls(2026, 8, 27, 0, 30, tzinfo=tz)

    monkeypatch.setattr(main_module, "date", UtcDate)
    monkeypatch.setattr(main_module, "datetime", MadridDateTime, raising=False)
    client.put("/api/settings/profile", json={"birth_date": "2000-08-27"})

    payload = client.get("/api/zones").json()

    assert payload["age_formula_refs"]["age"] == 26


def test_zones_prefers_profile_override(tmp_path):
    client = make_client(tmp_path)
    client.put("/api/settings/profile", json={"hrmax_override": 200})

    payload = client.get("/api/zones").json()

    assert payload["hrmax"] == 200.0
    assert payload["source"] == "override"


def test_activities_filters_by_inclusive_dates_and_sport(tmp_path):
    client = make_client(tmp_path)

    response = client.get(
        "/api/activities",
        params={"from": "2026-08-25", "to": "2026-08-25", "sport_type": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [activity["activity_id"] for activity in payload] == ["ride-1"]
    assert payload[0]["duration_s"] == 180
    assert payload[0]["started_at"] == "2026-08-25T20:00:00+02:00"


def test_activity_summaries_preserve_zone_totals_and_splats(tmp_path):
    client = make_client(tmp_path)

    payload = client.get("/api/activities", params={"to": "2026-08-24"}).json()

    assert payload[0]["activity_id"] == "run-1"
    assert payload[0]["time_in_zone"] == {
        "below": 0.0,
        "z1": 0.0,
        "z2": 60.0,
        "z3": 0.0,
        "z4": 60.0,
        "z5": 0.0,
    }
    assert payload[0]["splat_minutes_estimate"] == 1.0


def test_activity_summaries_default_to_empty_zones_without_hrmax(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(main_module, "_resolved_hrmax", lambda settings: (None, "none"))
    client = make_client(tmp_path)

    payload = client.get("/api/activities", params={"to": "2026-08-24"}).json()

    assert payload[0]["time_in_zone"] == {
        "below": 0.0,
        "z1": 0.0,
        "z2": 0.0,
        "z3": 0.0,
        "z4": 0.0,
        "z5": 0.0,
    }
    assert payload[0]["splat_minutes_estimate"] == 0.0


def test_activity_detail_has_zoned_hr_series_and_estimated_splats(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/api/activities/run-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["hr_series"] == [
        {"elapsed_s": 0, "hr_bpm": 100, "zone": "z2"},
        {"elapsed_s": 60, "hr_bpm": 140, "zone": "z4"},
        {"elapsed_s": 120, "hr_bpm": 150, "zone": "z5"},
    ]
    assert payload["time_in_zone"] == {
        "below": 0.0,
        "z1": 0.0,
        "z2": 60.0,
        "z3": 0.0,
        "z4": 60.0,
        "z5": 0.0,
    }
    assert payload["splat_minutes_estimate"] == 1.0
    assert client.get("/api/activities/missing").status_code == 404


def test_overview_aggregates_all_activity_samples_and_recent(tmp_path):
    client = make_client(tmp_path)

    payload = client.get("/api/overview").json()

    assert payload["activity_count"] == 2
    assert payload["duration_s"] == 300
    assert payload["zone_mix"] == {
        "below": 0.0,
        "z1": 0.0,
        "z2": 120.0,
        "z3": 0.0,
        "z4": 60.0,
        "z5": 120.0,
    }
    assert payload["splat_minutes_estimate"] == 3.0
    assert [activity["activity_id"] for activity in payload["recent"]] == [
        "ride-1",
        "run-1",
    ]


def test_overview_filters_totals_zones_splats_and_recent_by_period(tmp_path):
    client = make_client(tmp_path)

    response = client.get(
        "/api/overview",
        params={"from": "2026-08-24", "to": "2026-08-24"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["activity_count"] == 1
    assert payload["duration_s"] == 120
    assert payload["zone_mix"] == {
        "below": 0.0,
        "z1": 0.0,
        "z2": 60.0,
        "z3": 0.0,
        "z4": 60.0,
        "z5": 0.0,
    }
    assert payload["splat_minutes_estimate"] == 1.0
    assert [activity["activity_id"] for activity in payload["recent"]] == ["run-1"]
    assert payload["recent"][0]["time_in_zone"]["z4"] == 60.0
    assert payload["recent"][0]["splat_minutes_estimate"] == 1.0


def test_profile_endpoints_round_trip(tmp_path):
    client = make_client(tmp_path)
    profile = {
        "sex": "female",
        "birth_date": "1990-05-17",
        "resting_hr": 52,
        "hrmax_override": 188,
        "theme_preference": "dark",
        "display_timezone": "Europe/Madrid",
    }

    put_response = client.put("/api/settings/profile", json=profile)

    assert put_response.status_code == 200
    assert put_response.json() == profile
    assert client.get("/api/settings/profile").json() == profile


def test_profile_rejects_non_positive_hrmax_override(tmp_path):
    client = make_client(tmp_path)

    for override in (0, -1):
        response = client.put(
            "/api/settings/profile",
            json={"hrmax_override": override},
        )

        assert response.status_code == 422
