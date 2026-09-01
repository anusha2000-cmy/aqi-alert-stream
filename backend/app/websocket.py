"""WebSocket routes for real-time AQI updates."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.geocoding import GeocodingError, geocode_city
from app.poller import poll_city_loop
from app.schemas import Alert, AQIReading, SubscribeRequest, WSMessage, WSMessageType
from app.state import app_state

logger = logging.getLogger(__name__)

router = APIRouter()


async def _send_message(websocket: WebSocket, message: WSMessage) -> None:
    await websocket.send_json(message.model_dump(mode="json"))


async def _send_error(websocket: WebSocket, detail: str) -> None:
    await _send_message(
        websocket,
        WSMessage(type=WSMessageType.ERROR, data={"message": detail}),
    )


async def _wait_for_subscribe(websocket: WebSocket) -> SubscribeRequest:
    raw = await websocket.receive_text()

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON payload") from exc

    if not isinstance(payload, dict):
        raise ValueError("Message must be a JSON object")

    message_type = payload.get("type")
    if message_type != WSMessageType.SUBSCRIBE.value:
        raise ValueError("First message must be type 'subscribe'")

    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("Subscribe message requires a data object")

    try:
        return SubscribeRequest.model_validate(data)
    except ValidationError as exc:
        raise ValueError("Invalid subscribe payload") from exc


@router.websocket("/ws/aqi")
async def aqi_websocket(websocket: WebSocket) -> None:
    """
    Real-time AQI stream for a single city subscription.

    Client flow:
      1. Connect
      2. Send {"type": "subscribe", "data": {"city": "San Francisco"}}
      3. Receive a snapshot, then update messages on each poll
    """
    await websocket.accept()
    subscribed_city: str | None = None
    poll_task: asyncio.Task | None = None
    stop_event = asyncio.Event()

    logger.info("WebSocket connected")

    try:
        try:
            subscription = await _wait_for_subscribe(websocket)
        except ValueError as exc:
            await _send_error(websocket, str(exc))
            await websocket.close(code=1008, reason=str(exc))
            return

        try:
            location = await geocode_city(subscription.city)
        except GeocodingError as exc:
            await _send_error(websocket, str(exc))
            await websocket.close(code=1008, reason=str(exc))
            return

        subscribed_city = location.name
        await app_state.set_location(location.key, location)
        logger.info(
            "WebSocket subscribed to city=%s (%.4f, %.4f)",
            location.name,
            location.latitude,
            location.longitude,
        )

        snapshot = await app_state.snapshot(location.key)
        await _send_message(
            websocket,
            WSMessage(type=WSMessageType.SNAPSHOT, data=snapshot),
        )

        async def send_update(reading: AQIReading) -> None:
            await _send_message(
                websocket,
                WSMessage(type=WSMessageType.UPDATE, data=reading),
            )

        async def send_alerts(alerts: list[Alert]) -> None:
            for alert in alerts:
                await _send_message(
                    websocket,
                    WSMessage(type=WSMessageType.ALERT, data=alert),
                )

        poll_task = asyncio.create_task(
            poll_city_loop(
                city_key=location.key,
                city=location.name,
                latitude=location.latitude,
                longitude=location.longitude,
                stop_event=stop_event,
                on_reading=send_update,
                on_alerts=send_alerts,
            )
        )

        while True:
            message = await websocket.receive_text()
            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                await _send_error(websocket, "Invalid JSON payload")
                continue

            if payload.get("type") == WSMessageType.SUBSCRIBE.value:
                await _send_error(
                    websocket,
                    "Already subscribed — only one city per connection",
                )
                continue

            await _send_error(
                websocket,
                f"Unsupported message type: {payload.get('type')!r}",
            )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for city=%s", subscribed_city)
    except Exception:
        logger.exception("WebSocket error for city=%s", subscribed_city)
        try:
            await _send_error(websocket, "Internal server error")
        except Exception:
            logger.exception("Failed to send WebSocket error message")
    finally:
        stop_event.set()
        if poll_task is not None:
            poll_task.cancel()
            try:
                await poll_task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception("Poll task failed for city=%s", subscribed_city)
        logger.info("WebSocket cleanup complete for city=%s", subscribed_city)
