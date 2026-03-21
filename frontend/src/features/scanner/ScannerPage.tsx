import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetcher } from '@/shared/api/client';

interface ScanResponse {
  count: number;
  market: string;
  results: Array<{
    rank: number;
    ticker: string;
    overall_score: number;
    technical_score: number;
    fundamental_score: number;
    effective_signals: number;
    confidence: string;
    passed_presets: string[];
  }>;
}

export default function ScannerPage() {
  const [preset, setPreset] = useState<string>('');
  const [shouldScan, setShouldScan] = useState(false);

  const { data: presets } = useQuery({
    queryKey: ['scanner-presets'],
    queryFn: () => fetcher<{ presets: Array<{ id: string; name: string; description: string }> }>('/scanner/presets'),
  });

  const { data, isLoading } = useQuery({
    queryKey: ['scan-results', preset],
    queryFn: () => fetcher<ScanResponse>(`/scanner/scan?market=india${preset ? `&preset=${preset}` : ''}&limit=50`),
    enabled: shouldScan,
  });

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h2 className="text-2xl font-bold text-gray-100">Scanner</h2>
        <p className="text-sm text-gray-500 mt-1">Scan the market with pre-built or custom filters</p>
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
          onClick={() => setShouldScan(true)}
          className="px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-500 transition-colors"
        >
          {isLoading ? 'Scanning…' : 'Run Scan'}
        </button>
      </div>

      {data && (
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left p-3 text-gray-500 text-xs font-medium uppercase">#</th>
                  <th className="text-left p-3 text-gray-500 text-xs font-medium uppercase">Ticker</th>
                  <th className="text-right p-3 text-gray-500 text-xs font-medium uppercase">Score</th>
                  <th className="text-right p-3 text-gray-500 text-xs font-medium uppercase">Technical</th>
                  <th className="text-right p-3 text-gray-500 text-xs font-medium uppercase">Fundamental</th>
                  <th className="text-right p-3 text-gray-500 text-xs font-medium uppercase">Signals</th>
                  <th className="text-center p-3 text-gray-500 text-xs font-medium uppercase">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((r) => (
                  <tr key={r.ticker} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                    <td className="p-3 text-gray-500 font-mono text-xs">{r.rank}</td>
                    <td className="p-3 font-medium text-gray-200">{r.ticker}</td>
                    <td className="p-3 text-right font-mono text-brand-300">{r.overall_score.toFixed(1)}</td>
                    <td className="p-3 text-right font-mono text-gray-300">{r.technical_score.toFixed(1)}</td>
                    <td className="p-3 text-right font-mono text-gray-300">{r.fundamental_score.toFixed(1)}</td>
                    <td className="p-3 text-right font-mono text-gray-400">{r.effective_signals.toFixed(1)}</td>
                    <td className="p-3 text-center">
                      <span className={`inline-flex px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        r.confidence === 'high' ? 'bg-emerald-500/20 text-emerald-400' :
                        r.confidence === 'medium' ? 'bg-amber-500/20 text-amber-400' :
                        'bg-gray-700 text-gray-400'
                      }`}>
                        {r.confidence}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="p-3 border-t border-gray-800 text-xs text-gray-500">
            {data.count} results · {data.market} market
          </div>
        </div>
      )}
    </div>
  );
}
