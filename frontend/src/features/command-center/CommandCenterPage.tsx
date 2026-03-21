import { CircuitBreakerIndicator } from './components/CircuitBreakerIndicator';
import { QuickStats } from './components/QuickStats';

export default function CommandCenterPage() {
  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-100">Command Center</h2>
          <p className="text-sm text-gray-500 mt-1">Market overview and system status</p>
        </div>
        <CircuitBreakerIndicator />
      </div>

      <QuickStats />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">Top Recommendations</h3>
          <p className="text-gray-500 text-sm">Run a scan to see recommendations</p>
        </div>

        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">Alert Stream</h3>
          <p className="text-gray-500 text-sm">No alerts</p>
        </div>
      </div>

      <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">Market Regime</h3>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gray-800 text-gray-300">
            Awaiting Data
          </span>
          <span className="text-gray-500 text-xs">Market regime detection requires historical data</span>
        </div>
      </div>
    </div>
  );
}
