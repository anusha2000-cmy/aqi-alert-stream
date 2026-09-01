"""Pydantic models shared across routes, services, and WebSocket messages."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class AQICategory(str, Enum):
    """EPA AQI category labels."""

    GOOD = "Good"
    MODERATE = "Moderate"
    UNHEALTHY_SENSITIVE = "Unhealthy for Sensitive Groups"
    UNHEALTHY = "Unhealthy"
    VERY_UNHEALTHY = "Very Unhealthy"
    HAZARDOUS = "Hazardous"
    UNKNOWN = "Unknown"


class AQIReading(BaseModel):
    """Normalized AQI reading used throughout the app."""

    city: str
    aqi: int = Field(ge=0)
    category: AQICategory
    pm25: float | None = None
    timestamp: datetime  # provider observation time
    polled_at: datetime | None = None  # when this app fetched the reading
    stale: bool = False


class CityLocation(BaseModel):
    """Resolved city coordinates from geocoding."""

    key: str
    name: str
    latitude: float
    longitude: float
    country: str | None = None
    region: str | None = None


class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Alert(BaseModel):
    """Threshold or category-change notification."""

    id: str
    level: AlertLevel
    message: str
    aqi: int
    category: AQICategory
    timestamp: datetime


class HealthResponse(BaseModel):
    status: str


class ReadingsSnapshot(BaseModel):
    """Bootstrap payload for REST and WebSocket snapshot events."""

    current: AQIReading | None = None
    history: list[AQIReading] = Field(default_factory=list)
    alerts: list[Alert] = Field(default_factory=list)
    location: CityLocation | None = None


class WSMessageType(str, Enum):
    SUBSCRIBE = "subscribe"
    SNAPSHOT = "snapshot"
    UPDATE = "update"
    ALERT = "alert"
    ERROR = "error"


class SubscribeRequest(BaseModel):
    """Client subscribe payload — one city per WebSocket connection."""

    city: str = Field(min_length=1, max_length=100)


class WSMessage(BaseModel):
    """JSON envelope for /ws/aqi messages."""

    type: WSMessageType
    data: ReadingsSnapshot | AQIReading | Alert | SubscribeRequest | dict | None = None
