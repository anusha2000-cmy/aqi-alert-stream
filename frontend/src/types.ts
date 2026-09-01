export type AQICategory =
  | "Good"
  | "Moderate"
  | "Unhealthy for Sensitive Groups"
  | "Unhealthy"
  | "Very Unhealthy"
  | "Hazardous"
  | "Unknown";

export type AlertLevel = "info" | "warning" | "critical";

export interface AQIReading {
  city: string;
  aqi: number;
  category: AQICategory;
  pm25: number | null;
  timestamp: string;
  polled_at: string | null;
  stale: boolean;
}

export interface Alert {
  id: string;
  level: AlertLevel;
  message: string;
  aqi: number;
  category: AQICategory;
  timestamp: string;
}

export interface CityLocation {
  key: string;
  name: string;
  latitude: number;
  longitude: number;
  country: string | null;
  region: string | null;
}

export interface ReadingsSnapshot {
  current: AQIReading | null;
  history: AQIReading[];
  alerts: Alert[];
  location: CityLocation | null;
}

export type ConnectionState =
  | "idle"
  | "connecting"
  | "connected"
  | "disconnected"
  | "error";

export type WSMessage =
  | { type: "snapshot"; data: ReadingsSnapshot }
  | { type: "update"; data: AQIReading }
  | { type: "alert"; data: Alert }
  | { type: "error"; data: { message: string } };
