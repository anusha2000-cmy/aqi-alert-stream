"""Tests for AQI alert evaluation."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.alert_engine import aqi_to_category, evaluate_alerts
from app.schemas import AlertLevel, AQICategory, AQIReading


def _reading(aqi: int, *, polled_minute: int = 0) -> AQIReading:
    return AQIReading(
        city="San Francisco",
        aqi=aqi,
        category=aqi_to_category(aqi),
        timestamp=datetime(2026, 8, 22, 7, 0, tzinfo=timezone.utc),
        polled_at=datetime(2026, 8, 22, 7, polled_minute, tzinfo=timezone.utc),
    )


def test_aqi_to_category_boundaries() -> None:
    assert aqi_to_category(50) == AQICategory.GOOD
    assert aqi_to_category(51) == AQICategory.MODERATE
    assert aqi_to_category(100) == AQICategory.MODERATE
    assert aqi_to_category(101) == AQICategory.UNHEALTHY_SENSITIVE
    assert aqi_to_category(301) == AQICategory.HAZARDOUS


def test_no_alerts_on_first_reading() -> None:
    assert evaluate_alerts(None, _reading(55)) == []


def test_no_alerts_when_reading_unchanged() -> None:
    previous = _reading(68, polled_minute=0)
    current = _reading(68, polled_minute=5)
    assert evaluate_alerts(previous, current) == []


def test_no_alerts_within_same_category_without_threshold_cross() -> None:
    previous = _reading(60)
    current = _reading(65)
    assert evaluate_alerts(previous, current) == []


def test_category_worsening_alert() -> None:
    alerts = evaluate_alerts(_reading(48), _reading(55))

    assert len(alerts) == 2
    assert any("worsened" in alert.message for alert in alerts)
    assert any("crossed above 50" in alert.message for alert in alerts)


def test_category_recovery_alert() -> None:
    alerts = evaluate_alerts(_reading(88), _reading(45))

    assert any("improved" in alert.message for alert in alerts)
    assert any("dropped below 50" in alert.message for alert in alerts)
    assert all(alert.level == AlertLevel.INFO for alert in alerts if "improved" in alert.message)


def test_threshold_recovery_alert() -> None:
    alerts = evaluate_alerts(_reading(95), _reading(85), thresholds=[90])

    assert len(alerts) == 1
    assert alerts[0].message == "AQI dropped below 90 (now 85)"


def test_hazardous_worsening_is_critical() -> None:
    alerts = evaluate_alerts(_reading(280), _reading(305))

    category_alert = next(alert for alert in alerts if "worsened" in alert.message)
    assert category_alert.level == AlertLevel.CRITICAL


def test_evaluate_alerts_is_deterministic() -> None:
    previous = _reading(48)
    current = _reading(55)

    first = evaluate_alerts(previous, current)
    second = evaluate_alerts(previous, current)

    assert [(alert.id, alert.message, alert.level) for alert in first] == [
        (alert.id, alert.message, alert.level) for alert in second
    ]
