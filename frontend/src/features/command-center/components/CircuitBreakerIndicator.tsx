import { useQuery } from '@tanstack/react-query';
import { clsx } from 'clsx';
import { fetcher } from '@/shared/api/client';
import type { CircuitBreakerState } from '@/shared/types';

const stateConfig: Record<CircuitBreakerState, { bg: string; text: string; label: string; pulse: boolean }> = {
  green: { bg: 'bg-circuit-green/20', text: 'text-circuit-green', label: 'NORMAL', pulse: false },
  amber: { bg: 'bg-circuit-amber/20', text: 'text-circuit-amber', label: 'CAUTION', pulse: true },
  red: { bg: 'bg-circuit-red/20', text: 'text-circuit-red', label: 'ALERT', pulse: true },
  black: { bg: 'bg-gray-800', text: 'text-gray-300', label: 'HALTED', pulse: true },
};

export function CircuitBreakerIndicator() {
  const { data } = useQuery({
    queryKey: ['circuit-breaker'],
    queryFn: () => fetcher<{ state: CircuitBreakerState }>('/system/circuit-breaker'),
    refetchInterval: 10_000,
  });

  const state = data?.state ?? 'green';
  const config = stateConfig[state];

  return (
    <div className={clsx('rounded-xl p-4 border', config.bg, 'border-gray-800')}>
      <div className="flex items-center gap-3">
        <div className={clsx('w-3 h-3 rounded-full', config.text.replace('text-', 'bg-'), config.pulse && 'animate-pulse')} />
        <div>
          <p className={clsx('text-xs font-bold uppercase tracking-wider', config.text)}>{config.label}</p>
          <p className="text-[10px] text-gray-500 mt-0.5">Circuit Breaker</p>
        </div>
      </div>
    </div>
  );
}
