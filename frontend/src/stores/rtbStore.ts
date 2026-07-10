import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface BidEntry {
  dsp: string;
  bid: number;
  response_time_ms: number;
}

interface WinnerInfo {
  dsp: string;
  winning_bid: number;
  settlement_price: number;
}

interface AuctionResult {
  impression_id: string;
  floor_price: number;
  auction_type: string;
  total_bids: number;
  bids: BidEntry[];
  winner: WinnerInfo | null;
  latency_ms: number;
}

interface BatchStats {
  total_auctions: number;
  filled_auctions: number;
  fill_rate: number;
  avg_winning_bid: number;
  avg_winning_cpm: number;
  total_latency_ms: number;
  avg_latency_ms: number;
  win_rate_by_dsp: Record<string, { wins: number; bids: number; win_rate: number }>;
}

interface BatchResponse {
  count: number;
  results: AuctionResult[];
  stats: BatchStats;
}

interface LogEntry {
  id: string;
  time: string;
  auctionNumber: number;
  bids: number;
  winner: string;
  price: string;
  latency: number;
}

interface RTBState {
  auctionResult: AuctionResult | null;
  batchResult: BatchResponse | null;
  logs: LogEntry[];
  auctionCounter: number;
  setAuctionResult: (r: AuctionResult | null) => void;
  setBatchResult: (r: BatchResponse | null) => void;
  addLog: (entry: LogEntry) => void;
  clearAll: () => void;
}

export const useRTBStore = create<RTBState>()(
  persist(
    (set) => ({
      auctionResult: null,
      batchResult: null,
      logs: [],
      auctionCounter: 0,
      setAuctionResult: (r) => set({ auctionResult: r }),
      setBatchResult: (r) => set({ batchResult: r }),
      addLog: (entry) =>
        set((state) => ({
          logs: [...state.logs.slice(-49), entry],
          auctionCounter: state.auctionCounter + 1,
        })),
      clearAll: () => set({ auctionResult: null, batchResult: null, logs: [], auctionCounter: 0 }),
    }),
    { name: 'adpulse-rtb' }
  )
);
