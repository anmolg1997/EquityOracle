import { useQuery } from '@tanstack/react-query';
import { fetcher } from '@/shared/api/client';
import type { ProviderHealth } from '@/shared/types';

export default function PerformancePage() {
  const { data: providers } = useQuery({
    queryKey: ['provider-health'],
    queryFn: () => fetcher<{ overall_healthy: boolean; providers: ProviderHealth[] }>('/system/providers'),
    refetchInterval: 30_000,
  });

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h2 className="text-2xl font-bold text-gray-100">Performance & Learning</h2>
        <p className="text-sm text-gray-500 mt-1">Accuracy tracking, calibration, attribution, and system health</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">Accuracy Tracker</h3>
          <div className="text-center py-8 text-gray-500 text-sm">
            Accuracy data will populate as recommendations are tracked
          </div>
        </div>

        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">Calibration</h3>
          <div className="text-center py-8 text-gray-500 text-sm">
            Calibration chart shows predicted vs actual outcomes
          </div>
        </div>
      </div>

      <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">Data Provider Health</h3>
        {providers?.providers && providers.providers.length > 0 ? (
          <div className="space-y-2">
            {providers.providers.map((p) => (
              <div key={p.name} className="flex items-center justify-between p-3 bg-gray-800/30 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${p.healthy ? 'bg-emerald-400' : 'bg-red-400 animate-pulse'}`} />
                  <span className="text-sm text-gray-200">{p.name}</span>
                </div>
                <div className="text-right">
                  {p.healthy ? (
                    <span className="text-xs text-gray-500">Healthy</span>
                  ) : (
                    <span className="text-xs text-red-400">{p.error || 'Unhealthy'}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-sm">No provider data available</p>
        )}
      </div>
    </div>
  );
}
