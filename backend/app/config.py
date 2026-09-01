"""Application settings — override via environment variables or .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "AQI Alert Stream"
    debug: bool = False

    poll_interval_seconds: float = 300.0
    alert_thresholds: list[int] = [50, 100, 150, 200]
    history_size: int = 10
    alert_feed_size: int = 50

    # External AQI provider (Open-Meteo by default — no key required)
    aqi_api_base_url: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
    geocoding_api_base_url: str = "https://geocoding-api.open-meteo.com/v1/search"
    aqi_api_key: str | None = None
    aqi_request_timeout_seconds: float = 10.0


settings = Settings()
