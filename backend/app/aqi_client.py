"""Public AQI API client using httpx.AsyncClient."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.alert_engine import aqi_to_category
from app.config import settings
from app.schemas import AQIReading

logger = logging.getLogger(__name__)


class AQIClientError(Exception):
    """Base error for AQI client failures."""


class AQIClientTimeoutError(AQIClientError):
    """Raised when the provider does not respond in time."""


class AQIClientHTTPError(AQIClientError):
    """Raised for non-2xx HTTP responses."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)


class AQIClientResponseError(AQIClientError):
    """Raised when provider JSON is missing or malformed."""


class AQIClient:
    """
    Fetches and normalizes AQI data from a public provider.

    Provider-specific request/response handling stays in this module.
    Callers only receive normalized AQIReading objects.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url or settings.aqi_api_base_url
        self._api_key = api_key if api_key is not None else settings.aqi_api_key
        self._timeout = timeout_seconds or settings.aqi_request_timeout_seconds
        self._http_client = http_client

    async def fetch_current(
        self,
        *,
        city: str,
        latitude: float,
        longitude: float,
    ) -> AQIReading:
        if self._http_client is not None:
            payload = await self._fetch_open_meteo_payload(
                self._http_client, latitude, longitude
            )
        else:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                payload = await self._fetch_open_meteo_payload(
                    client, latitude, longitude
                )

        return self._normalize_open_meteo(payload, city=city)

    async def _fetch_open_meteo_payload(
        self,
        client: httpx.AsyncClient,
        latitude: float,
        longitude: float,
    ) -> dict[str, Any]:
        params: dict[str, str | float] = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "us_aqi,pm2_5",
        }
        headers: dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            response = await client.get(
                self._base_url,
                params=params,
                headers=headers or None,
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise AQIClientTimeoutError("AQI provider request timed out") from exc
        except httpx.HTTPStatusError as exc:
            raise AQIClientHTTPError(
                exc.response.status_code,
                f"AQI provider returned HTTP {exc.response.status_code}",
            ) from exc
        except httpx.HTTPError as exc:
            raise AQIClientError("AQI provider request failed") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise AQIClientResponseError("AQI provider returned invalid JSON") from exc

        if not isinstance(payload, dict):
            raise AQIClientResponseError("AQI provider response must be a JSON object")

        return payload

    def _normalize_open_meteo(self, payload: dict[str, Any], *, city: str) -> AQIReading:
        current = payload.get("current")
        if not isinstance(current, dict):
            raise AQIClientResponseError("AQI provider response missing current object")

        aqi_raw = current.get("us_aqi")
        if aqi_raw is None:
            raise AQIClientResponseError("AQI provider response missing us_aqi")

        try:
            aqi = int(aqi_raw)
        except (TypeError, ValueError) as exc:
            raise AQIClientResponseError("AQI provider returned invalid us_aqi") from exc

        if aqi < 0:
            raise AQIClientResponseError("AQI provider returned negative us_aqi")

        pm25_raw = current.get("pm2_5")
        pm25: float | None
        if pm25_raw is None:
            pm25 = None
        else:
            try:
                pm25 = float(pm25_raw)
            except (TypeError, ValueError) as exc:
                raise AQIClientResponseError("AQI provider returned invalid pm2_5") from exc

        timestamp = self._parse_open_meteo_timestamp(current.get("time"))

        return AQIReading(
            city=city,
            aqi=aqi,
            category=aqi_to_category(aqi),
            pm25=pm25,
            timestamp=timestamp,
            stale=False,
        )

    @staticmethod
    def _parse_open_meteo_timestamp(value: Any) -> datetime:
        if not isinstance(value, str) or not value:
            return datetime.now(timezone.utc)

        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise AQIClientResponseError("AQI provider returned invalid timestamp") from exc

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)


aqi_client = AQIClient()
