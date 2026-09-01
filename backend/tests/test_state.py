"""Tests for in-memory reading storage."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.schemas import AQICategory, AQIReading, CityLocation
from app.state import AppState

CITY_KEY = "5391959"
LOCATION = CityLocation(
    key=CITY_KEY,
    name="San Francisco",
    latitude=37.7749,
    longitude=-122.4194,
    country="United States",
    region="California",
)


def _reading(aqi: int, *, city: str = "San Francisco") -> AQIReading:
    return AQIReading(
        city=city,
        aqi=aqi,
        category=AQICategory.GOOD,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_state_keeps_only_last_ten_readings() -> None:
    state = AppState()

    for aqi in range(1, 15):
        await state.add_reading(CITY_KEY, _reading(aqi))

    snapshot = await state.snapshot(CITY_KEY)

    assert len(snapshot.history) == 10
    assert [reading.aqi for reading in snapshot.history] == list(range(14, 4, -1))
    assert snapshot.current is not None
    assert snapshot.current.aqi == 14


@pytest.mark.asyncio
async def test_state_isolated_per_city() -> None:
    state = AppState()
    oakland_key = "5378538"

    await state.set_location(CITY_KEY, LOCATION)
    await state.set_location(
        oakland_key,
        LOCATION.model_copy(update={"key": oakland_key, "name": "Oakland"}),
    )
    await state.add_reading(CITY_KEY, _reading(40))
    await state.add_reading(oakland_key, _reading(80, city="Oakland"))

    sf_snapshot = await state.snapshot(CITY_KEY)
    oakland_snapshot = await state.snapshot(oakland_key)

    assert sf_snapshot.current is not None
    assert sf_snapshot.current.aqi == 40
    assert oakland_snapshot.current is not None
    assert oakland_snapshot.current.aqi == 80


@pytest.mark.asyncio
async def test_state_sets_polled_at_on_add() -> None:
    state = AppState()
    observed_at = datetime(2026, 8, 22, 7, 0, tzinfo=timezone.utc)

    stored = await state.add_reading(
        CITY_KEY,
        _reading(42).model_copy(update={"timestamp": observed_at}),
    )

    assert stored.timestamp == observed_at
    assert stored.polled_at is not None
    assert stored.polled_at >= observed_at


@pytest.mark.asyncio
async def test_state_appends_each_poll_even_when_observation_unchanged() -> None:
    state = AppState()
    observed_at = datetime(2026, 8, 22, 7, 0, tzinfo=timezone.utc)

    await state.add_reading(
        CITY_KEY,
        _reading(42).model_copy(update={"timestamp": observed_at}),
    )
    await state.add_reading(
        CITY_KEY,
        _reading(42).model_copy(update={"timestamp": observed_at}),
    )

    snapshot = await state.snapshot(CITY_KEY)

    assert len(snapshot.history) == 2
    assert snapshot.history[0].polled_at != snapshot.history[1].polled_at


@pytest.mark.asyncio
async def test_state_marks_current_reading_stale() -> None:
    state = AppState()
    await state.add_reading(CITY_KEY, _reading(42))

    stale = await state.mark_current_stale(CITY_KEY)

    assert stale is not None
    assert stale.stale is True
    snapshot = await state.snapshot(CITY_KEY)
    assert snapshot.current is not None
    assert snapshot.current.stale is True
