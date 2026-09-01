"""AQI categorization and alert rules."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from app.config import settings
from app.schemas import Alert, AlertLevel, AQICategory, AQIReading

CATEGORY_SEVERITY: dict[AQICategory, int] = {
    AQICategory.GOOD: 0,
    AQICategory.MODERATE: 1,
    AQICategory.UNHEALTHY_SENSITIVE: 2,
    AQICategory.UNHEALTHY: 3,
    AQICategory.VERY_UNHEALTHY: 4,
    AQICategory.HAZARDOUS: 5,
    AQICategory.UNKNOWN: -1,
}


def aqi_to_category(aqi: int) -> AQICategory:
    """Map a US AQI value to an EPA category label."""
    if aqi <= 50:
        return AQICategory.GOOD
    if aqi <= 100:
        return AQICategory.MODERATE
    if aqi <= 150:
        return AQICategory.UNHEALTHY_SENSITIVE
    if aqi <= 200:
        return AQICategory.UNHEALTHY
    if aqi <= 300:
        return AQICategory.VERY_UNHEALTHY
    return AQICategory.HAZARDOUS


def _alert_timestamp(reading: AQIReading) -> datetime:
    return reading.polled_at or reading.timestamp


def _alert_id(
    previous: AQIReading | None,
    current: AQIReading,
    kind: str,
    *,
    threshold: int | None = None,
) -> str:
    previous_key = "none" if previous is None else str(previous.aqi)
    raw = f"{previous_key}:{current.aqi}:{kind}:{threshold}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _level_for_worsening(category: AQICategory) -> AlertLevel:
    if category in (AQICategory.GOOD, AQICategory.MODERATE):
        return AlertLevel.INFO
    if category in (AQICategory.UNHEALTHY_SENSITIVE, AQICategory.UNHEALTHY):
        return AlertLevel.WARNING
    return AlertLevel.CRITICAL


def _build_alert(
    previous: AQIReading | None,
    current: AQIReading,
    *,
    kind: str,
    level: AlertLevel,
    message: str,
    threshold: int | None = None,
) -> Alert:
    return Alert(
        id=_alert_id(previous, current, kind, threshold=threshold),
        level=level,
        message=message,
        aqi=current.aqi,
        category=current.category,
        timestamp=_alert_timestamp(current),
    )


def evaluate_alerts(
    previous: AQIReading | None,
    current: AQIReading,
    thresholds: list[int] | None = None,
) -> list[Alert]:
    """
    Compare previous and current readings and return structured alerts.

    Emits alerts when AQI worsens/recovers by category or crosses configured
    thresholds. No alerts on the first reading or when nothing changed.
    """
    if previous is None:
        return []

    if (
        previous.aqi == current.aqi
        and previous.category == current.category
        and previous.stale == current.stale
    ):
        return []

    alert_thresholds = sorted(thresholds or settings.alert_thresholds)
    alerts: list[Alert] = []

    previous_severity = CATEGORY_SEVERITY[previous.category]
    current_severity = CATEGORY_SEVERITY[current.category]

    if current_severity > previous_severity:
        alerts.append(
            _build_alert(
                previous,
                current,
                kind="category_worse",
                level=_level_for_worsening(current.category),
                message=(
                    f"AQI worsened: {previous.category.value} -> "
                    f"{current.category.value} (AQI {current.aqi})"
                ),
            )
        )
    elif current_severity < previous_severity:
        alerts.append(
            _build_alert(
                previous,
                current,
                kind="category_recovery",
                level=AlertLevel.INFO,
                message=(
                    f"AQI improved: {previous.category.value} -> "
                    f"{current.category.value} (AQI {current.aqi})"
                ),
            )
        )

    for threshold in alert_thresholds:
        if previous.aqi < threshold <= current.aqi:
            alerts.append(
                _build_alert(
                    previous,
                    current,
                    kind="threshold_up",
                    level=_level_for_worsening(current.category),
                    message=f"AQI crossed above {threshold} (now {current.aqi})",
                    threshold=threshold,
                )
            )
        elif previous.aqi >= threshold > current.aqi:
            alerts.append(
                _build_alert(
                    previous,
                    current,
                    kind="threshold_recovery",
                    level=AlertLevel.INFO,
                    message=f"AQI dropped below {threshold} (now {current.aqi})",
                    threshold=threshold,
                )
            )

    return alerts
