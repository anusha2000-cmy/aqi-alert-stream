# AQI Alert Stream

Real-time air quality monitoring dashboard. Subscribe to any city, stream live AQI readings over WebSocket, and get alerts when air quality worsens or crosses EPA thresholds.

## Features

- **City search** — geocodes any city name via [Open-Meteo Geocoding](https://open-meteo.com/en/docs/geocoding-api)
- **Live updates** — WebSocket stream pushes new readings on a configurable poll interval (default 5 minutes)
- **Alert engine** — category worsening/recovery and threshold-cross notifications (50, 100, 150, 200 AQI)
- **Reading history** — last 10 polls per city, deduplicated by fetch time
- **Session persistence** — selected city survives page refresh via `sessionStorage`
- **No API key required** — uses [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api) by default

## Tech stack

| Layer    | Stack                                      |
| -------- | ------------------------------------------ |
| Backend  | Python, FastAPI, httpx, pydantic-settings  |
| Frontend | React 19, TypeScript, Vite                 |
| Data     | Open-Meteo (geocoding + air quality)       |
| Tests    | pytest, pytest-asyncio (24 tests)          |

## Project structure

```
aqi-alert-stream/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app, CORS, /health
│   │   ├── websocket.py     # WS /ws/aqi
│   │   ├── aqi_client.py    # Open-Meteo AQI fetcher
│   │   ├── geocoding.py     # City → lat/lon resolution
│   │   ├── alert_engine.py  # Category + threshold alerts
│   │   ├── poller.py        # Per-connection poll loop
│   │   └── state.py         # In-memory per-city state
│   └── tests/
└── frontend/
    └── src/
        ├── hooks/useAqiSocket.ts
        └── components/      # CityInput, CurrentAqi, ReadingsTable, AlertFeed
```

## Prerequisites

- Python 3.11+
- Node.js 18+

## Quick start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # optional — defaults work out of the box
uvicorn app.main:app --reload --port 8000
```

Health check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173). The Vite dev server proxies WebSocket traffic to the backend on port 8000.

## Configuration

Set variables in `backend/.env` (see `.env.example`):

| Variable                  | Default | Description                          |
| ------------------------- | ------- | ------------------------------------ |
| `POLL_INTERVAL_SECONDS`   | `300`   | Seconds between AQI fetches          |
| `DEBUG`                   | `false` | Enable debug logging                 |
| `AQI_API_KEY`             | —       | Only needed for authenticated providers |

## WebSocket API

**Endpoint:** `ws://127.0.0.1:8000/ws/aqi`

1. Connect to the WebSocket.
2. Send a subscribe message with the city name:

```json
{
  "type": "subscribe",
  "data": { "city": "San Francisco" }
}
```

3. Receive message types:

| Type       | Description                                      |
| ---------- | ------------------------------------------------ |
| `snapshot` | Initial location + current reading               |
| `update`   | New AQI reading after each poll                  |
| `alert`    | Category change or threshold crossing            |
| `error`    | Geocoding failure or invalid payload             |

## Running tests

```bash
cd backend
source .venv/bin/activate
pytest
```

## License

MIT
