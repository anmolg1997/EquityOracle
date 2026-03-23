import { Component, type ReactNode, useCallback, useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { fetcher } from '@/shared/api/client';

interface ScanDiagnostics {
  composite: {
    overall: number;
    technical: number;
    fundamental: number;
    effective_signals: number;
    confidence: string;
  };
  technical: {
    score: number;
    rsi_14: number | null;
    macd_histogram: number | null;
    adx_14: number | null;
    volume_ratio: number | null;
    rs_rating: number | null;
    obv_trend: string;
  };
  factor: {
    composite: number;
    momentum_score: number;
    quality_score: number;
    value_score: number;
    momentum_details?: Record<string, number | string | null>;
    quality_details?: Record<string, number | string | null>;
    value_details?: Record<string, number | string | null>;
  };
  preset: {
    selected: string | null;
    passed: boolean;
    matched_presets: string[];
  };
  forecast?: ForecastPayload;
  timeline?: Record<string, string | boolean | null>;
}

interface PipelineSteps {
  universe_selected?: boolean;
  ohlcv_source?: string;
  fundamentals_source?: string;
  technical_computed?: boolean;
  factor_computed?: boolean;
  composite_computed?: boolean;
  preset_evaluated?: boolean;
  preset_passed?: boolean;
}

interface ContributionBreakdown {
  inputs?: {
    technical: number;
    fundamental: number;
    sentiment: number;
    ml_prediction: number;
  };
  weights?: {
    technical: number;
    fundamental: number;
    sentiment: number;
    ml_prediction: number;
  };
  weighted_contributions?: {
    technical: number;
    fundamental: number;
    sentiment: number;
    ml_prediction: number;
  };
  overall?: number;
  overall_adaptive_preview?: number;
  adaptive_weighting_enabled?: boolean;
  explainers?: string[];
}

interface ForecastScenario {
  id: 'bear' | 'base' | 'bull' | 'stretch';
  label: string;
  probability: number;
  expected_return: number;
  mean_reversion_risk?: boolean;
}

interface ForecastPayload {
  model: string;
  horizon_days: number;
  sample_size: number;
  distribution?: {
    mean_return?: number;
    std_return?: number;
    q20?: number;
    q50?: number;
    q80?: number;
  };
  regime?: {
    current?: string;
    p_up_next?: number;
    p_down_next?: number;
  };
  scenarios?: ForecastScenario[];
}

interface ScanResult {
  rank: number;
  ticker: string;
  overall_score: number;
  technical_score: number;
  fundamental_score: number;
  effective_signals: number;
  confidence: string;
  passed_presets: string[];
  pipeline_steps?: PipelineSteps;
  sparkline?: number[];
  forecast?: ForecastPayload;
  contribution_breakdown?: ContributionBreakdown;
  diagnostics?: ScanDiagnostics;
}

interface ScanResponse {
  count: number;
  market: string;
  preset: string | null;
  meta?: {
    source?: string;
    cache_schema?: string;
  };
  results: ScanResult[];
}

const SCAN_TIMEOUT = 10 * 60 * 1000;
const SCAN_STORAGE_KEY = 'equityoracle:last-scan-results';
const SCAN_STORAGE_VERSION = 3;

function loadSavedScan(): ScanResponse | null {
  try {
    const raw = localStorage.getItem(SCAN_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as
      | { version: number; data: ScanResponse }
      | ScanResponse;

    if ('version' in parsed && 'data' in parsed) {
      if (parsed.version !== SCAN_STORAGE_VERSION) return null;
      if (!parsed.data || !Array.isArray(parsed.data.results)) return null;
      return parsed.data;
    }

    // Discard legacy payloads that do not include diagnostics.
    if (!parsed || !Array.isArray(parsed.results)) return null;
    if (!parsed.results[0]?.diagnostics) return null;
    return parsed;
  } catch {
    return null;
  }
}

class ScannerErrorBoundary extends Component<
  { children: ReactNode; onReset: () => void },
  { error: Error | null }
> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error) {
    console.error('[ScannerPage] Render error:', error);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="bg-red-950/30 border border-red-900/50 rounded-lg px-4 py-3 mt-4">
          <p className="text-sm text-red-400 font-medium">Rendering error</p>
          <p className="text-xs text-red-500/80 mt-1 font-mono">{this.state.error.message}</p>
          <button
            onClick={() => {
              this.setState({ error: null });
              this.props.onReset();
            }}
            className="mt-2 text-xs text-red-400 hover:text-red-300 underline underline-offset-2"
          >
            Reset and retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

function safeFixed(val: unknown, digits = 1): string {
  if (val == null || typeof val !== 'number' || Number.isNaN(val)) return '—';
  return val.toFixed(digits);
}

function confidenceClass(level: string): string {
  if (level === 'high') return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
  if (level === 'medium') return 'bg-amber-500/20 text-amber-300 border-amber-500/30';
  return 'bg-gray-700/60 text-gray-300 border-gray-600/50';
}

function scoreColor(score: number): string {
  if (score >= 70) return 'text-emerald-400';
  if (score >= 50) return 'text-brand-300';
  if (score >= 30) return 'text-amber-400';
  return 'text-red-400';
}

function ScorePill({ score }: { score: number | null | undefined }) {
  if (score == null || Number.isNaN(score)) {
    return <span className="text-xs text-gray-600">—</span>;
  }
  const pct = Math.min(Math.max(score, 0), 100);
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            pct >= 70 ? 'bg-emerald-500' : pct >= 50 ? 'bg-brand-500' : pct >= 30 ? 'bg-amber-500' : 'bg-red-500'
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`font-mono text-xs ${scoreColor(score)}`}>{score.toFixed(1)}</span>
    </div>
  );
}

