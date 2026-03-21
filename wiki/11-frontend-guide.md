# Frontend Guide

> **Location:** `frontend/src/`
>
> **Stack:** React 18 + TypeScript 5 + Vite 6 + Tailwind CSS + TradingView Charts

## Architecture

The frontend is a single-page application with feature-based folder organization:

```
src/
├── app/
│   ├── App.tsx              # Root component, providers, layout
│   └── router.tsx           # React Router routes
├── features/                # One folder per page
│   ├── command-center/      # Dashboard
│   ├── scanner/             # Stock screener
│   ├── recommendations/     # Signal feed
│   ├── deep-dive/           # Single stock analysis
│   ├── portfolio/           # Paper trading portfolio
│   ├── performance/         # Performance analytics
│   └── settings/            # Configuration
└── shared/                  # Cross-cutting concerns
    ├── api/client.ts        # Axios HTTP client
    ├── hooks/               # useSSE, useWebSocket
    ├── stores/              # Zustand state management
    ├── components/          # Sidebar navigation
    └── types/index.ts       # Shared TypeScript interfaces
```

## Pages

### Command Center (`/`)
The main dashboard showing system health at a glance:
- **Circuit Breaker Indicator** — Color-coded status (green/amber/red/black) with explanation
- **Quick Stats** — Today's scan count, active recommendations, portfolio value
- **Market Breadth** — Advances vs. declines, stocks above key moving averages
- **Recent Alerts** — Latest circuit breaker transitions and data quality warnings

### Scanner (`/scanner`)
Interactive stock screener:
- Preset selector (Minervini, CANSLIM, Momentum Breakout, Deep Value)
- Virtualized table showing results (handles 500+ rows smoothly via TanStack Virtual)
- Columns: rank, ticker, overall score, technical/fundamental/sentiment breakdown, confidence
- Click any row to navigate to Deep Dive

### Recommendations (`/recommendations`)
Signal feed sorted by strength:
- Filter by horizon (1d / 3d / 1w / 1m / 3m)
- Filter by direction (BUY / SELL / HOLD)
- Each card shows: ticker, direction, expected return, confidence, independent signal count
- Exit rules listed per recommendation

### Deep Dive (`/deep-dive/:ticker`)
Single stock analysis page:
- **TradingView Chart** — Candlestick with volume, configurable indicators (SMA, EMA, BB)
- **Factor Breakdown** — Radar chart of momentum/quality/value scores
- **AI Thesis** — LLM-generated thesis streamed via SSE
- **Exit Rules** — Visual stop-loss levels on the chart
- **Recent Signals** — Historical signals and their outcomes

### Portfolio (`/portfolio`)
Paper trading dashboard:
- Cash, total value, gross P&L, net P&L
- Open positions with current prices, unrealized P&L
- Closed positions with holding period, realized P&L
- Cost decomposition — total costs, slippage, tax estimates
- Gross vs. net performance overlay chart

### Performance (`/performance`)
Analytics page:
- Equity curve (portfolio value over time)
- Drawdown chart
- Win rate, profit factor, Sharpe ratio
- Provider health panel — shows which data sources are up/down

### Settings (`/settings`)
Configuration:
- Market selection (India, US, Global)
- Autonomy levels per engine
- Risk parameters (max position size, max drawdown thresholds)
- LLM budget cap and provider preferences

## State Management

### Server State — TanStack Query
All data from the backend is managed by TanStack Query (React Query):
- Automatic caching and deduplication
- Stale-while-revalidate — show cached data immediately, refresh in background
- Prefetching — hover over a scan result to prefetch its deep-dive data
- Automatic retry on failure

### Client State — Zustand
Minimal client-only state:
- `portfolioStore` — selected portfolio, active tab
- `settingsStore` — market preference, autonomy config, risk parameters

Why Zustand over Redux: the client state is small (~10 fields). Zustand's no-boilerplate API matches the actual complexity.

## Real-Time Features

### Server-Sent Events (SSE)
Used for streaming LLM output:
- Bull/Bear debate text streams token-by-token to the Deep Dive page
- Thesis generation progressively appears
- `useSSE` hook handles connection lifecycle, reconnection, and cleanup

### WebSocket
Used for live portfolio updates:
- Position price updates
- Circuit breaker state changes
- `useWebSocket` hook with automatic reconnection

## UI Design

- **Dark theme** — designed for extended use (market analysis sessions)
- **Tailwind CSS** — utility-first styling, no custom CSS files
- **Framer Motion** — smooth page transitions and component animations
- **Responsive** — works on desktop and tablet (not optimized for phone — financial dashboards need screen space)
- **Skeleton loading** — content placeholders while data loads, not empty screens

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `@tanstack/react-query` | Server state, caching, background refresh |
| `@tanstack/react-table` | Headless table with sorting, filtering |
| `@tanstack/react-virtual` | Virtualized rendering for large lists |
| `lightweight-charts` | TradingView candlestick charts |
| `recharts` | Equity curves, drawdown charts |
| `zustand` | Client state management |
| `framer-motion` | Animations and transitions |
| `lucide-react` | Icon library |
| `axios` | HTTP client with interceptors |

## Development

```bash
cd frontend
npm install
npm run dev          # Start dev server on :5173
npx tsc --noEmit     # Type check without building
npm run build        # Production build
npm run preview      # Preview production build
```

The dev server proxies `/api` to `http://localhost:8000` (the FastAPI backend).
