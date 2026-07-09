# AdPulse Agent Guide

## Project Overview

AdPulse is a **full-stack demonstrative platform for programmatic advertising**. It covers RTB auction simulation, AI bidding agent decision loops, A/B testing, multi-touch attribution, and traffic quality monitoring. The project is intended for learning and technical exchange only — all data is simulated and does not involve real ad delivery.

The codebase is split into a Python/FastAPI backend (`backend/`) and a React/TypeScript frontend (`frontend/`), containerized together via Docker Compose.

> **Important current state:** The backend includes JWT/RBAC authentication, API key access, and production-oriented v2 engines (RTB, A/B testing, attribution, agent). Business pages also use dedicated `-sim` routers (`/api/v2/rtb/simulate`, `/api/v2/agent-sim`, `/api/v2/abtests-sim`) that expose the original interactive simulations under the v2 namespace. The Docker Compose stack now runs PostgreSQL, Redis, backend, and frontend services. Local development still defaults to SQLite. All backend tests pass and the code quality pipeline (black/isort/flake8/mypy) is clean.

## Tech Stack

### Backend

- **Python 3.11+**
- **FastAPI 0.111.1** + **Pydantic v2** + **pydantic-settings**
- **SQLAlchemy 2.0 async** with `Mapped` / `mapped_column` style
- **SQLite** via `aiosqlite` for local development and tests
- **PostgreSQL** via `asyncpg` in the Docker Compose stack
- **Alembic** 1.13.2 is configured; migrations run automatically in Docker (`USE_ALEMBIC=true`), while local SQLite mode still auto-creates tables via `Base.metadata.create_all()`
- **SciPy**, **NumPy**, **pandas**, **statsmodels** for A/B test inference and attribution
- **pytest** + **pytest-asyncio** + **httpx** + **pytest-cov**
- Code quality tools in `pyproject.toml`: **black**, **isort**, **flake8**, **mypy**

Dependencies that are installed but **optional or PostgreSQL-only**:
- `asyncpg`, `pgvector` (used only when `DATABASE_URL` points to PostgreSQL)
- `redis` (used when `REDIS_URL` is configured; otherwise falls back to a no-op client)

Dependencies now used by application code:
- `python-jose`, `passlib`, `bcrypt` for JWT access/refresh tokens and password/API-key hashing
- `openai`, `anthropic` for real LLM function calling in the v2 agent (fallback to deterministic output when no API key is configured)

### Frontend

- **React 18.3.1**
- **TypeScript 5.5.3**
- **Vite 5.3.3**
- **React Router v6**
- **Tailwind CSS 3.4.4** + PostCSS + Autoprefixer
- **Recharts** for charts
- **Lucide React** for icons
- **clsx** + **tailwind-merge**

- **Zustand** for authentication state (with `persist` middleware)
- **axios** for API calls via `src/lib/apiClient.ts` (auth header injection + 401 refresh retry)
- **react-hot-toast** for notifications
- **Playwright** for end-to-end tests (in `tests/e2e/`)

State is mostly plain React local state; authentication is managed globally by `src/stores/authStore.ts`.

## Directory Structure

