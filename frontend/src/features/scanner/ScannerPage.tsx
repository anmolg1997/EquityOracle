import { useState, useCallback, Component, type ReactNode } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { fetcher } from '@/shared/api/client';

interface ScanResult {
  rank: number;
  ticker: string;
  overall_score: number;
  technical_score: number;
  fundamental_score: number;
  effective_signals: number;
  confidence: string;
  passed_presets: string[];
}

interface ScanResponse {
  count: number;
  market: string;
  preset: string | null;
  results: ScanResult[];
}

const SCAN_TIMEOUT = 10 * 60 * 1000;

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
          <td className="p-3 text-right font-mono text-xs text-gray-400">{safeFixed(r.effective_signals, 0)}</td>
          <td className="p-3 text-center">
            <span className={`inline-flex px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
              r.confidence === 'high' ? 'bg-emerald-500/20 text-emerald-400' :
              r.confidence === 'medium' ? 'bg-amber-500/20 text-amber-400' :
              'bg-gray-700/60 text-gray-400'
            }`}>
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
  const [shouldScan, setShouldScan] = useState(false);
  const queryClient = useQueryClient();

  const { data: presets } = useQuery({
    queryKey: ['scanner-presets'],
    queryFn: () => fetcher<{ presets: Array<{ id: string; name: string; description: string }> }>('/scanner/presets'),
  });

  const scanQuery = useQuery({
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

  const handleScan = useCallback(() => {
    if (shouldScan) {
      queryClient.invalidateQueries({ queryKey: ['scan-results', preset] });
    }
    setShouldScan(true);
  }, [shouldScan, preset, queryClient]);

  const handleReset = useCallback(() => {
    setShouldScan(false);
    queryClient.removeQueries({ queryKey: ['scan-results'] });
  }, [queryClient]);

  const lastUpdated = dataUpdatedAt
    ? new Date(dataUpdatedAt).toLocaleTimeString()
    : null;

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h2 className="text-2xl font-bold text-gray-100">Scanner</h2>
        <p className="text-sm text-gray-500 mt-1">
          Scan the market with pre-built or custom filters
        </p>
      </div>

      <div className="flex items-center gap-3">
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
        {lastUpdated && !isFetching && (
          <span className="text-xs text-gray-600">Last updated {lastUpdated}</span>
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
              Subsequent scans are much faster.
            </p>
          </div>
        </div>
      )}

      {isError && (
        <div className="bg-red-950/30 border border-red-900/50 rounded-lg px-4 py-3">
          <p className="text-sm text-red-400 font-medium">Scan failed</p>
          <p className="text-xs text-red-500/80 mt-1">
            {(error as Error)?.message?.includes('timeout')
              ? 'Request timed out. The backend may still be processing — try again in a minute.'
              : (error as Error)?.message || 'An unexpected error occurred'}
          </p>
          <button
            onClick={handleScan}
            className="mt-2 text-xs text-red-400 hover:text-red-300 underline underline-offset-2"
          >
            Retry scan
          </button>
        </div>
      )}

      <ScannerErrorBoundary onReset={handleReset}>
        {(data || (isFetching && shouldScan)) && (
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
                    <th className="text-right p-3 text-gray-500 text-xs font-medium uppercase">Signals</th>
                    <th className="text-center p-3 text-gray-500 text-xs font-medium uppercase">Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  <ScanResultsTable data={data} isFetching={isFetching} />
                </tbody>
              </table>
            </div>
            {data && (
              <div className="p-3 border-t border-gray-800 text-xs text-gray-500">
                {data.count} results · {data.market} market
                {data.preset && ` · preset: ${data.preset}`}
              </div>
            )}
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
