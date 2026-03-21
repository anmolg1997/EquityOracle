import { useParams } from 'react-router-dom';

export default function DeepDivePage() {
  const { ticker } = useParams();

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h2 className="text-2xl font-bold text-gray-100">
          {ticker ? `Deep Dive: ${ticker}` : 'Stock Deep Dive'}
        </h2>
        <p className="text-sm text-gray-500 mt-1">Comprehensive analysis with charts, factors, and AI thesis</p>
      </div>

      {!ticker ? (
        <div className="text-center py-20 text-gray-500">
          <p className="text-lg mb-2">Select a stock to analyze</p>
          <p className="text-sm">Click on any ticker from Scanner or Recommendations</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-gray-900/60 border border-gray-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">Price Chart</h3>
            <div className="h-80 flex items-center justify-center text-gray-600 border border-gray-800 rounded-lg">
              TradingView Chart — {ticker}
            </div>
          </div>

          <div className="space-y-4">
            <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">Factor Scores</h3>
              {['Technical', 'Momentum', 'Quality', 'Value'].map((factor) => (
                <div key={factor} className="flex items-center justify-between py-2 border-b border-gray-800/50 last:border-0">
                  <span className="text-sm text-gray-400">{factor}</span>
                  <span className="font-mono text-sm text-gray-200">—</span>
                </div>
              ))}
            </div>

            <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">AI Thesis</h3>
              <p className="text-sm text-gray-500">Thesis generation available after LLM integration (Phase 7)</p>
            </div>

            <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">Decision Audit</h3>
              <p className="text-sm text-gray-500">Full decision context for this recommendation</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
