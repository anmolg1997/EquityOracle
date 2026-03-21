# Application Layer

Use case orchestration — coordinates multiple domain contexts to fulfill user-level actions.

## Structure

```
application/
├── scanner/
│   ├── service.py        ScannerService: runs filter presets across the universe
│   ├── filter_spec.py    FilterSpec builder with 8 operators (GT, GTE, LT, BETWEEN, etc.)
│   └── presets.py        YAML preset loader (Minervini, CANSLIM, etc.)
├── recommender/
│   ├── service.py        RecommenderService: composite → signals → thesis
│   ├── debate.py         LLM-powered Bull/Bear/Synthesis debate (streamed via SSE)
│   └── audit.py          DecisionAudit recording
├── autonomy/
│   ├── controller.py     AutonomyController: per-engine levels + circuit breaker integration
│   ├── self_improve.py   SelfImprovementService: Bayesian weight adjustment with safeguards
│   ├── ab_testing.py     ABTestingService: shadow portfolio with statistical significance gate
│   └── pipeline.py       Full daily autonomous pipeline orchestration
├── ingestion/
│   ├── service.py        IngestionService: multi-provider data fetch
│   └── scheduler_jobs.py APScheduler job definitions
├── backtester/
│   ├── service.py        BacktesterService: historical strategy replay
│   └── vectorbt_adapter.py   VectorBT integration for vectorized backtesting
└── simulator/
    ├── service.py        SimulatorService: paper trading simulation
    └── event_loop.py     Event-driven simulation with daily tick
```

## Key Concepts

- **Application services never contain business rules.** They coordinate: "fetch data, pass to quality gate, pass to analysis, pass to recommender." The rules live in domain modules.
- **Scanner presets** are YAML files in `configs/scanners/`. Adding a new preset is a YAML file, not code.
- **The recommender** chains: composite scoring → signal generation → exit rules → optional LLM debate. Each step is independently testable.
- **The autonomy pipeline** is the daily autopilot: ingestion → quality → analysis → recommendation → risk check → execution → learning. Gated by circuit breaker and autonomy levels.
