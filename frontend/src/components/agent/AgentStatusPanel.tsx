import { useMemo, type ReactNode } from 'react';
import { Activity, BarChart3, Target, TrendingUp } from 'lucide-react';

import { cn } from '../../utils/cn';
import {
  actionLabel,
  calculateConfidence,
  computeSuccessRate,
  formatCurrency,
  GaugeChart,
} from './utils';
import type { AgentMemoryEntry, AgentStatus, PerformanceMetrics } from './types';

interface AgentStatusPanelProps {
  status: AgentStatus | null;
  memory: AgentMemoryEntry[];
  metricsBefore: PerformanceMetrics | null;
  metricsAfter: PerformanceMetrics | null;
}

export default function AgentStatusPanel({
  status,
  memory,
  metricsBefore,
  metricsAfter,
}: AgentStatusPanelProps) {
  const strategy = status?.strategy || { target_cpa: 50, max_cpm: 20, daily_budget: 1000 };
  const successRate = useMemo(() => computeSuccessRate(memory), [memory]);
  const confidence = useMemo(() => calculateConfidence(successRate, memory.length), [successRate, memory.length]);

  const spendProgress = Math.min(100, ((metricsAfter?.spend || 0) / strategy.daily_budget) * 100);
  const cpm =
    metricsAfter && metricsAfter.impressions > 0 ? (metricsAfter.spend / metricsAfter.impressions) * 1000 : 0;
  const cpa = metricsAfter && metricsAfter.clicks > 0 ? metricsAfter.spend / metricsAfter.clicks : 0;
  const cpmProgress = Math.min(100, (cpm / strategy.max_cpm) * 100);
  const cpaProgress = Math.min(100, (cpa / strategy.target_cpa) * 100);

  return (
    <div className="card p-5">
      <div className="flex items-center gap-2 mb-5">
        <Activity size={18} className="text-accent" />
        <h3 className="text-base font-semibold text-slate-100">Agent 状态监控</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <ProgressBlock
          icon={<Target size={16} />}
          label="Spend / Daily Budget"
          actual={formatCurrency(metricsAfter?.spend || 0)}
          target={formatCurrency(strategy.daily_budget)}
          progress={spendProgress}
          color="bg-accent"
        />
        <ProgressBlock
          icon={<TrendingUp size={16} />}
          label="CPM / Max CPM"
          actual={`¥${cpm.toFixed(2)}`}
          target={`¥${strategy.max_cpm.toFixed(2)}`}
          progress={cpmProgress}
          color="bg-warning"
        />
        <ProgressBlock
          icon={<BarChart3 size={16} />}
          label="CPA / Target CPA"
          actual={`¥${cpa.toFixed(2)}`}
          target={`¥${strategy.target_cpa.toFixed(2)}`}
          progress={cpaProgress}
          color="bg-success"
        />

        <div className="flex items-center justify-center">
          <GaugeChart value={confidence} label="决策置信度" />
        </div>
      </div>

      <div className="mt-5 grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KpiStat label="决策成功率 (近10次)" value={`${successRate}%`} />
        <KpiStat label="记忆条目数" value={`${memory.length}`} />
        <KpiStat label="最新动作" value={status?.last_action ? actionLabel(status.last_action) : '-'} />
      </div>

      {metricsBefore && metricsAfter && (
        <div className="mt-5 pt-4 border-t border-slate-700/50 grid grid-cols-2 sm:grid-cols-4 gap-4">
          <MiniDelta label="Impressions" before={metricsBefore.impressions} after={metricsAfter.impressions} />
          <MiniDelta label="Clicks" before={metricsBefore.clicks} after={metricsAfter.clicks} />
          <MiniDelta label="CTR" before={metricsBefore.ctr} after={metricsAfter.ctr} isPercent />
          <MiniDelta label="ROI" before={metricsBefore.roi} after={metricsAfter.roi} />
        </div>
      )}
    </div>
  );
}

function ProgressBlock({
  icon,
  label,
  actual,
  target,
  progress,
  color,
}: {
  icon: ReactNode;
  label: string;
  actual: string;
  target: string;
  progress: number;
  color: string;
}) {
  return (
    <div>
      <div className="flex items-center gap-2 text-sm text-muted mb-2">
        {icon}
        {label}
      </div>
      <div className="flex items-baseline gap-2 mb-2">
        <span className="text-xl font-bold text-slate-100">{actual}</span>
        <span className="text-xs text-muted">/ {target}</span>
      </div>
      <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full transition-all duration-700', color)} style={{ width: `${progress}%` }} />
      </div>
      <p className="text-[10px] text-muted mt-1">{progress.toFixed(1)}% of target</p>
    </div>
  );
}

function KpiStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-slate-800/40 rounded-lg p-3">
      <p className="text-xs text-muted">{label}</p>
      <p className="text-lg font-semibold text-slate-100">{value}</p>
    </div>
  );
}

function MiniDelta({
  label,
  before,
  after,
  isPercent,
}: {
  label: string;
  before: number;
  after: number;
  isPercent?: boolean;
}) {
  const delta = before !== 0 ? ((after - before) / Math.abs(before)) * 100 : 0;
  const displayAfter = isPercent ? `${(after * 100).toFixed(2)}%` : after.toFixed(2);
  return (
    <div>
      <p className="text-xs text-muted">{label}</p>
      <div className="flex items-center gap-2">
        <span className="text-base font-mono text-slate-100">{displayAfter}</span>
        {before !== 0 && (
          <span className={cn('text-xs', delta >= 0 ? 'text-success' : 'text-danger')}>
            {delta >= 0 ? '↑' : '↓'} {Math.abs(delta).toFixed(1)}%
          </span>
        )}
      </div>
    </div>
  );
}
