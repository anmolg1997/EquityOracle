import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

const CommandCenterPage = lazy(() => import('@/features/command-center/CommandCenterPage'));
const ScannerPage = lazy(() => import('@/features/scanner/ScannerPage'));
const RecommendationsPage = lazy(() => import('@/features/recommendations/RecommendationsPage'));
const DeepDivePage = lazy(() => import('@/features/deep-dive/DeepDivePage'));
const PortfolioPage = lazy(() => import('@/features/portfolio/PortfolioPage'));
const PerformancePage = lazy(() => import('@/features/performance/PerformancePage'));
const SettingsPage = lazy(() => import('@/features/settings/SettingsPage'));

function LoadingFallback() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="animate-pulse flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-brand-400 border-t-transparent rounded-full animate-spin" />
        <span className="text-gray-400 text-sm">Loading…</span>
      </div>
    </div>
  );
}

export function AppRouter() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <Routes>
        <Route path="/" element={<CommandCenterPage />} />
        <Route path="/scanner" element={<ScannerPage />} />
        <Route path="/recommendations" element={<RecommendationsPage />} />
        <Route path="/deep-dive/:ticker?" element={<DeepDivePage />} />
        <Route path="/portfolio" element={<PortfolioPage />} />
        <Route path="/performance" element={<PerformancePage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
