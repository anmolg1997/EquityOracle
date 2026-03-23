import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { AppRouter } from './router';
import { Sidebar } from '@/shared/components/Sidebar';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      gcTime: 300_000,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="flex h-screen overflow-hidden bg-gray-950">
          <Sidebar />
          <main className="flex-1 min-w-0 min-h-0 overflow-hidden">
            <div className="h-full overflow-y-auto p-6">
              <AppRouter />
            </div>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
