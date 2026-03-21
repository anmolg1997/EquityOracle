# Frontend

React SPA for the EquityOracle dashboard — scans, recommendations, portfolio, and system monitoring.

## Structure

```
src/
├── app/
│   ├── App.tsx              Root component with providers and layout
│   └── router.tsx           React Router configuration
├── features/                Page-level feature modules
│   ├── command-center/      Dashboard: circuit breaker, quick stats, breadth
│   ├── scanner/             Stock screener with preset filters
│   ├── recommendations/     Signal feed with horizon/direction filters
│   ├── deep-dive/           Single stock: chart, factors, AI thesis
│   ├── portfolio/           Paper trading: positions, P&L, costs
│   ├── performance/         Equity curve, drawdown, win rate
│   └── settings/            Market, autonomy, risk configuration
└── shared/
    ├── api/client.ts        Axios client with base URL and interceptors
    ├── hooks/useSSE.ts      Server-Sent Events hook (LLM streaming)
    ├── hooks/useWebSocket.ts WebSocket hook (live portfolio updates)
    ├── stores/              Zustand stores (portfolio, settings)
    ├── components/          Sidebar navigation
    └── types/index.ts       Shared TypeScript interfaces
```

## Running

```bash
npm install
npm run dev          # Dev server → http://localhost:5173
npm run build        # Production build
npx tsc --noEmit     # Type check
```

## Tech Stack

| Tool | Purpose |
|------|---------|
| React 18 | UI framework |
| TypeScript 5 | Type safety |
| Vite 6 | Build tool |
| Tailwind CSS | Utility-first styling |
| TanStack Query | Server state + caching |
| TanStack Table + Virtual | Tables with virtualized rendering |
| Zustand | Client state management |
| lightweight-charts | TradingView candlestick charts |
| Recharts | Equity curves, analytics charts |
| Framer Motion | Animations |
| Axios | HTTP client |

## API Proxy

The Vite dev server proxies `/api` requests to `http://localhost:8000`. Configure in `vite.config.ts`.
