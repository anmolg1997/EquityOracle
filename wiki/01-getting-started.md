# Getting Started

## Prerequisites

| Tool | Version | Why |
|------|---------|-----|
| Python | 3.12+ | Backend runtime |
| Node.js | 18+ | Frontend build |
| Docker + Docker Compose | Latest | PostgreSQL, Redis, full stack |
| Git | Any | Version control |

Optional:
- **Ollama** — For free local LLM (thesis generation without API costs)
- **Gemini API key** — For cloud LLM features (debate, natural language scanning)

## Option A: Docker (Full Stack)

The simplest way to run everything:

```bash
git clone https://github.com/anmolg1997/EquityOracle.git
cd EquityOracle

# Copy environment template
cp .env.example .env
# Edit .env to add API keys (optional for basic functionality)

# Start all services
docker compose up -d

# Check status
docker compose ps
```

This starts:
- **PostgreSQL 16** with TimescaleDB on port 5432
- **Redis 7** on port 6379
- **Backend** (FastAPI) on port 8000
- **Frontend** (Vite) on port 5173

Visit `http://localhost:5173` to open the UI.

## Option B: Local Development

### Backend

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows

# Install with dev dependencies
pip install -e ".[dev]"

# Verify installation
pytest tests/ -v
# Expected: 300 passed

# Start the API server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

npm install
npm run dev
# → http://localhost:5173
```

### Infrastructure (needed for full features)

```bash
# PostgreSQL with TimescaleDB
docker run -d --name equityoracle-db \
  -e POSTGRES_DB=equityoracle \
  -e POSTGRES_USER=equityoracle \
  -e POSTGRES_PASSWORD=changeme \
  -p 5432:5432 \
  timescale/timescaledb:latest-pg16

# Redis
docker run -d --name equityoracle-redis \
  -p 6379:6379 \
  redis:7-alpine
```

## Environment Variables

Key variables in `.env`:

```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=equityoracle
POSTGRES_USER=equityoracle
POSTGRES_PASSWORD=changeme

# Redis
REDIS_URL=redis://localhost:6379/0

# LLM (optional — system works without these)
LLM_GEMINI_API_KEY=your_key_here
LLM_DAILY_BUDGET_INR=50.0

# Data sources (optional — yfinance works without keys)
ALPHA_VANTAGE_API_KEY=your_key
NEWSAPI_KEY=your_key
```

## Verifying Your Setup

### Backend health check
```bash
curl http://localhost:8000/health
# {"status":"healthy","service":"equityoracle","version":"0.1.0"}
```

### Run the test suite
```bash
cd backend && source .venv/bin/activate
pytest tests/ -v --tb=short
```

### TypeScript check
```bash
cd frontend
npx tsc --noEmit
# Should exit with 0 errors
```

### Production build
```bash
cd frontend
npm run build
# Should complete with no errors
```

## What to Do First

1. **Explore the Command Center** — Visit `http://localhost:5173`. The dashboard shows circuit breaker status, quick stats, and market overview.

2. **Run a scan** — Go to the Scanner page and try a preset like "Minervini Trend Template" or "CANSLIM".

3. **Read How It Works** — [wiki/02-how-it-works.md](02-how-it-works.md) walks through the full data → recommendation pipeline.

4. **Look at the tests** — `backend/tests/` is the best way to understand what each module actually does. Start with `tests/integration/test_recommendation_pipeline.py`.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: app` | Make sure you ran `pip install -e ".[dev]"` from `backend/` |
| Database connection error | Start PostgreSQL via Docker or update `.env` |
| Redis connection error | Start Redis via Docker or the system degrades gracefully |
| `pandas-ta` install fails | Try `pip install pandas-ta==0.3.14b1` explicitly |
| Frontend blank page | Check that the backend is running on port 8000 |
