"""Periodic AQI polling using the external API client."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from app.alert_engine import evaluate_alerts
from app.aqi_client import AQIClient, AQIClientError, aqi_client
from app.config import settings
from app.schemas import Alert, AQIReading
from app.state import app_state

logger = logging.getLogger(__name__)


async def poll_city_loop(
    *,
    city_key: str,
    city: str,
    latitude: float,
    longitude: float,
    stop_event: asyncio.Event,
    on_reading: Callable[[AQIReading], Awaitable[None]],
    on_alerts: Callable[[list[Alert]], Awaitable[None]] | None = None,
    client: AQIClient | None = None,
    interval_seconds: float | None = None,
) -> None:
    """
    Poll the AQI provider until stop_event is set.

    Each successful fetch is stored for the city key, evaluated for alerts,
    and forwarded to callbacks.
    """
    poll_client = client or aqi_client
    interval = interval_seconds or settings.poll_interval_seconds

    try:
        while not stop_event.is_set():
            try:
                previous = (await app_state.snapshot(city_key)).current
                reading = await poll_client.fetch_current(
                    city=city,
                    latitude=latitude,
                    longitude=longitude,
                )
                stored = await app_state.add_reading(city_key, reading)
                alerts = evaluate_alerts(previous, stored)
                if alerts:
                    await app_state.add_alerts(city_key, alerts)
                    if on_alerts is not None:
                        await on_alerts(alerts)
                await on_reading(stored)
            except AQIClientError as exc:
                logger.warning("AQI poll failed for city=%s: %s", city, exc)
                await app_state.record_poll_error(city_key, str(exc))
                stale_reading = await app_state.mark_current_stale(city_key)
                if stale_reading is not None:
                    await on_reading(stale_reading)

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                continue
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Poll loop failed for city=%s", city)
        raise
