import { useQuery } from '@tanstack/react-query';
import { fetcher } from '@/shared/api/client';

export default function PortfolioPage() {
  const { data } = useQuery({
    queryKey: ['portfolio'],
    queryFn: () => fetcher<{ portfolio_id: string; positions: unknown[]; cash: number; total_value: number }>('/portfolio'),
  });

  const { data: perf } = useQuery({
    queryKey: ['portfolio-performance'],
    queryFn: () => fetcher<Record<string, number>>('/portfolio/performance'),
  });

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h2 className="text-2xl font-bold text-gray-100">Paper Portfolio</h2>
        <p className="text-sm text-gray-500 mt-1">Simulated portfolio with realistic costs, slippage, and tax</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
          <p className="text-[10px] text-gray-500 uppercase tracking-wider">Cash</p>
          <p className="text-xl font-bold font-mono text-gray-100">₹{(data?.cash ?? 1_000_000).toLocaleString('en-IN')}</p>
        </div>
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
          <p className="text-[10px] text-gray-500 uppercase tracking-wider">Total Value</p>
          <p className="text-xl font-bold font-mono text-gray-100">₹{(data?.total_value ?? 1_000_000).toLocaleString('en-IN')}</p>
        </div>
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
          <p className="text-[10px] text-gray-500 uppercase tracking-wider">Gross P&L</p>
          <p className="text-xl font-bold font-mono text-gray-300">₹{(perf?.gross_return_pct ?? 0).toLocaleString('en-IN')}</p>
        </div>
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
          <p className="text-[10px] text-gray-500 uppercase tracking-wider">Net P&L</p>
          <p className="text-xl font-bold font-mono text-gray-300">₹{(perf?.net_return_pct ?? 0).toLocaleString('en-IN')}</p>
          <p className="text-[10px] text-gray-600 mt-0.5">After costs + tax</p>
        </div>
      </div>

      <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">Positions</h3>
        <div className="text-center py-8 text-gray-500 text-sm">
          No open positions. Recommendations will appear here when traded.
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">Gross vs Net Performance</h3>
          <div className="h-48 flex items-center justify-center text-gray-600 border border-gray-800 rounded-lg">
            Performance overlay chart
          </div>
        </div>

        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">Risk Decomposition</h3>
          <div className="space-y-2">
            {[
              { label: 'Total Costs', key: 'total_costs' },
              { label: 'Slippage', key: 'total_slippage' },
              { label: 'Tax Estimate', key: 'total_tax' },
            ].map(({ label, key }) => (
              <div key={key} className="flex justify-between text-sm">
                <span className="text-gray-400">{label}</span>
                <span className="font-mono text-gray-300">₹{((perf as Record<string, number> | undefined)?.[key] ?? 0).toLocaleString('en-IN')}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