```
adpulse/
├── .github/workflows/ci.yml    # GitHub Actions CI
├── docker-compose.yml          # Local Docker stack (backend + frontend)
├── README.md                   # Human-facing documentation (Chinese)
├── AGENTS.md                   # This file
├── backend/
│   ├── .env                    # Environment variables (not committed)
│   ├── alembic.ini             # Alembic configuration
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/           # Initial migration (PostgreSQL-oriented)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI application and lifespan
│   │   ├── agent/              # ReAct bidding agent logic
│   │   │   ├── bidding_agent.py
│   │   │   ├── bidding_agent_v2.py
│   │   │   ├── llm_client.py
│   │   │   ├── memory_store.py
│   │   │   └── tools.py
│   │   ├── api/                # FastAPI routers
│   │   │   ├── abtest.py
│   │   │   ├── abtest_v2.py
│   │   │   ├── agent.py
│   │   │   ├── agent_v2.py
│   │   │   ├── attribution.py
│   │   │   ├── attribution_v2.py
│   │   │   ├── auth.py
│   │   │   ├── dashboard.py
│   │   │   ├── rtb.py
│   │   │   ├── rtb_v2.py
│   │   │   └── traffic.py
│   │   ├── core/               # Config, DB, response envelope, seed, security
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── exceptions.py
│   │   │   ├── redis.py
│   │   │   ├── response.py
│   │   │   ├── security.py
│   │   │   └── seed.py
│   │   ├── models/             # SQLAlchemy models (single file)
│   │   │   └── models.py
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   │   ├── abtest.py
│   │   │   ├── agent.py
│   │   │   ├── attribution.py
│   │   │   ├── dashboard.py
│   │   │   ├── rtb.py
│   │   │   └── traffic.py
│   │   ├── services/           # Business engines
│   │   │   ├── ab_test_engine.py
│   │   │   ├── ab_test_v2_engine.py
│   │   │   ├── attribution_engine.py
│   │   │   ├── attribution_v2_engine.py
│   │   │   ├── auth_service.py
│   │   │   ├── rtb_engine.py
│   │   │   ├── rtb_v2_engine.py
│   │   │   └── traffic_quality_engine.py
│   │   └── main.py             # FastAPI application and lifespan
│   ├── tests/
│   │   ├── conftest.py         # In-memory SQLite test DB fixture
│   │   ├── test_api.py         # Legacy endpoint integration tests
│   │   └── test_v2.py          # Auth and v2 endpoint/service tests
│   ├── Dockerfile
│   ├── adpulse.db              # Local SQLite database (created at runtime)
│   ├── pyproject.toml          # Tool config for black/isort/mypy/flake8
│   ├── pytest.ini
│   ├── requirements.txt
│   └── uploads/                # Uploaded assets directory
└── frontend/
    ├── index.html
    ├── package.json
    ├── package-lock.json
    ├── Dockerfile
    ├── nginx.conf               # Nginx config used in production image
    ├── postcss.config.js
    ├── tailwind.config.js
    ├── tsconfig.json
    ├── tsconfig.node.json
    ├── vite.config.ts
    └── src/
        ├── main.tsx
        ├── App.tsx              # Route table
        ├── index.css            # Tailwind + dark theme utilities
        ├── vite-env.d.ts
        ├── components/
        │   ├── Layout.tsx
        │   ├── agent/
        │   │   ├── AgentConfig.tsx
        │   │   ├── AgentLog.tsx
        │   │   ├── AgentStatusPanel.tsx
        │   │   ├── AgentStep.tsx
        │   │   ├── types.ts
        │   │   └── utils.tsx
        │   ├── abtesting/
        │   │   ├── ResultChart.tsx
        │   │   ├── TestDetail.tsx
        │   │   ├── TestForm.tsx
        │   │   ├── TestList.tsx
        │   │   ├── types.ts
        │   │   └── utils.ts
        │   └── attribution-traffic/
        │       ├── AttributionPanel.tsx
        │       ├── TrafficPanel.tsx
        │       ├── types.ts
        │       └── utils.ts
        ├── pages/
        │   ├── ABTesting.tsx
        │   ├── Agent.tsx          # Unused placeholder (not wired in App.tsx)
        │   ├── AgentLoop.tsx
        │   ├── AttributionTraffic.tsx
        │   ├── Dashboard.tsx
        │   └── RTBEngine.tsx
        ├── lib/
        │   └── apiClient.ts       # Axios instance for /api/v2 with JWT refresh
        ├── stores/
        │   └── authStore.ts       # Zustand auth store
        └── utils/
            ├── api.ts             # Envelope-unwrapping wrapper around apiClient
            ├── cn.ts              # tailwind-merge helper
            └── mockData.ts        # Fallback mock data
```

```
frontend/
├── playwright.config.ts         # Playwright e2e configuration
└── tests/
    └── e2e/
        └── auth.spec.ts         # End-to-end auth flow test
```

## Quick Start

### Local Development

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

The Vite dev server proxies `/api` requests to `http://localhost:8000`. The frontend API client uses `VITE_API_URL=/api/v2` by default, so all requests are routed under `/api/v2/*`.

### Docker

```bash
docker-compose up --build
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost`

The Docker Compose stack now uses PostgreSQL (`postgres:15-alpine`) and Redis (`redis:7-alpine`). The backend runs Alembic migrations on startup and seeds data only when tables are empty.

## Build and Test Commands

### Backend

```bash
cd backend
source venv/bin/activate      # Windows: venv\Scripts\activate

# Run tests
pytest tests/ -v

# Code formatting / linting
black app tests
isort app tests
flake8 app tests
mypy app
```

### Frontend

```bash
cd frontend
npm install

# Start dev server
npm run dev

# Production build
npm run build

# Preview production build
npm run preview

# Lint
npm run lint

# End-to-end tests (requires Playwright browsers; set PLAYWRIGHT_BASE_URL to override http://localhost:5173)
npm run test:e2e
```

## API Conventions

