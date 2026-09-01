"""Tests for the external AQI client."""

from __future__ import annotations

import json

import httpx
import pytest

from app.aqi_client import (
    AQIClient,
    AQIClientHTTPError,
    AQIClientResponseError,
    AQIClientTimeoutError,
)
from app.schemas import AQICategory

SF_COORDS = {"city": "San Francisco", "latitude": 37.7749, "longitude": -122.4194}


def _mock_transport(status_code: int, payload: object) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if isinstance(payload, Exception):
            raise payload
        return httpx.Response(
            status_code=status_code,
            json=payload,
            request=request,
        )

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_fetch_current_normalizes_open_meteo_response() -> None:
    transport = _mock_transport(
        200,
        {
            "current": {
                "time": "2026-08-22T07:00",
                "us_aqi": 68,
                "pm2_5": 18.4,
            }
        },
    )
    client = AQIClient(http_client=httpx.AsyncClient(transport=transport))

    reading = await client.fetch_current(**SF_COORDS)

    assert reading.city == "San Francisco"
    assert reading.aqi == 68
    assert reading.category == AQICategory.MODERATE
    assert reading.pm25 == 18.4
    assert reading.stale is False


@pytest.mark.asyncio
async def test_fetch_current_raises_on_missing_aqi() -> None:
    transport = _mock_transport(200, {"current": {"time": "2026-08-22T07:00"}})
    client = AQIClient(http_client=httpx.AsyncClient(transport=transport))

    with pytest.raises(AQIClientResponseError, match="missing us_aqi"):
        await client.fetch_current(**SF_COORDS)


@pytest.mark.asyncio
async def test_fetch_current_raises_on_malformed_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            content=b"not-json",
            request=request,
        )

    client = AQIClient(http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    with pytest.raises(AQIClientResponseError, match="invalid JSON"):
        await client.fetch_current(**SF_COORDS)


@pytest.mark.asyncio
async def test_fetch_current_raises_on_http_error() -> None:
    transport = _mock_transport(503, {"error": "unavailable"})
    client = AQIClient(http_client=httpx.AsyncClient(transport=transport))

    with pytest.raises(AQIClientHTTPError) as exc_info:
        await client.fetch_current(**SF_COORDS)

    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_fetch_current_raises_on_timeout() -> None:
    transport = _mock_transport(200, httpx.ReadTimeout("timed out"))
    client = AQIClient(
        http_client=httpx.AsyncClient(transport=transport),
        timeout_seconds=0.1,
    )

    with pytest.raises(AQIClientTimeoutError, match="timed out"):
        await client.fetch_current(**SF_COORDS)
