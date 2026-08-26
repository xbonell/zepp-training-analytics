from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from fitness_api.config import Settings
from fitness_api.db import duckdb_available
from fitness_api.profile import Profile, load_profile, save_profile
from fitness_api.queries import (
    all_activity_samples,
    get_activity,
    get_activity_samples,
    list_activities,
    overview_totals,
    suggested_hrmax,
)
from fitness_api.schemas import (
    ActivityDetail,
    ActivitySummary,
    HeartRatePoint,
    OverviewResponse,
    ZonesResponse,
)
from fitness_api.zones import (
    BELOW_COLOR,
    OTF_BANDS,
    assign_zone,
    bpm_boundaries,
    splat_minutes,
    time_in_zones,
)


def _resolved_hrmax(
    settings: Settings,
) -> tuple[float | None, Literal["override", "suggested", "none"]]:
    override = load_profile(settings.profile_path).hrmax_override
    if override is not None:
        return float(override), "override"
    suggestion = suggested_hrmax(settings.duckdb_path)
    if suggestion is not None:
        return suggestion, "suggested"
    return None, "none"


def _empty_zone_totals() -> dict:
    return time_in_zones([], 1.0)


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()
    app = FastAPI(title="Zepp Training Analytics API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[app_settings.cors_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str | bool]:
        return {
            "status": "ok",
            "duckdb": duckdb_available(app_settings.duckdb_path),
        }

    @app.get("/api/settings/profile", response_model=Profile)
    def get_profile() -> Profile:
        return load_profile(app_settings.profile_path)

    @app.put("/api/settings/profile", response_model=Profile)
    def put_profile(profile: Profile) -> Profile:
        save_profile(profile, app_settings.profile_path)
        return profile

    @app.get("/api/zones", response_model=ZonesResponse)
    def zones() -> ZonesResponse:
        profile = load_profile(app_settings.profile_path)
        hrmax, source = _resolved_hrmax(app_settings)
        colors = {"below": BELOW_COLOR}
        colors.update({zone: color for zone, _, _, color in OTF_BANDS})
        age_formula_refs = None
        if profile.birth_date is not None:
            today = datetime.now(ZoneInfo("Europe/Madrid")).date()
            age = today.year - profile.birth_date.year - (
                (today.month, today.day)
                < (profile.birth_date.month, profile.birth_date.day)
            )
            age_formula_refs = {
                "age": age,
                "fox_220_minus_age": 220 - age,
                "tanaka_208_minus_0_7_age": 208 - 0.7 * age,
            }
        return ZonesResponse(
            hrmax=hrmax,
            source=source,
            boundaries=bpm_boundaries(hrmax) if hrmax is not None else {},
            colors=colors,
            age_formula_refs=age_formula_refs,
        )

    @app.get("/api/activities", response_model=list[ActivitySummary])
    def activities(
        from_date: date | None = Query(default=None, alias="from"),
        to_date: date | None = Query(default=None, alias="to"),
        sport_type: int | None = None,
    ) -> list[dict]:
        return list_activities(
            app_settings.duckdb_path,
            from_date=from_date,
            to_date=to_date,
            sport_type=sport_type,
        )

    @app.get("/api/activities/{activity_id}", response_model=ActivityDetail)
    def activity_detail(activity_id: str) -> dict:
        activity = get_activity(app_settings.duckdb_path, activity_id)
        if activity is None:
            raise HTTPException(status_code=404, detail="Activity not found")
        series = get_activity_samples(app_settings.duckdb_path, activity_id)
        hrmax, _ = _resolved_hrmax(app_settings)
        totals = (
            time_in_zones(series, hrmax) if hrmax is not None else _empty_zone_totals()
        )
        activity["hr_series"] = [
            HeartRatePoint(
                elapsed_s=elapsed_s,
                hr_bpm=hr_bpm,
                zone=assign_zone(hr_bpm, hrmax) if hrmax is not None else None,
            )
            for elapsed_s, hr_bpm in series
        ]
        activity["time_in_zone"] = totals
        activity["splat_minutes_estimate"] = splat_minutes(totals)
        return activity

    @app.get("/api/overview", response_model=OverviewResponse)
    def overview() -> OverviewResponse:
        count, duration = overview_totals(app_settings.duckdb_path)
        hrmax, _ = _resolved_hrmax(app_settings)
        zone_mix = _empty_zone_totals()
        if hrmax is not None:
            for series in all_activity_samples(app_settings.duckdb_path).values():
                totals = time_in_zones(series, hrmax)
                for zone, seconds in totals.items():
                    zone_mix[zone] += seconds
        return OverviewResponse(
            activity_count=count,
            duration_s=duration,
            zone_mix=zone_mix,
            splat_minutes_estimate=splat_minutes(zone_mix),
            recent=list_activities(app_settings.duckdb_path, limit=10),
        )

    return app


app = create_app()
