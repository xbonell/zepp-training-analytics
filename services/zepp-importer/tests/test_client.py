from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from fitness import endpoints
from fitness.client import ZeppAuthError, ZeppClient


FIXTURE = Path(__file__).parent / "fixtures" / "history_page.json"


def test_endpoint_paths_and_params():
    assert endpoints.history_path() == "/v1/sport/run/history.json"
    assert endpoints.detail_path() == "/v1/sport/run/detail.json"
    assert endpoints.heart_rate_path("uid") == "/users/uid/heartRate"
    assert endpoints.history_params() == {}
    assert endpoints.history_params(123) == {"trackid": 123}
    assert endpoints.detail_params("track", "source") == {
        "trackid": "track",
        "source": "source",
    }
    assert endpoints.heart_rate_params("2026-01-01", "2026-01-31") == {
        "start": "2026-01-01",
        "end": "2026-01-31",
    }


def test_get_history_sends_auth_headers_and_cursor():
    body = FIXTURE.read_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["apptoken"] == "tok"
        assert request.headers["appPlatform"] == "web"
        assert request.headers["appname"] == "com.xiaomi.hm.health"
        assert request.url.path == "/v1/sport/run/history.json"
        assert dict(request.url.params) == {"trackid": "123"}
        return httpx.Response(200, content=body)

    with ZeppClient(
        "api-mifit-us3.zepp.com",
        "tok",
        "uid",
        transport=httpx.MockTransport(handler),
    ) as client:
        assert client.get_history(123) == body


def test_detail_and_heart_rate_requests():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=b"ok")

    with ZeppClient(
        "https://api-mifit-us3.zepp.com/",
        "tok",
        "uid",
        transport=httpx.MockTransport(handler),
    ) as client:
        assert client.get_detail("track", "source") == b"ok"
        assert client.get_heart_rate("2026-01-01", "2026-01-31") == b"ok"

    assert seen[0].url.path == "/v1/sport/run/detail.json"
    assert dict(seen[0].url.params) == {"trackid": "track", "source": "source"}
    assert seen[1].url.path == "/users/uid/heartRate"
    assert dict(seen[1].url.params) == {
        "start": "2026-01-01",
        "end": "2026-01-31",
    }


@pytest.mark.parametrize("status_code", [401, 403])
def test_auth_failures_raise_auth_error(status_code: int):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, content=b"nope")

    with ZeppClient(
        "api-mifit-us3.zepp.com",
        "tok",
        "uid",
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(ZeppAuthError, match="Re-extract apptoken"):
            client.get_history()


@pytest.mark.parametrize("status_code", [429, 500, 501, 502, 503, 504])
def test_retryable_status_retries_once(status_code: int):
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(status_code if attempts == 1 else 200, content=b"ok")

    with (
        patch("fitness.client.time.sleep") as sleep,
        ZeppClient(
            "api-mifit-us3.zepp.com",
            "tok",
            "uid",
            transport=httpx.MockTransport(handler),
        ) as client,
    ):
        assert client.get_history() == b"ok"

    assert attempts == 2
    sleep.assert_called_once_with(0.5)


def test_retryable_status_raises_after_second_failure():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(500, content=b"nope")

    with (
        patch("fitness.client.time.sleep"),
        ZeppClient(
            "api-mifit-us3.zepp.com",
            "tok",
            "uid",
            transport=httpx.MockTransport(handler),
        ) as client,
    ):
        with pytest.raises(httpx.HTTPStatusError):
            client.get_history()

    assert attempts == 2
