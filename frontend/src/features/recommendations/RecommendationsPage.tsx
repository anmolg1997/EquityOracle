import { useQuery } from '@tanstack/react-query';
import { fetcher } from '@/shared/api/client';
import type { Recommendation } from '@/shared/types';

export default function RecommendationsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['recommendations'],
    queryFn: () => fetcher<{ count: number; recommendations: Recommendation[] }>('/recommendations?market=india&limit=20'),
  });

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h2 className="text-2xl font-bold text-gray-100">Recommendations</h2>
        <p className="text-sm text-gray-500 mt-1">AI-ranked stock picks with confidence scores and exit rules</p>
      </div>

      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-gray-900/60 border border-gray-800 rounded-xl p-5 animate-pulse">
              <div className="h-4 bg-gray-800 rounded w-1/3 mb-3" />
              <div className="h-3 bg-gray-800 rounded w-2/3 mb-2" />
              <div className="h-3 bg-gray-800 rounded w-1/2" />
            </div>
          ))}
        </div>
      )}

      {data && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.recommendations.map((rec) => (
            <div
              key={`${rec.ticker}-${rec.horizon}`}
              className="bg-gray-900/60 border border-gray-800 rounded-xl p-5 hover:border-brand-600/40 transition-colors"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-bold text-gray-100">{rec.ticker}</h3>
                  <span className="text-[10px] uppercase tracking-wider text-gray-500">{rec.horizon} horizon</span>
                </div>
                <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${
                  rec.direction === 'buy' ? 'bg-emerald-500/20 text-emerald-400' :
                  rec.direction === 'sell' ? 'bg-red-500/20 text-red-400' :
                  'bg-gray-700 text-gray-400'
                }`}>
                  {rec.direction}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-3 mb-3">
                <div>
                  <p className="text-[10px] text-gray-500">Strength</p>
                  <p className="font-mono text-sm text-gray-200">{rec.strength.toFixed(1)}</p>
                </div>
                <div>
                  <p className="text-[10px] text-gray-500">Expected</p>
                  <p className={`font-mono text-sm ${rec.expected_return_pct > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {rec.expected_return_pct > 0 ? '+' : ''}{rec.expected_return_pct.toFixed(2)}%
                  </p>
                </div>
                <div>
                  <p className="text-[10px] text-gray-500">Confidence</p>
                  <p className="font-mono text-sm text-brand-300">{(rec.confidence * 100).toFixed(0)}%</p>
                </div>
              </div>

              {rec.exit_rules.length > 0 && (
                <div className="text-[10px] text-gray-500 space-y-0.5">
                  {rec.exit_rules.map((rule, i) => (
                    <p key={i}>↳ {rule.description}</p>
                  ))}
                </div>
              )}

              {rec.independent_signals < 2 && (
                <p className="text-[10px] text-amber-400 mt-2">⚠ Low signal independence ({rec.independent_signals.toFixed(1)})</p>
              )}
            </div>
          ))}
        </div>
      )}

      {data?.count === 0 && (
        <div className="text-center py-12 text-gray-500">
          <p>No recommendations available. Run a scan first.</p>
        </div>
      )}
    </div>
  );
}
