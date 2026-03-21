interface StatCardProps {
  label: string;
  value: string | number;
  change?: number;
  suffix?: string;
}

function StatCard({ label, value, change, suffix = '' }: StatCardProps) {
  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
      <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      <p className="text-2xl font-bold text-gray-100 font-mono">
        {value}
        {suffix && <span className="text-sm text-gray-500 ml-1">{suffix}</span>}
      </p>
      {change !== undefined && (
        <p className={change >= 0 ? 'text-emerald-400 text-xs mt-1' : 'text-red-400 text-xs mt-1'}>
          {change >= 0 ? '+' : ''}{change.toFixed(2)}%
        </p>
      )}
    </div>
  );
}

export function QuickStats() {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <StatCard label="Portfolio Value" value="₹10,00,000" />
      <StatCard label="Today's P&L" value="₹0" change={0} />
      <StatCard label="Open Positions" value="0" />
      <StatCard label="Win Rate" value="—" suffix="%" />
    </div>
  );
}