- All API responses are wrapped as `{code, message, data}` by `app.core.response.WrappedAPIRouter`.
- Exceptions are handled by `app.core.response.register_exception_handlers` and return the same envelope.
- Business-domain routers live in `app/api/` and are registered in `app/main.py`. V2 routers are mounted under `/api/v2/*`.
- Dashboard and traffic routers are also mounted under `/api/v2/*` for consistency.
- Simulation routers (`rtb_v2` `/simulate/*`, `agent_simulation`, `abtest_simulation`) expose the interactive, JWT-authenticated endpoints used by the frontend pages.
- Auth routes live in `app/api/auth.py` under `/api/v2/auth/*`; protected endpoints use `get_current_active_user`, `require_permission`, or `validate_api_key`.
- ORM primary keys use `uuid.UUID` with `default=uuid.uuid4`.
- `datetime` fields use `datetime.utcnow`.
- SQLAlchemy 2.0 style with `Mapped` / `mapped_column` type hints.
- RTB monetary values are stored as **per-impression** prices. CPM values are converted with `cpm / 1000` for storage and `price * 1000` for display.
- A/B test assignment uses consistent hashing (`hashlib.md5`) so the same user always sees the same variant; non-experiment traffic is routed to `control`.
- The attribution engine supports First Touch, Last Touch, Linear, Time Decay, Position Based, and Shapley approximation.
- The bidding agent follows a ReAct loop (`think -> act -> observe`) and each step is returned in a structured format for frontend visualization. The v2 agent can call OpenAI/Anthropic function calling with pgvector memory.

## Code Style Guidelines

- Python: format with **black**, import sort with **isort**, lint with **flake8**, type-check with **mypy**. Configurations are in `backend/pyproject.toml`.
- TypeScript: `strict: true` is enabled. Path alias `@/*` maps to `src/*`.
- Frontend uses a dark theme. Custom Tailwind colors are defined in `tailwind.config.js`: `primary`, `secondary`, `accent`, `success`, `warning`, `danger`, `muted`.
- Prefer functional React components and hooks; no class components are used.

## Testing Instructions

- Backend tests are in `backend/tests/test_api.py` and `backend/tests/test_v2.py` and use an in-memory SQLite database configured in `backend/tests/conftest.py`.
- `pytest.ini` sets `asyncio_mode = auto`.
- CI runs `pytest tests/ -v` for the backend and `npm run build` for the frontend.

## Deployment

- **CI/CD**: `.github/workflows/ci.yml` runs on pushes and pull requests to `main`. It installs Python dependencies and runs backend tests, then builds the frontend. It does not build or push Docker images and has no deploy stage.
- **Backend image**: `backend/Dockerfile` builds a multi-stage `python:3.11-slim` image, runs `alembic upgrade head`, and starts `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- **Frontend image**: `frontend/Dockerfile` builds the Vite app with `node:20-alpine` (default `VITE_API_URL=/api/v2`), then serves `dist/` with `nginx:alpine` using `frontend/nginx.conf`.
- **Nginx**: routes `/api/v2` to `http://backend:8000` and falls back to `index.html` for the SPA.
- **Database**: Docker Compose uses PostgreSQL with a persistent `pgdata` volume. Redis is available for caching/messaging. Local development still defaults to SQLite.

## Security Considerations

- Authentication and authorization are now implemented via JWT access/refresh tokens, RBAC permissions, and API keys (`app/core/security.py`, `app/services/auth_service.py`, `app/api/auth.py`).
- CORS origins are configurable via the `CORS_ORIGINS` environment variable. `docker-compose.yml` sets `CORS_ORIGINS=http://localhost,http://localhost:5173`; do not use wildcards in production.
- `SECRET_KEY` is used to sign JWTs; set a strong value in production.
- Uploaded files are stored under `backend/uploads/`.
- Treat `.env` values as sensitive and do not commit the file.

## Known Issues / Important Notes

1. **Model coexistence.** Legacy model names (`Auction`, `BidRecord`, `ABTest`, `ABTestVariant`) coexist with the new PostgreSQL-oriented tables (`AuctionRequest`, `AuctionBid`, `AuctionWin`, `Experiment`, `Variant`). Legacy endpoints use the old tables; v2 endpoints use the new tables.

2. **Runtime DB target.** `app/core/config.py` defaults to SQLite. PostgreSQL and Redis are wired in dependencies and configuration but are optional: Redis falls back to a no-op client and LLM calls fall back to deterministic output when no API key is configured.

3. **Alembic in Docker, auto-create in SQLite.** `app/main.py` skips `create_all()` when `USE_ALEMBIC=true` (Docker Compose) and expects `alembic upgrade head` to have run. SQLite local mode still auto-creates tables.

4. **Unused file.** `frontend/src/pages/Agent.tsx` exists but is not wired into `App.tsx`; `/agent` uses `AgentLoop.tsx`.

When modifying this project, keep the legacy/v2 model split in mind and decide whether the runtime target should remain SQLite or be migrated to PostgreSQL.
