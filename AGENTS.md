# AdPulse Agent Guide

## Project Overview

AdPulse is an AI-powered programmatic advertising intelligent optimization platform.

## Tech Stack

### Backend

- Python 3.11+
- FastAPI
- SQLAlchemy 2.0 (async)
- SQLite (via `aiosqlite`)
- Pydantic v2 / pydantic-settings
- PyTorch + torchvision (ResNet-50 creative scoring)
- SciPy + NumPy (A/B test inference)

### Frontend

- React 18
- TypeScript
- Vite
- React Router v6
- Tailwind CSS
- Recharts
- Lucide React

## Directory Structure

```
backend/
├── .env
├── requirements.txt
├── venv/
├── uploads/
└── app/
    ├── main.py
    ├── agent/
    │   ├── tools.py
    │   └── bidding_agent.py
    ├── api/
    │   ├── abtest.py
    │   ├── agent.py
    │   ├── creatives.py
    │   ├── dashboard.py
    │   └── rtb.py
    ├── core/
    │   ├── config.py
    │   └── database.py
    ├── models/
    │   └── models.py
    ├── schemas/
    │   ├── abtest.py
    │   ├── agent.py
    │   ├── creative.py
    │   ├── dashboard.py
    │   └── rtb.py
    └── services/
        ├── ab_test_engine.py
        ├── creative_scorer.py
        ├── fatigue_predictor.py
        └── rtb_engine.py

frontend/
├── index.html
├── package.json
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
    │   └── Layout.tsx
    ├── pages/
    │   ├── Dashboard.tsx
    │   ├── RTB.tsx
    │   ├── Creatives.tsx
    │   ├── ABTesting.tsx
    │   └── Agent.tsx
    └── utils/
        └── api.ts
```

## Quick Start

### Backend

```bash
cd backend
source venv/Scripts/activate
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

The Vite dev server proxies `/api` requests to `http://localhost:8000`.

## Conventions

- All ORM primary keys use `uuid.UUID` with `default=uuid.uuid4`.
- All `datetime` fields use `datetime.utcnow`.
- SQLAlchemy 2.0 style with `Mapped` / `mapped_column` type hints.
- AI services run on CPU by default.
- Business-domain APIs live in `app/api/` and are registered in `app/main.py`.
- RTB monetary values are stored as **per-impression** prices. CPM values are
  converted with `cpm / 1000` for storage and `price * 1000` for display.
- A/B test assignment uses consistent hashing (`hashlib.md5`) so the same user
  always sees the same variant; non-experiment traffic is routed to `control`.
- The bidding agent follows a ReAct loop (`think -> act -> observe`) and each
  step is returned in a structured format for frontend visualization.
- Frontend uses a dark theme with custom Tailwind colors: `primary`,
  `secondary`, `accent`, `success`, `warning`, `danger`, `muted`.
