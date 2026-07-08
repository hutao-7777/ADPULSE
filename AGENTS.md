# AdPulse Agent Guide

## Project Overview

AdPulse is a production-grade programmatic advertising platform covering RTB auction simulation, AI bidding agent decision loops, A/B testing, multi-touch attribution, and traffic quality monitoring.

## Tech Stack

### Backend

- Python 3.11+
- FastAPI + Pydantic v2
- SQLAlchemy 2.0 (async) + Alembic migrations
- PostgreSQL 15+ (production) with `pgvector` extension
- Redis 7+ (cache, distributed locks, rate limiting)
- pydantic-settings
- python-jose + passlib (JWT, password hashing)
- OpenAI / Anthropic (real LLM API, function calling)
- SciPy + NumPy + statsmodels (A/B test inference, power analysis)
- pytest + pytest-asyncio + httpx + pytest-cov + testcontainers
- black + isort + flake8 + mypy + pre-commit

### Frontend

- React 18
- TypeScript
- Vite
- React Router v6
- Zustand (state management)
- TanStack Query (server state)
- Tailwind CSS
- Recharts
- Lucide React
- clsx + tailwind-merge

## Directory Structure

```
backend/
├── alembic/
│   ├── versions/
│   └── env.py
├── .env
├── .env.example
├── requirements.txt
├── Dockerfile
├── pytest.ini
├── venv/
├── uploads/
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── perf/
└── app/
    ├── main.py
    ├── agent/
    │   ├── tools.py
    │   └── bidding_agent.py
    ├── api/
    │   ├── auth.py
    │   ├── abtest.py
    │   ├── agent.py
    │   ├── attribution.py
    │   ├── dashboard.py
    │   ├── rtb.py
    │   └── traffic.py
    ├── core/
    │   ├── config.py
    │   ├── database.py
    │   ├── redis.py
    │   ├── security.py
    │   ├── exceptions.py
    │   ├── response.py
    │   └── seed.py
    ├── models/
    │   └── models.py
    ├── schemas/
    │   ├── auth.py
    │   ├── abtest.py
    │   ├── agent.py
    │   ├── attribution.py
    │   ├── dashboard.py
    │   ├── rtb.py
    │   └── traffic.py
    └── services/
        ├── auth_service.py
        ├── rtb_engine.py
        ├── ab_test_engine.py
        ├── attribution_engine.py
        ├── bidding_agent.py
        └── traffic_quality_engine.py

frontend/
├── index.html
├── package.json
├── Dockerfile
├── nginx.conf
├── postcss.config.js
├── tailwind.config.js
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── index.css
    ├── components/
    │   ├── Layout.tsx
    │   ├── ErrorBoundary.tsx
    │   ├── LoadingSkeleton.tsx
    │   ├── ProtectedRoute.tsx
    │   ├── agent/
    │   ├── abtesting/
    │   ├── attribution-traffic/
    │   └── rtb/
    ├── features/
    │   ├── auth/
    │   ├── rtb/
    │   ├── abtest/
    │   ├── attribution/
    │   └── agent/
    ├── pages/
    │   ├── Login.tsx
    │   ├── Dashboard.tsx
    │   ├── RTBEngine.tsx
    │   ├── ABTesting.tsx
    │   ├── AttributionTraffic.tsx
    │   └── AgentLoop.tsx
    ├── hooks/
    ├── stores/
    ├── utils/
    │   ├── api.ts
    │   ├── cn.ts
    │   └── mockData.ts
```

## Quick Start

### Local development

Prerequisites: PostgreSQL 15+ and Redis 7+ running locally.

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # update DATABASE_URL, REDIS_URL, SECRET_KEY, etc.
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

The Vite dev server proxies `/api` requests to `http://localhost:8000`.

### Docker

```bash
docker-compose up --build
```

- App: `http://localhost:8000`
- Frontend: `http://localhost:5173`

## API Conventions

- All ORM primary keys use `uuid.UUID` with `default=uuid.uuid4`.
- All `datetime` fields use `datetime.utcnow`.
- SQLAlchemy 2.0 style with `Mapped` / `mapped_column` type hints.
- Database schema is managed exclusively by Alembic; `Base.metadata.create_all` is forbidden in production.
- Business-domain APIs live in `app/api/` and are registered in `app/main.py`.
- All API responses are wrapped as `{code, message, data}` by `app.core.response.WrappedAPIRouter`.
- Exceptions are handled by `app.core.response.register_exception_handlers` and return the same envelope.
- Authentication uses JWT Access Token + Refresh Token; RTB endpoints additionally require an API Key.
- CORS is whitelist-only; `allow_origins=["*"]` is not permitted.
- RTB monetary values are stored as **per-impression** prices. CPM values are converted with `cpm / 1000` for storage and `price * 1000` for display.
- A/B test assignment uses consistent hashing `hash(user_id + experiment_id) % 100` so the same user always sees the same variant; non-experiment traffic is routed to `control`.
- The attribution engine records ordered touchpoint sequences and uses Monte Carlo permutation sampling (`n=10000`) to approximate Shapley Values.
- The bidding agent follows a ReAct loop (`think -> act -> observe`) backed by a real LLM with function calling and pgvector long-term memory.
- Frontend uses a dark theme with custom Tailwind colors: `primary`, `secondary`, `accent`, `success`, `warning`, `danger`, `muted`.
