"""Tests for WebSocket polling integration."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.aqi_client import AQIClient
from app.main import app
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


def _reading(aqi: int) -> AQIReading:
    return AQIReading(
        city="San Francisco",
        aqi=aqi,
        category=AQICategory.GOOD,
        pm25=10.0,
        timestamp=datetime(2026, 8, 22, 7, 0, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_poll_city_loop_emits_alerts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import poller
    from app.alert_engine import aqi_to_category

    isolated_state = AppState()
    monkeypatch.setattr(poller, "app_state", isolated_state)

    def make_reading(aqi: int) -> AQIReading:
        return AQIReading(
            city="San Francisco",
            aqi=aqi,
            category=aqi_to_category(aqi),
            timestamp=datetime(2026, 8, 22, 7, 0, tzinfo=timezone.utc),
        )

    mock_client = AsyncMock(spec=AQIClient)
    mock_client.fetch_current.side_effect = [make_reading(48), make_reading(55)]

    seen_alerts: list[str] = []
    stop_event = asyncio.Event()
    done = asyncio.Event()

    async def on_reading(reading: AQIReading) -> None:
        if reading.aqi == 55:
            done.set()

    async def on_alerts(alerts) -> None:
        seen_alerts.extend(alert.message for alert in alerts)

    task = asyncio.create_task(
        poller.poll_city_loop(
            city_key=CITY_KEY,
            city="San Francisco",
            latitude=37.7749,
            longitude=-122.4194,
            stop_event=stop_event,
            on_reading=on_reading,
            on_alerts=on_alerts,
            client=mock_client,
            interval_seconds=1,
        )
    )

    await asyncio.wait_for(done.wait(), timeout=2)
    stop_event.set()
    await task

    snapshot = await isolated_state.snapshot(CITY_KEY)
    assert any("worsened" in message for message in seen_alerts)
    assert len(snapshot.alerts) >= 1


@pytest.mark.asyncio
async def test_poll_city_loop_stores_readings_and_notifies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import poller

    isolated_state = AppState()
    monkeypatch.setattr(poller, "app_state", isolated_state)

    mock_client = AsyncMock(spec=AQIClient)
    mock_client.fetch_current.side_effect = [_reading(40), _reading(41)]

    seen: list[int] = []
    stop_event = asyncio.Event()
    done = asyncio.Event()

    async def on_reading(reading: AQIReading) -> None:
        seen.append(reading.aqi)
        if len(seen) >= 2:
            done.set()

    task = asyncio.create_task(
        poller.poll_city_loop(
            city_key=CITY_KEY,
            city="San Francisco",
            latitude=37.7749,
            longitude=-122.4194,
            stop_event=stop_event,
            on_reading=on_reading,
            client=mock_client,
            interval_seconds=1,
        )
    )

    await asyncio.wait_for(done.wait(), timeout=2)
    stop_event.set()
    await task

    snapshot = await isolated_state.snapshot(CITY_KEY)
    assert seen == [40, 41]
    assert len(snapshot.history) == 2
    assert snapshot.current is not None
    assert snapshot.current.aqi == 41


def test_websocket_receives_snapshot_and_first_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import websocket as ws_module

    mock_client = AsyncMock(spec=AQIClient)
    mock_client.fetch_current.return_value = _reading(55)

    async def mock_geocode_city(city: str) -> CityLocation:
        return LOCATION

    async def fast_poll(
        *,
        city_key: str,
        city: str,
        latitude: float,
        longitude: float,
        stop_event: asyncio.Event,
        on_reading,
        on_alerts=None,
        client=None,
        interval_seconds=None,
    ) -> None:
        reading = await (client or mock_client).fetch_current(
            city=city,
            latitude=latitude,
            longitude=longitude,
        )
        await on_reading(reading)
        await stop_event.wait()

    monkeypatch.setattr(ws_module, "geocode_city", mock_geocode_city)
    monkeypatch.setattr(ws_module, "poll_city_loop", fast_poll)

    client = TestClient(app)
    with client.websocket_connect("/ws/aqi") as ws:
        ws.send_json({"type": "subscribe", "data": {"city": "San Francisco"}})
        snapshot = ws.receive_json()
        update = ws.receive_json()

    assert snapshot["type"] == "snapshot"
    assert snapshot["data"]["location"]["name"] == "San Francisco"
    assert update["type"] == "update"
    assert update["data"]["aqi"] == 55
