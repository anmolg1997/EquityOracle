export interface ScanResult {
  rank: number;
  ticker: string;
  overall_score: number;
  technical_score: number;
  fundamental_score: number;
  effective_signals: number;
  confidence: string;
  passed_presets: string[];
}

export interface Recommendation {
  ticker: string;
  direction: 'buy' | 'sell' | 'hold';
  horizon: string;
  strength: number;
  expected_return_pct: number;
  confidence: number;
  independent_signals: number;
  exit_rules: ExitRule[];
}

export interface ExitRule {
  type: string;
  description: string;
}

export interface Position {
  ticker: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  gross_pnl: number;
  net_pnl: number;
  entry_date: string;
  is_open: boolean;
}

export interface PerformanceMetrics {
  gross_return_pct: number;
  net_return_pct: number;
  total_trades: number;
  win_rate: number;
  total_costs: number;
  total_tax: number;
  sharpe_ratio: number;
  max_drawdown_pct: number;
}

export interface ProviderHealth {
  name: string;
  healthy: boolean;
  last_success: string | null;
  consecutive_failures: number;
  error: string;
}

export interface SystemHealth {
  status: string;
  components: Record<string, string>;
}

export type CircuitBreakerState = 'green' | 'amber' | 'red' | 'black';
