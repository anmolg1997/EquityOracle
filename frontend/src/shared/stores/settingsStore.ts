import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SettingsState {
  market: string;
  theme: 'dark' | 'light';
  autonomyLevel: 'manual' | 'semi_auto' | 'full_auto';
  setMarket: (market: string) => void;
  setTheme: (theme: 'dark' | 'light') => void;
  setAutonomyLevel: (level: 'manual' | 'semi_auto' | 'full_auto') => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      market: 'india',
      theme: 'dark',
      autonomyLevel: 'manual',
      setMarket: (market) => set({ market }),
      setTheme: (theme) => set({ theme }),
      setAutonomyLevel: (level) => set({ autonomyLevel: level }),
    }),
    { name: 'equityoracle-settings' }
  )
);
