"""Tests for geocoding client."""

from __future__ import annotations

import httpx
import pytest

from app.geocoding import GeocodingClient, GeocodingError


def _mock_transport(status_code: int, payload: object) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=status_code, json=payload, request=request)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_resolve_normalizes_open_meteo_response() -> None:
    transport = _mock_transport(
        200,
        {
            "results": [
                {
                    "id": 5378538,
                    "name": "Oakland",
                    "latitude": 37.8044,
                    "longitude": -122.2712,
                    "country": "United States",
                    "admin1": "California",
                }
            ]
        },
    )
    client = GeocodingClient(http_client=httpx.AsyncClient(transport=transport))

    location = await client.resolve("Oakland")

    assert location.key == "5378538"
    assert location.name == "Oakland"
    assert location.latitude == pytest.approx(37.8044)
    assert location.longitude == pytest.approx(-122.2712)
    assert location.country == "United States"
    assert location.region == "California"


@pytest.mark.asyncio
async def test_resolve_raises_when_city_not_found() -> None:
    transport = _mock_transport(200, {"results": []})
    client = GeocodingClient(http_client=httpx.AsyncClient(transport=transport))

    with pytest.raises(GeocodingError, match="City not found"):
        await client.resolve("Not A Real City")