function SignalBar({ label, value }: { label: string; value: number | null | undefined }) {
  if (value == null || Number.isNaN(value)) {
    return (
      <div className="space-y-1">
        <p className="text-[10px] uppercase tracking-wide text-gray-500">{label}</p>
        <p className="text-xs text-gray-600">N/A</p>
      </div>
    );
  }
  const pct = Math.min(Math.max(value, 0), 100);
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <p className="text-[10px] uppercase tracking-wide text-gray-500">{label}</p>
        <p className="text-xs font-mono text-gray-300">{value.toFixed(1)}</p>
      </div>
      <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${
            pct >= 70 ? 'bg-emerald-500' : pct >= 50 ? 'bg-brand-500' : pct >= 30 ? 'bg-amber-500' : 'bg-red-500'
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function Sparkline({ data, className }: { data?: number[]; className?: string }) {
  if (!data || data.length < 2) {
    return <div className={`h-8 rounded bg-gray-900/40 ${className ?? ''}`} />;
  }
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * 100;
      const y = 100 - ((v - min) / range) * 100;
      return `${x},${y}`;
    })
    .join(' ');
  const first = data[0] ?? 0;
  const last = data[data.length - 1] ?? first;
  const positive = last >= first;
  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className={className ?? 'h-8 w-full'}>
      <polyline
        fill="none"
        stroke={positive ? '#22c55e' : '#f59e0b'}
        strokeWidth="3"
        points={points}
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

function FutureProjectionFlow({ result }: { result: ScanResult }) {
  const [hoveredPath, setHoveredPath] = useState<string | null>(null);
  const history = (result.sparkline && result.sparkline.length >= 4 ? result.sparkline : []).slice(-12);
  const historyFirst = history[0] ?? 100;
  const historyLast = history[history.length - 1] ?? historyFirst;
  const forecast = result.forecast;
  const scenarios = forecast?.scenarios ?? [];
  const toPct = (v: number | undefined) => (v == null || Number.isNaN(v) ? '—' : `${(v * 100).toFixed(1)}%`);
  const quantiles = forecast?.distribution;

  const scenarioStyles: Record<string, { color: string; meaning: string; how: string }> = {
    bear: {
      color: '#ef4444',
      meaning: 'Downside regime dominates over horizon.',
      how: 'Estimated from historical forward-return tails and regime transition state.',
    },
    base: {
      color: '#eab308',
      meaning: 'Balanced path around central tendency.',
      how: 'Driven by median historical outcomes adjusted by current regime probability.',
    },
    bull: {
      color: '#22c55e',
      meaning: 'Positive continuation with supportive trend state.',
      how: 'Reflects upper-mid return cluster when trend/factor context stays constructive.',
    },
    stretch: {
      color: '#10b981',
      meaning: 'Low-frequency upside extension.',
      how: 'Represents tail upside scenarios from empirical return history.',
    },
  };
  const defaultScenarioStyle = scenarioStyles.base ?? {
    color: '#eab308',
    meaning: 'Balanced path around central tendency.',
    how: 'Driven by median historical outcomes adjusted by current regime probability.',
  };

  const scenarioPaths = scenarios.map((scenario) => {
    const terminal = historyLast * (1 + scenario.expected_return);
    const points: number[] = [];
    for (let i = 1; i <= 8; i += 1) {
      const ratio = i / 8;
      points.push(historyLast + (terminal - historyLast) * ratio);
    }
    const style = scenarioStyles[scenario.id] ?? defaultScenarioStyle;
    return { ...scenario, points, color: style.color, meaning: style.meaning, how: style.how };
  });

  const q20Terminal = quantiles?.q20 != null ? historyLast * (1 + quantiles.q20) : null;
  const q50Terminal = quantiles?.q50 != null ? historyLast * (1 + quantiles.q50) : null;
  const q80Terminal = quantiles?.q80 != null ? historyLast * (1 + quantiles.q80) : null;

  const quantileTrails = [q20Terminal, q50Terminal, q80Terminal]
    .map((q) => {
      if (q == null) return null;
      const points: number[] = [];
      for (let i = 1; i <= 8; i += 1) {
        const ratio = i / 8;
        points.push(historyLast + (q - historyLast) * ratio);
      }
      return points;
    })
    .filter((trail): trail is number[] => Boolean(trail));

  const allValues = [...history, ...scenarioPaths.flatMap((s) => s.points), ...quantileTrails.flat()];
  const min = allValues.length ? Math.min(...allValues) : historyLast - 1;
  const max = allValues.length ? Math.max(...allValues) : historyLast + 1;
  const range = max - min || 1;
  const mapY = (value: number) => 132 - ((value - min) / range) * 104;

  const historyPoints = history
    .map((value, idx) => {
      const x = (idx / Math.max(history.length - 1, 1)) * 42 + 6;
      return `${x},${mapY(value).toFixed(2)}`;
    })
    .join(' ');

  const hovered = scenarioPaths.find((s) => s.id === hoveredPath) ?? null;

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-950/30 p-3 space-y-3">
      <p className="text-xs font-semibold text-gray-300 uppercase tracking-wide">Future Direction Flow</p>
      <svg viewBox="0 0 100 140" className="w-full h-40 rounded-md bg-gray-950/70 border border-gray-800/70">
        <line x1="48" y1="12" x2="48" y2="134" stroke="#374151" strokeDasharray="2 2" />
        {history.length > 1 && (
          <polyline
            points={historyPoints}
            fill="none"
            stroke="#38bdf8"
            strokeWidth="1.8"
            vectorEffect="non-scaling-stroke"
            strokeLinecap="round"
          />
        )}
        {quantileTrails.map((trail, idx) => {
          const label = idx === 0 ? 'Q20' : idx === 1 ? 'Q50' : 'Q80';
          const points = trail
            .map((value, i) => `${48 + ((i + 1) / trail.length) * 45},${mapY(value).toFixed(2)}`)
            .join(' ');
          return (
            <polyline
              key={label}
              points={`48,${mapY(historyLast).toFixed(2)} ${points}`}
              fill="none"
              stroke="#94a3b8"
              strokeWidth="1.1"
              strokeDasharray={idx === 1 ? '4 2' : '2 2'}
              strokeOpacity="0.55"
              vectorEffect="non-scaling-stroke"
            >
              <title>{`${label} projected quantile`}</title>
            </polyline>
          );
        })}
        {scenarioPaths.map((scenario) => {
          const points = scenario.points
            .map((value, idx) => {
              const x = 48 + ((idx + 1) / scenario.points.length) * 45;
              return `${x},${mapY(value).toFixed(2)}`;
            })
            .join(' ');
          const endX = 93;
          const endY = mapY(scenario.points[scenario.points.length - 1] ?? historyLast);
          return (
            <g key={scenario.id}>
              <polyline
                points={`48,${mapY(historyLast).toFixed(2)} ${points}`}
                fill="none"
                stroke={scenario.color}
                strokeWidth={hoveredPath === scenario.id ? '2.6' : '1.7'}
                strokeOpacity={hoveredPath && hoveredPath !== scenario.id ? '0.35' : '0.95'}
                vectorEffect="non-scaling-stroke"
                strokeLinecap="round"
                onMouseEnter={() => setHoveredPath(scenario.id)}
                onMouseLeave={() => setHoveredPath(null)}
              >
                <title>{`${scenario.label}: ${scenario.meaning}`}</title>
              </polyline>
              <circle
                cx={endX}
                cy={endY}
                r={hoveredPath === scenario.id ? '1.9' : '1.5'}
                fill={scenario.color}
                onMouseEnter={() => setHoveredPath(scenario.id)}
                onMouseLeave={() => setHoveredPath(null)}
              >
                <title>{`${scenario.label} endpoint`}</title>
              </circle>
            </g>
          );
        })}
      </svg>
      <div className="flex flex-wrap items-center gap-2">
        {scenarioPaths.map((scenario) => (
          <button
            key={scenario.id}
            type="button"
            className={`px-2 py-1 rounded border text-[11px] transition-colors ${
              hoveredPath === scenario.id
                ? 'border-brand-500/60 bg-brand-500/10 text-brand-200'
                : 'border-gray-700 bg-gray-900/60 text-gray-400 hover:border-gray-600'
            }`}
            style={{ boxShadow: hoveredPath === scenario.id ? `inset 0 0 0 1px ${scenario.color}55` : undefined }}
            onMouseEnter={() => setHoveredPath(scenario.id)}
            onMouseLeave={() => setHoveredPath(null)}
            title={`${scenario.label}: ${scenario.meaning}`}
          >
            <span className="inline-block w-2 h-2 rounded-full mr-1.5 align-middle" style={{ backgroundColor: scenario.color }} />
            <span className="align-middle">{scenario.label} {toPct(scenario.probability)}</span>
          </button>
        ))}
      </div>
      <div className="rounded border border-gray-800/80 bg-gray-950/60 px-2 py-2 text-[11px] text-gray-400 min-h-[3.25rem]">
        {!forecast || !scenarioPaths.length ? (
          <p>Forecast unavailable for this ticker (insufficient historical sample).</p>
        ) : !hovered ? (
          <p>
            Hover a projected line to inspect probability and rationale. Model: {forecast.model}, sample size {forecast.sample_size}.
          </p>
        ) : (
          <>
            <p className="text-gray-200">{hovered.label}</p>
            <p className="mt-0.5">
              Probability {toPct(hovered.probability)} · Expected return {toPct(hovered.expected_return)}
            </p>
            <p className="mt-0.5">{hovered.meaning}</p>
            <p className="mt-0.5 text-gray-500">{hovered.how}</p>
            <p className="mt-0.5 text-gray-500">
              Regime: {forecast.regime?.current ?? 'n/a'} · P(up next) {toPct(forecast.regime?.p_up_next)}
            </p>
          </>
        )}
      </div>
    </div>
  );
}

