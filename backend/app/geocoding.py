"""Geocoding client for resolving city names to coordinates."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings
from app.schemas import CityLocation

logger = logging.getLogger(__name__)


class GeocodingError(Exception):
    """Raised when a city cannot be resolved."""


class GeocodingClient:
    """Resolve city names using the Open-Meteo geocoding API."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url or settings.geocoding_api_base_url
        self._timeout = timeout_seconds or settings.aqi_request_timeout_seconds
        self._http_client = http_client

    async def resolve(self, query: str) -> CityLocation:
        trimmed = query.strip()
        if not trimmed:
            raise GeocodingError("City name is required")

        params: dict[str, str | int] = {
            "name": trimmed,
            "count": 1,
            "language": "en",
            "format": "json",
        }

        if self._http_client is not None:
            payload = await self._fetch_payload(self._http_client, params)
        else:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                payload = await self._fetch_payload(client, params)

        return self._normalize_open_meteo(payload, query=trimmed)

    async def _fetch_payload(
        self,
        client: httpx.AsyncClient,
        params: dict[str, str | int],
    ) -> dict[str, Any]:
        try:
            response = await client.get(self._base_url, params=params)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise GeocodingError("Geocoding request timed out") from exc
        except httpx.HTTPStatusError as exc:
            raise GeocodingError(
                f"Geocoding provider returned HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise GeocodingError("Geocoding request failed") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise GeocodingError("Geocoding provider returned invalid JSON") from exc

        if not isinstance(payload, dict):
            raise GeocodingError("Geocoding provider response must be a JSON object")

        return payload

    def _normalize_open_meteo(self, payload: dict[str, Any], *, query: str) -> CityLocation:
        results = payload.get("results")
        if not isinstance(results, list) or not results:
            raise GeocodingError(f"City not found: {query}")

        match = results[0]
        if not isinstance(match, dict):
            raise GeocodingError("Geocoding provider returned invalid result")

        name = match.get("name")
        latitude = match.get("latitude")
        longitude = match.get("longitude")
        result_id = match.get("id")

        if not isinstance(name, str) or not name:
            raise GeocodingError("Geocoding provider returned invalid city name")
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            raise GeocodingError("Geocoding provider returned invalid coordinates")
        if result_id is None:
            raise GeocodingError("Geocoding provider returned invalid city id")

        country = match.get("country")
        region = match.get("admin1")

        return CityLocation(
            key=str(result_id),
            name=name,
            latitude=float(latitude),
            longitude=float(longitude),
            country=country if isinstance(country, str) else None,
            region=region if isinstance(region, str) else None,
        )


geocoding_client = GeocodingClient()


async def geocode_city(query: str) -> CityLocation:
    return await geocoding_client.resolve(query)
