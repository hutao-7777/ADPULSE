import { create } from 'zustand';
import { persist } from 'zustand/middleware';

import apiClient from '../lib/apiClient';

export interface DataSource {
  name: string;
  label: string;
  record_count: number;
}

interface DataSourceState {
  activeSource: string;
  availableSources: DataSource[];
  isLoading: boolean;
  setActiveSource: (source: string) => void;
  fetchAvailableSources: () => Promise<void>;
  hasRealData: () => boolean;
}

export const useDataSourceStore = create<DataSourceState>()(
  persist(
    (set, get) => ({
      activeSource: 'all',
      availableSources: [{ name: 'mock', label: 'Mock 数据', record_count: 0 }],
      isLoading: false,

      setActiveSource: (source) => set({ activeSource: source }),

      fetchAvailableSources: async () => {
        set({ isLoading: true });
        try {
          const res = await apiClient.get('/dashboard/available-sources');
          const sources = res.data?.sources ?? [];
          set({ availableSources: sources, isLoading: false });
        } catch {
          set({ isLoading: false });
        }
      },

      hasRealData: () => {
        const sources = get().availableSources;
        return sources.some((s) => s.name !== 'mock' && s.record_count > 0);
      },
    }),
    {
      name: 'adpulse-datasource',
      partialize: (state) => ({ activeSource: state.activeSource }),
    }
  )
);