function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-950/40 px-3 py-2">
      <p className="text-[10px] uppercase tracking-wide text-gray-500">{label}</p>
      <p className="mt-1 text-sm font-mono text-gray-200">{value}</p>
    </div>
  );
}

function ForecastCell({ forecast }: { forecast?: ForecastPayload }) {
  if (!forecast?.scenarios?.length) {
    return <span className="text-xs text-gray-600">N/A</span>;
  }
  const top = [...forecast.scenarios].sort((a, b) => b.probability - a.probability)[0];
  if (!top) return <span className="text-xs text-gray-600">N/A</span>;

  const detail = forecast.scenarios
    .map((s) => `${s.label}: ${(s.probability * 100).toFixed(1)}% (${(s.expected_return * 100).toFixed(1)}%)`)
    .join(' | ');
  const quant = forecast.distribution;
  const meta = `Q20 ${quant?.q20 != null ? (quant.q20 * 100).toFixed(1) : '—'}% · Q50 ${
    quant?.q50 != null ? (quant.q50 * 100).toFixed(1) : '—'
  }% · Q80 ${quant?.q80 != null ? (quant.q80 * 100).toFixed(1) : '—'}% · n=${forecast.sample_size}`;

  return (
    <div className="inline-flex items-center gap-1.5" title={`${detail}\n${meta}`}>
      <span className="text-xs text-gray-200">{top.label.replace(' path', '')}</span>
      <span className="text-[11px] font-mono text-brand-300">{(top.probability * 100).toFixed(1)}%</span>
      <span className={`text-[11px] font-mono ${top.expected_return >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
        {(top.expected_return * 100).toFixed(1)}%
      </span>
    </div>
  );
}

function FlowNode({
  icon,
  value,
  subvalue,
  tooltip,
  tone = 'neutral',
}: {
  icon: string;
  value: string;
  subvalue?: string;
  tooltip: string;
  tone?: 'neutral' | 'good' | 'warn';
}) {
  const toneClass =
    tone === 'good'
      ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
      : tone === 'warn'
        ? 'border-amber-500/30 bg-amber-500/10 text-amber-300'
        : 'border-gray-700 bg-gray-900/60 text-gray-300';
  return (
    <div
      title={tooltip}
      className={`rounded-lg border px-2 py-2 min-w-[6rem] text-center transition-colors hover:border-brand-500/60 ${toneClass}`}
    >
      <p className="text-[14px] leading-none">{icon}</p>
      <p className="mt-1 text-sm font-mono font-semibold">{value}</p>
      {subvalue && <p className="text-[10px] text-gray-500 mt-0.5">{subvalue}</p>}
    </div>
  );
}

function SkeletonRows() {
  return (
    <>
      {Array.from({ length: 8 }).map((_, i) => (
        <tr key={i} className="border-b border-gray-800/50 animate-pulse">
          <td className="p-3"><div className="h-3 w-4 bg-gray-800 rounded" /></td>
          <td className="p-3"><div className="h-3 w-24 bg-gray-800 rounded" /></td>
          <td className="p-3"><div className="h-3 w-16 bg-gray-800 rounded ml-auto" /></td>
          <td className="p-3"><div className="h-3 w-16 bg-gray-800 rounded ml-auto" /></td>
          <td className="p-3"><div className="h-3 w-16 bg-gray-800 rounded ml-auto" /></td>
          <td className="p-3"><div className="h-3 w-20 bg-gray-800 rounded ml-auto" /></td>
          <td className="p-3"><div className="h-3 w-8 bg-gray-800 rounded ml-auto" /></td>
          <td className="p-3 flex justify-center"><div className="h-4 w-12 bg-gray-800 rounded" /></td>
        </tr>
      ))}
    </>
  );
}

function ScanResultsTable({ data, isFetching }: { data?: ScanResponse; isFetching: boolean }) {
  if (isFetching && !data) return <SkeletonRows />;
  if (!data?.results?.length) return null;

  return (
    <>
      {data.results.map((r) => (
        <tr key={r.ticker} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
          <td className="p-3 text-gray-500 font-mono text-xs">{r.rank}</td>
          <td className="p-3 font-medium text-gray-200">{r.ticker}</td>
          <td className="p-3 text-right"><ScorePill score={r.overall_score} /></td>
          <td className="p-3 text-right font-mono text-xs text-gray-300">{safeFixed(r.technical_score)}</td>
          <td className="p-3 text-right font-mono text-xs text-gray-300">{safeFixed(r.fundamental_score)}</td>
          <td className="p-3 text-right"><ForecastCell forecast={r.forecast} /></td>
          <td className="p-3 text-right font-mono text-xs text-gray-400">{safeFixed(r.effective_signals, 0)}</td>
          <td className="p-3 w-28"><Sparkline data={r.sparkline} className="h-7 w-full" /></td>
          <td className="p-3 text-center">
            <span className={`inline-flex px-2 py-0.5 rounded border text-[10px] font-bold uppercase ${confidenceClass(r.confidence)}`}>
              {r.confidence || '—'}
            </span>
          </td>
        </tr>
      ))}
    </>
  );
}

export default function ScannerPage() {
  const [preset, setPreset] = useState<string>('');
  const [savedData, setSavedData] = useState<ScanResponse | null>(() => loadSavedScan());
  const [shouldScan, setShouldScan] = useState(Boolean(savedData));
  const [immersiveMode, setImmersiveMode] = useState(false);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(savedData?.results?.[0]?.ticker ?? null);
  const queryClient = useQueryClient();

  const { data: presets } = useQuery({
    queryKey: ['scanner-presets'],
    queryFn: () => fetcher<{ presets: Array<{ id: string; name: string; description: string }> }>('/scanner/presets'),
  });

  const scanQuery = useQuery<ScanResponse>({
    queryKey: ['scan-results', preset],
    queryFn: () =>
      fetcher<ScanResponse>(
        `/scanner/scan?market=india${preset ? `&preset=${preset}` : ''}&limit=50`,
        { timeout: SCAN_TIMEOUT },
      ),
    enabled: shouldScan,
    retry: 1,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });

  const { data, isFetching, isError, error, dataUpdatedAt } = scanQuery;
  const effectiveData = data ?? savedData;
  const selectedResult = effectiveData?.results.find((r) => r.ticker === selectedTicker) ?? null;

  useEffect(() => {
    if (!data) return;
    setSavedData(data);
    try {
      localStorage.setItem(
        SCAN_STORAGE_KEY,
        JSON.stringify({
          version: SCAN_STORAGE_VERSION,
          data,
        }),
      );
    } catch {
      // Ignore storage failures.
    }
  }, [data]);

  useEffect(() => {
    if (!effectiveData?.results?.length) {
      setSelectedTicker(null);
      return;
    }
    if (!selectedTicker || !effectiveData.results.some((r) => r.ticker === selectedTicker)) {
      const first = effectiveData.results[0];
      if (first) {
        setSelectedTicker(first.ticker);
      }
    }
  }, [effectiveData, selectedTicker]);

  const handleScan = useCallback(() => {
    if (shouldScan) {
      queryClient.invalidateQueries({ queryKey: ['scan-results', preset] });
    }
    setShouldScan(true);
  }, [shouldScan, preset, queryClient]);

  const handleReset = useCallback(() => {
    setShouldScan(false);
    setSavedData(null);
    setSelectedTicker(null);
    try {
      localStorage.removeItem(SCAN_STORAGE_KEY);
    } catch {
      // Ignore storage cleanup failures.
    }
    queryClient.removeQueries({ queryKey: ['scan-results'] });
  }, [queryClient]);

  const lastUpdated = dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString() : null;

  return (
    <div className={`space-y-6 ${immersiveMode ? 'max-w-none' : 'max-w-7xl'}`}>
      <div>
        <h2 className="text-2xl font-bold text-gray-100">Scanner</h2>
        <p className="text-sm text-gray-500 mt-1">
          Scan the market with pre-built filters, then inspect full signal derivation per stock.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <select
          value={preset}
          onChange={(e) => setPreset(e.target.value)}
          className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-brand-500"
        >
          <option value="">All Stocks</option>
          {presets?.presets.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
        <button
          onClick={handleScan}
          disabled={isFetching}
          className="px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {isFetching && (
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          )}
          {isFetching ? 'Scanning…' : 'Run Scan'}
        </button>
        <button
          onClick={() => setImmersiveMode((v: boolean) => !v)}
          className={`px-3 py-2 rounded-lg border text-xs font-medium transition-colors ${
            immersiveMode
              ? 'border-brand-500/60 bg-brand-600/20 text-brand-200'
              : 'border-gray-700 bg-gray-900 text-gray-300 hover:border-gray-600'
          }`}
        >
          {immersiveMode ? 'Immersive: ON' : 'Immersive: OFF'}
        </button>
        {lastUpdated && !isFetching && (
          <span className="text-xs text-gray-600">Last updated {lastUpdated}</span>
        )}
        {effectiveData?.meta?.source && !isFetching && (
          <span
            className={`text-[11px] px-2 py-1 rounded border ${
              effectiveData.meta.source === 'cache'
                ? 'border-amber-500/30 text-amber-300 bg-amber-500/10'
                : 'border-emerald-500/30 text-emerald-300 bg-emerald-500/10'
            }`}
          >
            {effectiveData.meta.source === 'cache' ? 'Served from cache' : 'Fresh scan'}
          </span>
        )}
      </div>

      {isFetching && (
        <div className="bg-brand-950/30 border border-brand-900/50 rounded-lg px-4 py-3 flex items-center gap-3">
          <svg className="animate-spin h-4 w-4 text-brand-400" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <div>
            <p className="text-sm text-brand-300 font-medium">Scanning market…</p>
            <p className="text-xs text-gray-500 mt-0.5">
              First scan may take several minutes while market data is downloaded.
              Later scans are served from persisted data + cache.
            </p>
          </div>
        </div>
      )}

      {isError && (
        <div className="bg-red-950/30 border border-red-900/50 rounded-lg px-4 py-3">
          <p className="text-sm text-red-400 font-medium">Scan failed</p>
          <p className="text-xs text-red-500/80 mt-1">
            {(error as Error)?.message?.includes('timeout')
              ? 'Request timed out. Backend may still be processing; try again in a minute.'
              : (error as Error)?.message || 'An unexpected error occurred'}
          </p>
          <button
            onClick={handleScan}
            className="mt-2 text-xs text-red-400 hover:text-red-300 underline underline-offset-2"
          >
            Retry scan
          </button>
          {savedData && (
            <p className="text-xs text-gray-500 mt-2">Showing last successful scan while retrying.</p>
          )}
        </div>
      )}

      <ScannerErrorBoundary onReset={handleReset}>
        {(effectiveData || (isFetching && shouldScan)) && !immersiveMode && (
          <div className="bg-gray-900/60 border border-gray-800 rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800">
                    <th className="text-left p-3 text-gray-500 text-xs font-medium uppercase">#</th>
                    <th className="text-left p-3 text-gray-500 text-xs font-medium uppercase">Ticker</th>
                    <th className="text-right p-3 text-gray-500 text-xs font-medium uppercase">Overall</th>
                    <th className="text-right p-3 text-gray-500 text-xs font-medium uppercase">Technical</th>
                    <th className="text-right p-3 text-gray-500 text-xs font-medium uppercase">Fundamental</th>
                    <th className="text-right p-3 text-gray-500 text-xs font-medium uppercase">Forecast</th>
                    <th className="text-right p-3 text-gray-500 text-xs font-medium uppercase">Signals</th>
                    <th className="text-left p-3 text-gray-500 text-xs font-medium uppercase">Trend</th>
                    <th className="text-center p-3 text-gray-500 text-xs font-medium uppercase">Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  <ScanResultsTable data={effectiveData ?? undefined} isFetching={isFetching} />
                </tbody>
              </table>
            </div>
            {effectiveData && (
              <div className="p-3 border-t border-gray-800 text-xs text-gray-500">
                {effectiveData.count} results · {effectiveData.market} market
                {effectiveData.preset && ` · preset: ${effectiveData.preset}`}
              </div>
            )}
          </div>
        )}

        {(effectiveData || (isFetching && shouldScan)) && immersiveMode && (
          <div className="grid grid-cols-1 xl:grid-cols-[1.25fr_0.75fr] gap-4 min-h-[34rem] xl:h-[calc(100vh-14rem)]">
            <div className="bg-gray-900/60 border border-gray-800 rounded-xl overflow-hidden flex flex-col min-h-0">
              <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-gray-200">Immersive Signal Feed</h3>
                <p className="text-[11px] text-gray-500">{effectiveData?.count ?? 0} stocks</p>
              </div>
              <div className="flex-1 min-h-0 overflow-y-auto p-3 space-y-2">
                {effectiveData?.results.map((r) => {
                  const active = r.ticker === selectedTicker;
                  return (
                    <button
                      key={r.ticker}
                      onClick={() => setSelectedTicker(r.ticker)}
                      className={`w-full text-left rounded-lg border px-3 py-3 transition-colors ${
                        active
                          ? 'border-brand-500/70 bg-brand-900/20'
                          : 'border-gray-800 bg-gray-950/30 hover:border-gray-700'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-gray-100">{r.ticker}</p>
                          <p className="text-[11px] text-gray-500">Rank #{r.rank} · Signals {safeFixed(r.effective_signals, 0)}</p>
                        </div>
                        <span className={`px-2 py-1 rounded border text-[10px] font-bold uppercase ${confidenceClass(r.confidence)}`}>
                          {r.confidence}
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-2 mt-3">
                        <SignalBar label="Overall" value={r.overall_score} />
                        <SignalBar label="Technical" value={r.technical_score} />
                        <SignalBar label="Fundamental" value={r.fundamental_score} />
                      </div>
                      <div className="mt-2 rounded bg-gray-900/40 p-1">
                        <Sparkline data={r.sparkline} className="h-7 w-full" />
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4 flex flex-col min-h-0 overflow-hidden">
              <h3 className="text-sm font-semibold text-gray-200">Signal Architecture</h3>
              {!selectedResult ? (
                <p className="text-sm text-gray-500 mt-3">Select a stock for deep diagnostics.</p>
              ) : (
                <div className="mt-3 space-y-4 flex-1 min-h-0 overflow-y-auto pr-1">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-lg font-bold text-gray-100">{selectedResult.ticker}</p>
                      <p className="text-xs text-gray-500">Rank #{selectedResult.rank}</p>
                    </div>
                    <span className={`px-2 py-1 rounded border text-[10px] font-bold uppercase ${confidenceClass(selectedResult.confidence)}`}>
                      {selectedResult.confidence}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <MetricTile label="Overall" value={safeFixed(selectedResult.overall_score)} />
                    <MetricTile label="Effective Signals" value={safeFixed(selectedResult.effective_signals, 0)} />
                  </div>

                  <div className="rounded-lg border border-gray-800 bg-gray-950/30 p-3 space-y-3">
                    <p className="text-xs font-semibold text-gray-300 uppercase tracking-wide">Signal Flow (hover each node)</p>
                    <div className="flex items-center gap-1 overflow-x-auto pb-1">
                      <FlowNode
                        icon="◎"
                        value={selectedResult.pipeline_steps?.ohlcv_source || 'unknown'}
                        subvalue="price source"
                        tooltip="OHLCV data source used in this run."
                        tone={selectedResult.pipeline_steps?.ohlcv_source === 'provider' ? 'warn' : 'good'}
                      />
                      <span className="text-gray-600 text-xs">→</span>
                      <FlowNode
                        icon="∿"
                        value={safeFixed(selectedResult.technical_score)}
                        subvalue="technical"
                        tooltip="Technical pillar score derived from RSI, ADX, MACD, RS and volume context."
                        tone="neutral"
                      />
                      <span className="text-gray-600 text-xs">→</span>
                      <FlowNode
                        icon="ƒ"
                        value={safeFixed(selectedResult.fundamental_score)}
                        subvalue="factor"
                        tooltip="Fundamental/factor pillar score from momentum, quality and value models."
                        tone="neutral"
                      />
                      <span className="text-gray-600 text-xs">→</span>
                      <FlowNode
                        icon="Σ"
                        value={safeFixed(selectedResult.overall_score)}
                        subvalue={selectedResult.confidence}
                        tooltip="Final weighted composite score from all pillars and model assumptions."
                        tone={selectedResult.confidence === 'high' ? 'good' : selectedResult.confidence === 'medium' ? 'warn' : 'neutral'}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <MetricTile label="Tech weighted" value={safeFixed(selectedResult.contribution_breakdown?.weighted_contributions?.technical, 2)} />
                      <MetricTile label="Fund weighted" value={safeFixed(selectedResult.contribution_breakdown?.weighted_contributions?.fundamental, 2)} />
                      <MetricTile label="Sent weighted" value={safeFixed(selectedResult.contribution_breakdown?.weighted_contributions?.sentiment, 2)} />
                      <MetricTile label="ML weighted" value={safeFixed(selectedResult.contribution_breakdown?.weighted_contributions?.ml_prediction, 2)} />
                    </div>
                    <div className="rounded border border-gray-800/80 bg-gray-950/60 px-2 py-2 text-[11px] text-gray-400" title="Why overall can be lower than visible technical/fundamental scores.">
                      {(selectedResult.contribution_breakdown?.explainers || []).slice(0, 2).map((line) => (
                        <p key={line}>• {line}</p>
                      ))}
                    </div>
                  </div>

                  <FutureProjectionFlow result={selectedResult} />

                  <div className="rounded-lg border border-gray-800 bg-gray-950/30 p-3 space-y-3">
                    <p className="text-xs font-semibold text-gray-300 uppercase tracking-wide">Technical Derivation</p>
                    <div className="grid grid-cols-2 gap-2">
                      <MetricTile label="RSI 14" value={safeFixed(selectedResult.diagnostics?.technical?.rsi_14)} />
                      <MetricTile label="ADX 14" value={safeFixed(selectedResult.diagnostics?.technical?.adx_14)} />
                      <MetricTile label="MACD Hist" value={safeFixed(selectedResult.diagnostics?.technical?.macd_histogram)} />
                      <MetricTile label="RS Rating" value={safeFixed(selectedResult.diagnostics?.technical?.rs_rating)} />
                      <MetricTile label="Volume Ratio" value={safeFixed(selectedResult.diagnostics?.technical?.volume_ratio)} />
                      <MetricTile label="OBV Trend" value={selectedResult.diagnostics?.technical?.obv_trend || 'N/A'} />
                    </div>
                  </div>

                  <div className="rounded-lg border border-gray-800 bg-gray-950/30 p-3 space-y-3">
                    <p className="text-xs font-semibold text-gray-300 uppercase tracking-wide">Factor Derivation</p>
                    <div className="grid grid-cols-3 gap-2">
                      <SignalBar label="Momentum" value={selectedResult.diagnostics?.factor?.momentum_score} />
                      <SignalBar label="Quality" value={selectedResult.diagnostics?.factor?.quality_score} />
                      <SignalBar label="Value" value={selectedResult.diagnostics?.factor?.value_score} />
                    </div>
                    <p className="text-xs text-gray-500">
                      Factor composite: {safeFixed(selectedResult.diagnostics?.factor?.composite)}
                    </p>
                  </div>

                  <div className="rounded-lg border border-gray-800 bg-gray-950/30 p-3 space-y-2">
                    <p className="text-xs font-semibold text-gray-300 uppercase tracking-wide">Pipeline Pulse</p>
                    <div className="flex items-center gap-2 overflow-x-auto pb-1">
                      <FlowNode
                        icon={selectedResult.pipeline_steps?.universe_selected ? '●' : '○'}
                        value="Universe"
                        tooltip="Universe selection stage."
                        tone={selectedResult.pipeline_steps?.universe_selected ? 'good' : 'neutral'}
                      />
                      <span className="text-gray-600 text-xs">→</span>
                      <FlowNode
                        icon={selectedResult.pipeline_steps?.technical_computed ? '●' : '○'}
                        value="Tech"
                        tooltip="Technical indicators computed."
                        tone={selectedResult.pipeline_steps?.technical_computed ? 'good' : 'neutral'}
                      />
                      <span className="text-gray-600 text-xs">→</span>
                      <FlowNode
                        icon={selectedResult.pipeline_steps?.factor_computed ? '●' : '○'}
                        value="Factor"
                        tooltip="Factor model computed (momentum/quality/value)."
                        tone={selectedResult.pipeline_steps?.factor_computed ? 'good' : 'neutral'}
                      />
                      <span className="text-gray-600 text-xs">→</span>
                      <FlowNode
                        icon={selectedResult.pipeline_steps?.composite_computed ? '●' : '○'}
                        value="Composite"
                        tooltip="Final weighted composite generated."
                        tone={selectedResult.pipeline_steps?.composite_computed ? 'good' : 'neutral'}
                      />
                    </div>
                  </div>

                  {selectedResult.diagnostics?.preset?.selected && (
                    <div className="rounded-lg border border-gray-800 bg-gray-950/30 p-3">
                      <p className="text-xs font-semibold text-gray-300 uppercase tracking-wide">Preset Evaluation</p>
                      <p className={`mt-2 text-xs ${selectedResult.diagnostics.preset.passed ? 'text-emerald-400' : 'text-amber-400'}`}>
                        {selectedResult.diagnostics.preset.selected}: {selectedResult.diagnostics.preset.passed ? 'Passed' : 'Not matched'}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </ScannerErrorBoundary>

      {!shouldScan && (
        <div className="text-center py-16 text-gray-600">
          <svg className="mx-auto h-12 w-12 mb-4 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <p className="text-sm">Click <span className="text-brand-400 font-medium">Run Scan</span> to analyze the market</p>
        </div>
      )}
    </div>
  );
}
