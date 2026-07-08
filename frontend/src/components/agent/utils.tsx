import { useId } from 'react';

import type { AgentMemoryEntry } from './types';

export function formatPercent(value: number, digits = 2): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatCurrency(value: number): string {
  return `¥${value.toFixed(2)}`;
}

export function actionColor(action: string): { bg: string; text: string; border: string; label: string } {
  switch (action) {
    case 'increase_bid':
      return { bg: 'bg-success/10', text: 'text-success', border: 'border-success/40', label: '提高出价' };
    case 'decrease_bid':
    case 'optimize_creative':
      return {
        bg: 'bg-warning/10',
        text: 'text-warning',
        border: 'border-warning/40',
        label: action === 'decrease_bid' ? '降低出价' : '优化创意',
      };
    case 'switch_creative':
      return { bg: 'bg-accent/10', text: 'text-accent', border: 'border-accent/40', label: '更换创意' };
    case 'maintain_strategy':
    default:
      return { bg: 'bg-slate-600/20', text: 'text-slate-300', border: 'border-slate-500/40', label: '保持策略' };
  }
}

export function actionLabel(action: string): string {
  return actionColor(action).label;
}

export function computeSuccessRate(memory: AgentMemoryEntry[]): number {
  if (!memory.length) return 0;
  const recent = memory.slice(-10);
  const passed = recent.filter((entry) => {
    const eva = entry.expected_vs_actual || {};
    const impOk = (eva.expected_impressions_change_pct || 0) * (eva.actual_impressions_change_pct || 0) >= 0;
    const ctrOk = (eva.expected_ctr_change_pct || 0) * (eva.actual_ctr_change_pct || 0) >= 0;
    return impOk && ctrOk;
  }).length;
  return Math.round((passed / recent.length) * 100);
}

export function calculateConfidence(successRate: number, memorySize: number): number {
  return Math.min(95, Math.round(35 + successRate * 0.45 + Math.min(memorySize, 12) * 2.5));
}

export function FlowArrow({ durationMs }: { durationMs: number }) {
  const uid = useId().replace(/:/g, '-');
  const markerId = `arrowhead-${uid}`;
  return (
    <div className="flex flex-col items-center py-1">
      <svg width="24" height="36" viewBox="0 0 24 36" className="overflow-visible">
        <defs>
          <marker id={markerId} markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#64748B" />
          </marker>
        </defs>
        <line
          x1="12"
          y1="0"
          x2="12"
          y2="30"
          stroke="#64748B"
          strokeWidth="2"
          strokeDasharray="6 4"
          className="animate-flow-arrow"
          markerEnd={`url(#${markerId})`}
        />
      </svg>
      <span className="text-[10px] text-muted -mt-1">{durationMs}ms</span>
    </div>
  );
}

export function MetricBadge({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-slate-900/60 rounded-lg px-3 py-2">
      <p className="text-[10px] text-muted">{label}</p>
      <p className="text-sm font-mono text-slate-100">{value}</p>
    </div>
  );
}

export function GaugeChart({ value, label }: { value: number; label: string }) {
  const radius = 70;
  const stroke = 12;
  const normalized = Math.max(0, Math.min(100, value));
  const circumference = Math.PI * radius;
  const offset = circumference * (1 - normalized / 100);

  let color = '#EF4444';
  if (normalized >= 70) color = '#10B981';
  else if (normalized >= 40) color = '#F59E0B';

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-[180px] h-[100px]">
        <svg width="180" height="100" viewBox="0 0 180 100" className="overflow-visible">
          <path
            d="M 15 90 A 75 75 0 0 1 165 90"
            fill="none"
            stroke="#334155"
            strokeWidth={stroke}
            strokeLinecap="round"
          />
          <path
            d="M 15 90 A 75 75 0 0 1 165 90"
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-all duration-700"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-end pb-2">
          <span className="text-2xl font-bold text-slate-100">{normalized}%</span>
          <span className="text-xs text-muted">{label}</span>
        </div>
      </div>
    </div>
  );
}
