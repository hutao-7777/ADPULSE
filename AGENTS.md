# AdPulse Agent Guide

## Project Overview

AdPulse is a full-stack demonstrative platform for programmatic advertising, covering RTB auction simulation, AI bidding agent decision loops, A/B testing, multi-touch attribution, and traffic quality monitoring.

## Tech Stack

### Backend

- Python 3.11+
- FastAPI + Pydantic v2
- SQLAlchemy 2.0 (async)
- SQLite (via `aiosqlite`)
- pydantic-settings
- SciPy + NumPy (A/B test inference)
- pytest + pytest-asyncio + httpx

### Frontend

- React 18
- TypeScript
- Vite
- React Router v6
- Tailwind CSS
- Recharts
- Lucide React
- clsx + tailwind-merge

## Directory Structure

```
backend/
├── .env
├── requirements.txt
├── Dockerfile
├── pytest.ini
├── venv/
├── uploads/
├── tests/
│   ├── conftest.py
│   └── test_api.py
└── app/
    ├── main.py
    ├── agent/
    │   ├── tools.py
    │   └── bidding_agent.py
    ├── api/
    │   ├── abtest.py
    │   ├── agent.py
    │   ├── attribution.py
    │   ├── dashboard.py
    │   ├── rtb.py
    │   └── traffic.py
    ├── core/
    │   ├── config.py
    │   ├── database.py
    │   ├── exceptions.py
    │   ├── response.py
    │   └── seed.py
    ├── models/
    │   └── models.py
    ├── schemas/
    │   ├── abtest.py
    │   ├── agent.py
    │   ├── attribution.py
    │   ├── dashboard.py
    │   ├── rtb.py
    │   └── traffic.py
    └── services/
        ├── ab_test_engine.py
        ├── attribution_engine.py
        ├── rtb_engine.py
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
    │   ├── AgentLoop.tsx
    │   ├── AttributionTraffic.tsx
    │   ├── Dashboard.tsx
    │   └── RTBEngine.tsx
    └── utils/
        ├── api.ts
        ├── cn.ts
        └── mockData.ts
```

## Quick Start

### Local development

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

The Vite dev server proxies `/api` requests to `http://localhost:8000`.

### Docker

```bash
docker-compose up --build
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

## API Conventions

- All ORM primary keys use `uuid.UUID` with `default=uuid.uuid4`.
- All `datetime` fields use `datetime.utcnow`.
- SQLAlchemy 2.0 style with `Mapped` / `mapped_column` type hints.
- Business-domain APIs live in `app/api/` and are registered in `app/main.py`.
- All API responses are wrapped as `{code, message, data}` by `app.core.response.WrappedAPIRouter`.
- Exceptions are handled by `app.core.response.register_exception_handlers` and return the same envelope.
- RTB monetary values are stored as **per-impression** prices. CPM values are converted with `cpm / 1000` for storage and `price * 1000` for display.
- A/B test assignment uses consistent hashing (`hashlib.md5`) so the same user always sees the same variant; non-experiment traffic is routed to `control`.
- The bidding agent follows a ReAct loop (`think -> act -> observe`) and each step is returned in a structured format for frontend visualization.
- Frontend uses a dark theme with custom Tailwind colors: `primary`, `secondary`, `accent`, `success`, `warning`, `danger`, `muted`.
