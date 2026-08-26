from __future__ import annotations

import time
from types import TracebackType
from typing import Self

import httpx

from fitness import endpoints


class ZeppAuthError(Exception):
    """Raised when Zepp rejects the configured application token."""


class ZeppClient:
    def __init__(
        self,
        host: str,
        app_token: str,
        user_id: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.user_id = user_id
        base_url = host if host.startswith(("http://", "https://")) else f"https://{host}"
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={
                "apptoken": app_token,
                "appPlatform": endpoints.APP_PLATFORM,
                "appname": endpoints.APP_NAME,
            },
            transport=transport,
            timeout=60.0,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def get_raw(self, path: str, params: dict | None = None) -> bytes:
        for attempt in range(2):
            response = self._client.get(path, params=params or {})

            if response.status_code in (401, 403):
                raise ZeppAuthError(
                    f"Zepp auth failed ({response.status_code}). "
                    "Re-extract apptoken — see docs/zepp-auth.md"
                )

            retryable = response.status_code == 429 or 500 <= response.status_code < 600
            if retryable and attempt == 0:
                time.sleep(0.5)
                continue

            response.raise_for_status()
            return response.content

        raise RuntimeError("unreachable")

    def get_history(self, from_track_id: int | None = None) -> bytes:
        return self.get_raw(
            endpoints.history_path(),
            endpoints.history_params(from_track_id),
        )

    def get_detail(self, track_id: str, source: str) -> bytes:
        return self.get_raw(
            endpoints.detail_path(),
            endpoints.detail_params(track_id, source),
        )

    def get_heart_rate(self, start: str, end: str) -> bytes:
        return self.get_raw(
            endpoints.heart_rate_path(self.user_id),
            endpoints.heart_rate_params(start, end),
        )

    def get_band_data(self, day: str) -> bytes:
        return self.get_raw(
            endpoints.band_data_path(),
            endpoints.band_data_params(self.user_id, day),
        )
