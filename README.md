# 🌬️ WindSight — UK Wind Power Forecast Monitor

A **production-grade full-stack system** for monitoring UK wind power forecast accuracy against actual generation data from the BMRS Elexon API.

![Architecture: FastAPI + Next.js + DuckDB](https://img.shields.io/badge/architecture-FastAPI%20%2B%20Next.js%20%2B%20DuckDB-blue)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-green)
![TypeScript](https://img.shields.io/badge/typescript-5.3%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-yellow)

---

## 📋 Table of Contents

- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Deployment & Demo](#deployment--demo)
- [AI Usage Disclosure](#ai-usage-disclosure)
- [Known Limitations](#known-limitations)
- [Data Pipeline](#data-pipeline)
- [Backend API](#backend-api)
- [Frontend Dashboard](#frontend-dashboard)
- [Data Analysis](#data-analysis)
- [Docker Deployment](#docker-deployment)
- [API Reference](#api-reference)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        WindSight Architecture                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────┐    │
│  │  BMRS Elexon │     │   Pipeline   │     │     DuckDB       │    │
│  │     API      │────▶│  (Python)    │────▶│  (Columnar DB)   │    │
│  │  FUELHH      │     │  ingest.py   │     │  actual_gen      │    │
│  │  WINDFOR     │     │  Retry/Batch │     │  wind_forecast   │    │
│  └──────────────┘     └──────────────┘     └────────┬─────────┘    │
│                                                      │              │
│                                              ┌───────▼───────┐     │
│                                              │   FastAPI      │     │
│  ┌──────────────────┐                        │   Backend      │     │
│  │   Next.js 14     │◀──────REST API────────▶│   /generation  │     │
│  │   Frontend       │                        │   /forecast    │     │
│  │   ECharts        │     ┌──────────┐       │   /metrics     │     │
│  │   TypeScript     │     │ LRU Cache│◀─────▶│   Processor    │     │
│  └──────────────────┘     └──────────┘       └───────────────┘     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Design Principles

| Principle | Implementation |
|---|---|
| **Scalability** | Columnar DuckDB tuned for the January dataset; clear path to swap to a warehouse (e.g., ClickHouse/Snowflake) by replacing the connection layer |
| **Cost Efficiency** | In-memory LRU cache; columnar storage; efficient SQL window functions |
| **Fault Tolerance** | Retry with exponential backoff; partial data display; graceful degradation |
| **Clean Architecture** | Separated layers: ingestion → storage → query → API → frontend |

---

## Project Structure

```
windsight-forecast-monitor/
├── pipeline/                    # Data Ingestion Layer
│   ├── __init__.py
│   ├── config.py               # API URLs, date ranges, retry config
│   ├── schema.py               # DuckDB table DDL + indexes
│   └── ingest.py               # BMRS API fetcher + DuckDB loader
│
├── backend/                     # FastAPI Backend
│   ├── main.py                 # App entrypoint, CORS, lifespan
│   ├── routers/
│   │   ├── generation.py       # GET /api/v1/generation
│   │   ├── forecast.py         # GET /api/v1/forecast
│   │   └── metrics.py          # GET /api/v1/metrics
│   ├── services/
│   │   ├── forecast_processor.py  # Horizon selection algorithm
│   │   └── cache.py            # In-memory LRU cache with TTL
│   ├── db/
│   │   └── connection.py       # DuckDB connection pool
│   └── models/
│       └── schemas.py          # Pydantic request/response models
│
├── frontend/                    # Next.js Frontend
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   └── src/
│       ├── app/
│       │   ├── layout.tsx      # Root layout + SEO meta
│       │   ├── page.tsx        # Dashboard page
│       │   └── globals.css     # Design system (glassmorphism dark)
│       ├── components/
│       │   ├── Dashboard.tsx   # Main orchestrator
│       │   ├── TimeSeriesChart.tsx  # ECharts chart
│       │   ├── DateRangeSelector.tsx
│       │   ├── HorizonSlider.tsx
│       │   └── MetricsPanel.tsx
│       └── lib/
│           ├── api.ts          # API client
│           └── types.ts        # TypeScript types
│
├── analysis/
│   └── forecast_analysis.ipynb # Jupyter analysis notebook
│
├── data/                        # Generated data (gitignored)
│   ├── windsight.duckdb
│   ├── raw/
│   └── parquet/
│
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Quick Start

### Prerequisites

- **Python** 3.11+
- **Node.js** 20+
- **npm** 10+

### 1. Install Python dependencies

```bash
cd windsight-forecast-monitor
python -m venv .venv
source .venv/bin/activate    # macOS/Linux
pip install -r requirements.txt
```

### 2. Run the data pipeline

Fetches January 2024 wind data from the BMRS Elexon API:

```bash
python -m pipeline.ingest
```

This will:
- Fetch FUELHH (actual wind generation) and WINDFOR (forecasts) for each day of January 2024
- Save intermediate Parquet files to `data/parquet/`
- Load all records into `data/windsight.duckdb`

To validate without writing to the database:

```bash
python -m pipeline.ingest --dry-run
```

### 3. Start the backend API

```bash
uvicorn backend.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard available at: http://localhost:3000

---

## Deployment & Demo

- **Deployed frontend:** https://<your-vercel-app>.vercel.app  
- **API base URL:** https://<your-backend-host>  
- **Demo video (unlisted YouTube):** https://youtu.be/<video-id>  

> Replace the placeholders above with your live URLs before submitting. The take-home spec requires a deployed app link and a short demo video.

### CORS / Environment

- Set `WINDSIGHT_FRONTEND_ORIGINS` (comma-separated) to the exact frontend origin(s) when deploying the backend (e.g., `https://windsight.vercel.app`).
- Default development origins (`localhost:3000/3001`) are already allowed.

---

## AI Usage Disclosure

AI tools were used to accelerate parts of the build:

- **GitHub Copilot** — Code completion for routine React/TypeScript and Python boilerplate.
- **ChatGPT** — Drafting docstrings, README scaffolding, and CSS styling ideas.
- **VS Code inline suggestions** — Minor refactors and lint fixes.

All system design decisions (horizon selection SQL, ingestion boundaries, metric definitions), debugging, and validation were performed by the author. Notebook analysis and API logic were reviewed manually for correctness.

---

## Known Limitations

- **January-only data** — The dataset covers January 2024; reliability metrics (P10/P20) should not be generalized to other seasons without additional data.
- **Single-writer DuckDB** — Concurrent writes are not supported; the API runs read-only against a static file.
- **No authentication** — The demo API is open; add auth if exposing publicly.
- **Deployment placeholders** — Fill in the production URLs and demo video link before submission.

---

## Data Pipeline

The pipeline fetches data from two BMRS Elexon API endpoints:

| Dataset | Endpoint | Description |
|---|---|---|
| **FUELHH** | `/datasets/FUELHH/stream` | Half-hourly actual generation by fuel type |
| **WINDFOR** | `/datasets/WINDFOR/stream` | Wind generation forecasts with publish times |

WINDFOR is fetched **by target start time** (not publish time) to ensure forecasts published in late December but targeting early January are ingested for high-horizon queries.

### Resilience Features

- **Exponential backoff retry** with configurable max retries (default: 5)
- **Daily batch processing** to avoid API timeouts
- **Idempotent** — safe to re-run (uses INSERT OR REPLACE)
- **Partial failure tolerance** — continues processing remaining days on error

---

## Backend API

### Core Forecast Algorithm

For each target half-hour time slot, the system:

1. Filters forecasts where `publish_time ≤ target_time - horizon`
2. Selects the forecast with the **latest** `publish_time` (most informed)
3. Returns paired actual/forecast data for visualization

This is implemented as an efficient SQL query using DuckDB's `ROW_NUMBER()` window function.

### Performance

- **LRU cache** with 300s TTL for sub-200ms responses
- **DuckDB columnar storage** with specialized indexes
- **Read-only connections** for API queries (no write contention)

---

## Frontend Dashboard

### Features

- **Date/Time Range Selector** — Choose start/end times (UTC) within January 2024 at 30‑minute resolution
- **Horizon Slider** — Adjust forecast horizon from 0h (nowcast) to 48h
- **Time Series Chart** — Interactive ECharts chart with:
  - Actual generation (blue solid line)
  - Forecast generation (green dashed line)
  - Zoom/pan via scroll and slider
  - Rich tooltips showing MW values
- **Metrics Panel** — Real-time KPI cards:
  - MAE, Median Absolute Error, P99 Error, RMSE
  - P10 Reliable Supply, Capacity Factor
- **Responsive** — Works on desktop and mobile

### Fault Tolerance

The frontend uses `Promise.allSettled` to fetch data — if one API call fails, the dashboard still renders whatever data is available.

---

## Data Analysis

The Jupyter notebook (`analysis/forecast_analysis.ipynb`) provides:

1. **Error Metrics** — MAE, median, P99, RMSE at 4h horizon
2. **Error Distribution** — Histogram and CDF of forecast errors
3. **Error vs Horizon** — How accuracy degrades from 0h to 48h
4. **Error by Hour** — Temporal patterns (which hours are harder to forecast)
5. **Wind Reliability** — P10/P20 generation levels and duration curve
6. **Actual vs Forecast** — Visual comparison for the first week

### Running the notebook

```bash
pip install -r requirements.txt  # includes jupyter
cd analysis
jupyter notebook forecast_analysis.ipynb
```

---

## Docker Deployment

### Build and run all services

```bash
docker-compose up -d
```

This starts:
- **Backend** (port 8000) — FastAPI with uvicorn workers
- **Frontend** (port 3000) — Next.js standalone server
- (Cache is in-memory LRU; Redis container removed for simplicity)

### Production deployment

For production deployment:

1. **Backend**: Deploy to Render / Fly.io / AWS ECS
   ```bash
   docker build -f Dockerfile.backend -t windsight-backend .
   ```

2. **Frontend**: Deploy to Vercel
   ```bash
   cd frontend && npx vercel --prod
   ```
   Set `NEXT_PUBLIC_API_URL` to your backend URL.

3. **Database**: For production scale, migrate from DuckDB to ClickHouse
   by implementing the DB adapter interface in `backend/db/connection.py`.

---

## API Reference

### `GET /api/v1/generation`

Returns actual wind generation data.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `start` | datetime | Yes | Start time (ISO 8601 UTC) |
| `end` | datetime | Yes | End time (ISO 8601 UTC) |

### `GET /api/v1/forecast`

Returns horizon-adjusted forecast data.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `start` | datetime | Yes | Start time (ISO 8601 UTC) |
| `end` | datetime | Yes | End time (ISO 8601 UTC) |
| `horizon` | float | No | Forecast horizon in hours (0–48, default: 4) |

### `GET /api/v1/metrics`

Returns accuracy metrics and reliability analysis.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `start` | datetime | Yes | Start time (ISO 8601 UTC) |
| `end` | datetime | Yes | End time (ISO 8601 UTC) |
| `horizon` | float | No | Forecast horizon in hours (0–48, default: 4) |

### `GET /health`

Returns system health and record counts.

---

## License

MIT
