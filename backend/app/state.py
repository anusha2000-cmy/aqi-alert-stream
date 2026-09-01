"""In-memory application state — per-city readings, alerts, and poll metadata."""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.config import settings
from app.schemas import Alert, AQIReading, CityLocation, ReadingsSnapshot


@dataclass
class CityState:
    location: CityLocation | None = None
    current: AQIReading | None = None
    history: deque[AQIReading] = field(default_factory=lambda: deque(maxlen=settings.history_size))
    alerts: deque[Alert] = field(default_factory=lambda: deque(maxlen=settings.alert_feed_size))
    last_poll_at: datetime | None = None
    last_poll_error: str | None = None


class AppState:
    """Async-safe in-memory store keyed by geocoded city id."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._cities: dict[str, CityState] = {}

    def _city_state(self, city_key: str) -> CityState:
        if city_key not in self._cities:
            self._cities[city_key] = CityState()
        return self._cities[city_key]

    async def set_location(self, city_key: str, location: CityLocation) -> None:
        async with self._lock:
            state = self._city_state(city_key)
            state.location = location

    async def add_reading(self, city_key: str, reading: AQIReading) -> AQIReading:
        async with self._lock:
            state = self._city_state(city_key)
            polled_at = datetime.now(timezone.utc)
            stored = reading.model_copy(update={"polled_at": polled_at, "stale": False})
            state.current = stored
            state.history.appendleft(stored)
            state.last_poll_at = polled_at
            state.last_poll_error = None
            return stored

    async def add_alerts(self, city_key: str, alerts: list[Alert]) -> None:
        async with self._lock:
            state = self._city_state(city_key)
            for alert in alerts:
                state.alerts.appendleft(alert)

    async def mark_current_stale(self, city_key: str) -> AQIReading | None:
        async with self._lock:
            state = self._city_state(city_key)
            if state.current is None:
                return None
            polled_at = datetime.now(timezone.utc)
            stale_reading = state.current.model_copy(
                update={"stale": True, "polled_at": polled_at}
            )
            state.current = stale_reading
            if state.history:
                state.history[0] = stale_reading
            state.last_poll_at = polled_at
            return stale_reading

    async def record_poll_error(self, city_key: str, message: str) -> None:
        async with self._lock:
            state = self._city_state(city_key)
            state.last_poll_error = message

    async def snapshot(self, city_key: str) -> ReadingsSnapshot:
        async with self._lock:
            state = self._city_state(city_key)
            return ReadingsSnapshot(
                current=state.current,
                history=list(state.history),
                alerts=list(state.alerts),
                location=state.location,
            )


app_state = AppState()
