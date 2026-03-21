import { create } from 'zustand';
import type { Position } from '../types';

interface PortfolioState {
  positions: Position[];
  cash: number;
  totalValue: number;
  setPositions: (positions: Position[]) => void;
  setCash: (cash: number) => void;
}

export const usePortfolioStore = create<PortfolioState>((set) => ({
  positions: [],
  cash: 1_000_000,
  totalValue: 1_000_000,
  setPositions: (positions) =>
    set((state) => ({
      positions,
      totalValue: state.cash + positions.reduce((sum, p) => sum + p.current_price * p.quantity, 0),
    })),
  setCash: (cash) => set({ cash }),
}));
