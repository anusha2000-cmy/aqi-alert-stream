import { useCallback, useEffect, useRef, useState } from "react";
import type {
  Alert,
  AQIReading,
  CityLocation,
  ConnectionState,
  WSMessage,
} from "../types";

const MAX_HISTORY = 10;
const MAX_ALERTS = 50;
const STORAGE_KEY = "aqi-subscribed-city";
const WS_URL =
  import.meta.env.VITE_WS_URL ??
  `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/ws/aqi`;

interface DashboardState {
  connectionState: ConnectionState;
  error: string | null;
  location: CityLocation | null;
  current: AQIReading | null;
  history: AQIReading[];
  alerts: Alert[];
}

function pollKey(reading: AQIReading): string {
  return reading.polled_at ?? `${reading.aqi}|${reading.timestamp}`;
}

function prependReading(
  history: AQIReading[],
  reading: AQIReading,
): AQIReading[] {
  const key = pollKey(reading);
  const without = history.filter((item) => pollKey(item) !== key);
  return [reading, ...without].slice(0, MAX_HISTORY);
}

function prependAlert(alerts: Alert[], alert: Alert): Alert[] {
  const next = [alert, ...alerts.filter((item) => item.id !== alert.id)];
  return next.slice(0, MAX_ALERTS);
}

export function loadSavedCity(): string {
  try {
    return sessionStorage.getItem(STORAGE_KEY)?.trim() ?? "";
  } catch {
    return "";
  }
}

export function saveSubscribedCity(city: string): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, city);
  } catch {
    // Ignore storage failures in private browsing or restricted contexts.
  }
}

export function useAqiSocket(city: string) {
  const [state, setState] = useState<DashboardState>({
    connectionState: "idle",
    error: null,
    location: null,
    current: null,
    history: [],
    alerts: [],
  });

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const reconnectAttemptRef = useRef(0);
  const intentionalCloseRef = useRef(false);
  const cityRef = useRef(city);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current !== null) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const closeSocket = useCallback(
    (intentional = true) => {
      clearReconnectTimer();
      intentionalCloseRef.current = intentional;
      const socket = socketRef.current;
      socketRef.current = null;
      if (!socket) {
        return;
      }

      socket.onopen = null;
      socket.onmessage = null;
      socket.onerror = null;
      socket.onclose = null;

      if (
        socket.readyState === WebSocket.OPEN ||
        socket.readyState === WebSocket.CONNECTING
      ) {
        socket.close();
      }
    },
    [clearReconnectTimer],
  );

  const handleMessage = useCallback((event: MessageEvent<string>) => {
    let message: WSMessage;
    try {
      message = JSON.parse(event.data) as WSMessage;
    } catch {
      setState((prev) => ({
        ...prev,
        error: "Received invalid WebSocket payload",
      }));
      return;
    }

    switch (message.type) {
      case "snapshot":
        if (message.data.location?.name) {
          saveSubscribedCity(message.data.location.name);
        }
        // Session only: keep city/location, start fresh — do not restore server history.
        setState((prev) => ({
          ...prev,
          location: message.data.location,
          error: null,
        }));
        break;
      case "update":
        setState((prev) => ({
          ...prev,
          current: message.data,
          history: prependReading(prev.history, message.data),
          error: null,
        }));
        break;
      case "alert":
        setState((prev) => ({
          ...prev,
          alerts: prependAlert(prev.alerts, message.data),
          error: null,
        }));
        break;
      case "error":
        setState((prev) => ({
          ...prev,
          error: message.data.message,
        }));
        break;
      default:
        break;
    }
  }, []);

  const connect = useCallback(() => {
    const trimmedCity = cityRef.current.trim();
    if (!trimmedCity) {
      setState({
        connectionState: "idle",
        error: null,
        location: null,
        current: null,
        history: [],
        alerts: [],
      });
      return;
    }

    closeSocket(true);
    setState({
      connectionState: "connecting",
      error: null,
      location: null,
      current: null,
      history: [],
      alerts: [],
    });

    const socket = new WebSocket(WS_URL);
    socketRef.current = socket;

    socket.onopen = () => {
      if (socketRef.current !== socket) {
        return;
      }

      reconnectAttemptRef.current = 0;
      setState((prev) => ({
        ...prev,
        connectionState: "connected",
        error: null,
      }));
      socket.send(
        JSON.stringify({
          type: "subscribe",
          data: { city: trimmedCity },
        }),
      );
    };

    socket.onmessage = (event) => {
      if (socketRef.current !== socket) {
        return;
      }
      handleMessage(event);
    };

    socket.onerror = () => {
      if (socketRef.current !== socket) {
        return;
      }
      setState((prev) => ({
        ...prev,
        connectionState: "error",
        error: "WebSocket connection error",
      }));
    };

    socket.onclose = () => {
      if (socketRef.current !== socket) {
        return;
      }

      socketRef.current = null;

      if (intentionalCloseRef.current) {
        intentionalCloseRef.current = false;
        return;
      }

      setState((prev) => ({
        ...prev,
        connectionState: "disconnected",
      }));

      const delay = Math.min(1000 * 2 ** reconnectAttemptRef.current, 10000);
      reconnectAttemptRef.current += 1;
      reconnectTimerRef.current = window.setTimeout(connect, delay);
    };
  }, [closeSocket, handleMessage]);

  useEffect(() => {
    cityRef.current = city;
  }, [city]);

  useEffect(() => {
    if (!city.trim()) {
      closeSocket(true);
      setState({
        connectionState: "idle",
        error: null,
        location: null,
        current: null,
        history: [],
        alerts: [],
      });
      return;
    }

    connect();

    return () => {
      closeSocket(true);
    };
  }, [city, connect, closeSocket]);

  return state;
}
