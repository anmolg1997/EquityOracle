import { useSettingsStore } from '@/shared/stores/settingsStore';

export default function SettingsPage() {
  const { market, setMarket, autonomyLevel, setAutonomyLevel } = useSettingsStore();

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h2 className="text-2xl font-bold text-gray-100">Settings</h2>
        <p className="text-sm text-gray-500 mt-1">Configure market, autonomy, risk, and system preferences</p>
      </div>

      <div className="space-y-6">
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">Market Configuration</h3>
          <label className="block mb-2 text-sm text-gray-400">Default Market</label>
          <select
            value={market}
            onChange={(e) => setMarket(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 w-full max-w-xs"
          >
            <option value="india">India (NSE/BSE)</option>
            <option value="us">US (NYSE/NASDAQ)</option>
            <option value="global">Global</option>
          </select>
        </div>

        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">Autonomy Level</h3>
          <div className="space-y-3">
            {[
              { value: 'manual' as const, label: 'Manual', desc: 'All actions require confirmation' },
              { value: 'semi_auto' as const, label: 'Semi-Auto', desc: 'Recommendations auto-generated, trades need approval' },
              { value: 'full_auto' as const, label: 'Full Auto', desc: 'System operates autonomously within risk limits' },
            ].map((opt) => (
              <label key={opt.value} className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-800/30 cursor-pointer">
                <input
                  type="radio"
                  name="autonomy"
                  value={opt.value}
                  checked={autonomyLevel === opt.value}
                  onChange={() => setAutonomyLevel(opt.value)}
                  className="mt-1 accent-brand-500"
                />
                <div>
                  <p className="text-sm font-medium text-gray-200">{opt.label}</p>
                  <p className="text-xs text-gray-500">{opt.desc}</p>
                </div>
              </label>
            ))}
          </div>
        </div>

        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">Risk Parameters</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <label className="text-gray-500 text-xs">Max Position %</label>
              <p className="font-mono text-gray-200">10%</p>
            </div>
            <div>
              <label className="text-gray-500 text-xs">Max Sector %</label>
              <p className="font-mono text-gray-200">30%</p>
            </div>
            <div>
              <label className="text-gray-500 text-xs">Max Drawdown (Black)</label>
              <p className="font-mono text-gray-200">15%</p>
            </div>
            <div>
              <label className="text-gray-500 text-xs">LLM Daily Budget</label>
              <p className="font-mono text-gray-200">₹50</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
