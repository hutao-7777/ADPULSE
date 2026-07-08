import { useEffect, useId, useMemo, useRef, useState } from 'react';
import {
  BrainCircuit,
  ChevronDown,
  ChevronUp,
  Loader2,
  Activity,
  Eye,
  Zap,
  Code,
  BarChart3,
  History,
  Target,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  X,
  Settings2,
} from 'lucide-react';

import { apiRequest } from '../utils/api';

// ------------------------------------------------------------------
// 类型定义
// ------------------------------------------------------------------

interface DSPStatus {
  name: string;
  budget_remaining: number;
  target_segments: string[];
  max_cpm: number;
  pacing_rate: number;
  bidding_strategy: string;
}

interface PerformanceMetrics {
  impressions: number;
  clicks: number;
  ctr: number;
  spend: number;
  revenue: number;
  roi: number;
  spend_ratio: number;
  budget: number;
  days: number;
}

interface ThoughtData {
  performance: PerformanceMetrics;
  benchmark: {
    avg_cpm: number;
    avg_ctr: number;
    competition_level: string;
  };
  derived: {
    win_rate: number;
    avg_winning_cpm: number;
    auction_count: number;
  };
  creative?: {
    exists?: boolean;
    name?: string;
    ai_score?: number;
    fatigue_score?: number;
    ctr?: number;
  };
}

interface ThoughtStep {
  analysis: string;
  data: ThoughtData;
}

interface ActionStep {
  action: string;
  parameters: Record<string, unknown>;
  reasoning: string;
}

interface ObservationStep {
  observation: string;
  expected_vs_actual: Record<string, number>;
  learned: string;
}

interface AgentIteration {
  iteration: number;
  thought: ThoughtStep;
  action: ActionStep;
  observation: ObservationStep;
}

interface AgentRunResponse {
  campaign_id: string;
  iterations: AgentIteration[];
  final_recommendation: string;
  metrics_before: PerformanceMetrics;
  metrics_after: PerformanceMetrics;
}

interface AgentMemoryEntry {
  timestamp: string;
  action: string;
  parameters: Record<string, unknown>;
  result: Record<string, unknown>;
  expected_vs_actual: Record<string, number>;
  learned: string;
}

interface AgentMemoryResponse {
  campaign_id: string;
  memory: AgentMemoryEntry[];
}

interface AgentStatus {
  campaign_id: string;
  strategy: {
    target_cpa: number;
    max_cpm: number;
    daily_budget: number;
  };
  memory_size: number;
  current_state: string;
  last_action: string | null;
}

interface StepDurations {
  think: number;
  act: number;
  observe: number;
}

// ------------------------------------------------------------------
// 工具函数
// ------------------------------------------------------------------

function cn(...classes: (string | false | undefined)[]) {
  return classes.filter(Boolean).join(' ');
}

function formatPercent(value: number, digits = 2): string {
  return `${(value * 100).toFixed(digits)}%`;
}

function formatCurrency(value: number): string {
  return `¥${value.toFixed(2)}`;
}

function actionColor(action: string): { bg: string; text: string; border: string; label: string } {
  switch (action) {
    case 'increase_bid':
      return { bg: 'bg-success/10', text: 'text-success', border: 'border-success/40', label: '提高出价' };
    case 'decrease_bid':
    case 'optimize_creative':
      return { bg: 'bg-warning/10', text: 'text-warning', border: 'border-warning/40', label: action === 'decrease_bid' ? '降低出价' : '优化创意' };
    case 'switch_creative':
      return { bg: 'bg-accent/10', text: 'text-accent', border: 'border-accent/40', label: '更换创意' };
    case 'maintain_strategy':
    default:
      return { bg: 'bg-slate-600/20', text: 'text-slate-300', border: 'border-slate-500/40', label: '保持策略' };
  }
}

function actionLabel(action: string): string {
  return actionColor(action).label;
}

function computeSuccessRate(memory: AgentMemoryEntry[]): number {
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

function calculateConfidence(successRate: number, memorySize: number): number {
  return Math.min(95, Math.round(35 + successRate * 0.45 + Math.min(memorySize, 12) * 2.5));
}

// ------------------------------------------------------------------
// FlowArrow 动画箭头
// ------------------------------------------------------------------

function FlowArrow({ durationMs }: { durationMs: number }) {
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

// ------------------------------------------------------------------
// AgentControls 控制面板
// ------------------------------------------------------------------

interface AgentControlsProps {
  dsps: DSPStatus[];
  selectedCampaign: string;
  onSelectCampaign: (id: string) => void;
  strategy: { target_cpa: number; max_cpm: number; daily_budget: number };
  onStrategyChange: (strategy: { target_cpa: number; max_cpm: number; daily_budget: number }) => void;
  loopCount: number;
  onLoopCountChange: (count: number) => void;
  onRun: () => void;
  running: boolean;
}

function AgentControls({
  dsps,
  selectedCampaign,
  onSelectCampaign,
  strategy,
  onStrategyChange,
  loopCount,
  onLoopCountChange,
  onRun,
  running,
}: AgentControlsProps) {
  const [showStrategy, setShowStrategy] = useState(false);

  const updateField = (field: keyof typeof strategy, value: string) => {
    const num = parseFloat(value);
    if (Number.isNaN(num) || num < 0) return;
    onStrategyChange({ ...strategy, [field]: num });
  };

  return (
    <div className="card p-5 space-y-4">
      <div className="flex flex-col lg:flex-row lg:items-end gap-4">
        <div className="flex-1">
          <label className="block text-xs text-muted mb-1.5">Campaign / DSP</label>
          <select
            value={selectedCampaign}
            onChange={(e) => onSelectCampaign(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-accent"
          >
            <option value="">选择 Campaign</option>
            {dsps.map((dsp) => (
              <option key={dsp.name} value={dsp.name}>
                {dsp.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs text-muted mb-1.5">循环次数</label>
          <div className="flex items-center gap-2">
            {[1, 3, 5].map((n) => (
              <button
                key={n}
                onClick={() => onLoopCountChange(n)}
                className={cn(
                  'px-3 py-2 rounded-lg text-sm font-medium border transition-colors',
                  loopCount === n
                    ? 'bg-accent/15 text-accent border-accent/50'
                    : 'bg-slate-800 text-slate-300 border-slate-700 hover:border-slate-600'
                )}
              >
                {n} 次
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={onRun}
          disabled={running || !selectedCampaign}
          className="btn-primary flex items-center justify-center gap-2 text-base px-6 py-2.5 disabled:opacity-60 disabled:cursor-not-allowed min-w-[180px]"
        >
          {running ? <Loader2 size={20} className="animate-spin" /> : <BrainCircuit size={20} />}
          {running ? 'Agent 运行中...' : '运行 Agent 决策循环'}
        </button>
      </div>

      <div>
        <button
          onClick={() => setShowStrategy((s) => !s)}
          className="flex items-center gap-2 text-sm text-slate-300 hover:text-slate-100"
        >
          <Settings2 size={16} />
          Agent 策略配置
          {showStrategy ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>

        {showStrategy && (
          <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-4 animate-fade-in-slide-up">
            <div>
              <label className="block text-xs text-muted mb-1.5">Target CPA (¥)</label>
              <input
                type="number"
                value={strategy.target_cpa}
                onChange={(e) => updateField('target_cpa', e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-accent"
              />
            </div>
            <div>
              <label className="block text-xs text-muted mb-1.5">Max CPM (¥)</label>
              <input
                type="number"
                value={strategy.max_cpm}
                onChange={(e) => updateField('max_cpm', e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-accent"
              />
            </div>
            <div>
              <label className="block text-xs text-muted mb-1.5">Daily Budget (¥)</label>
              <input
                type="number"
                value={strategy.daily_budget}
                onChange={(e) => updateField('daily_budget', e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-accent"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}


// ------------------------------------------------------------------
// IterationCard 单个迭代卡片
// ------------------------------------------------------------------

interface IterationCardProps {
  iteration: AgentIteration;
  isLast: boolean;
  expanded: boolean;
  onToggleExpand: () => void;
  durations: StepDurations;
}

function IterationCard({ iteration, isLast, expanded, onToggleExpand, durations }: IterationCardProps) {
  const { thought, action, observation } = iteration;
  const actionTheme = actionColor(action.action);
  const isHold = action.action === 'maintain_strategy';

  const performance = thought.data.performance || {};
  const derived = thought.data.derived || {};

  return (
    <div className="card p-5 animate-fade-in-slide-up">
      <div className="flex items-center gap-3 mb-4">
        <span className="flex items-center justify-center w-8 h-8 rounded-full bg-accent/15 text-accent text-sm font-bold">
          {iteration.iteration}
        </span>
        <h3 className="text-base font-semibold text-slate-100">
          Iteration #{iteration.iteration}
        </h3>
        {isHold && (
          <span className="ml-auto inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-slate-600/20 text-slate-300 border border-slate-500/40">
            <CheckCircle2 size={12} />
            Hold
          </span>
        )}
      </div>

      {/* Step 1: Think */}
      <div className="relative pl-4 border-l-4 border-accent bg-slate-800/30 rounded-r-xl p-4">
        <div className="flex items-center gap-2 mb-2">
          <BrainCircuit size={18} className="text-accent" />
          <h4 className="text-sm font-semibold text-slate-100">Step 1: 数据收集与分析</h4>
        </div>
        <p className="text-sm text-slate-300 leading-relaxed">{thought.analysis}</p>

        <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3">
          <MetricBadge label="CTR" value={formatPercent(performance.ctr || 0)} />
          <MetricBadge label="Spend" value={formatCurrency(performance.spend || 0)} />
          <MetricBadge label="ROI" value={`${(performance.roi || 0).toFixed(2)}x`} />
          <MetricBadge label="胜率" value={formatPercent(derived.win_rate || 0)} />
        </div>

        <button
          onClick={onToggleExpand}
          className="mt-3 flex items-center gap-1 text-xs text-accent hover:text-blue-400"
        >
          <Code size={12} />
          {expanded ? '收起原始数据' : '展开原始数据 JSON'}
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </button>

        {expanded && (
          <pre className="mt-3 text-[11px] text-slate-300 bg-slate-900 p-3 rounded-lg overflow-auto max-h-64">
            {JSON.stringify(thought.data, null, 2)}
          </pre>
        )}
      </div>

      <FlowArrow durationMs={durations.think} />

      {/* Step 2: Act */}
      <div className="relative pl-4 border-l-4 border-purple-500 bg-slate-800/30 rounded-r-xl p-4">
        <div className="flex items-center gap-2 mb-2">
          <Zap size={18} className="text-purple-400" />
          <h4 className="text-sm font-semibold text-slate-100">Step 2: 策略决策</h4>
        </div>

        <div className="flex flex-wrap items-center gap-3 mb-3">
          <span
            className={cn(
              'px-2.5 py-1 rounded-lg text-xs font-medium border',
              actionTheme.bg,
              actionTheme.text,
              actionTheme.border
            )}
          >
            {actionLabel(action.action)}
          </span>
          <span className="text-xs text-muted font-mono">
            {Object.keys(action.parameters).length > 0
              ? JSON.stringify(action.parameters)
              : '无参数'}
          </span>
        </div>

        <p className="text-sm text-slate-300 leading-relaxed">{action.reasoning}</p>
      </div>

      <FlowArrow durationMs={durations.act} />

      {/* Step 3: Observe */}
      <div className="relative pl-4 border-l-4 border-success bg-slate-800/30 rounded-r-xl p-4">
        <div className="flex items-center gap-2 mb-2">
          <Eye size={18} className="text-success" />
          <h4 className="text-sm font-semibold text-slate-100">Step 3: 效果评估</h4>
        </div>

        <p className="text-sm text-slate-300 leading-relaxed mb-3">{observation.observation}</p>

        {observation.expected_vs_actual && Object.keys(observation.expected_vs_actual).length > 0 && (
          <div className="overflow-x-auto mb-3">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-muted border-b border-slate-700">
                  <th className="pb-2 font-medium">指标</th>
                  <th className="pb-2 font-medium">预期变化</th>
                  <th className="pb-2 font-medium">实际反馈</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(observation.expected_vs_actual).map(([key, value]) => {
                  const isExpected = key.startsWith('expected_');
                  if (!isExpected) return null;
                  const actualKey = key.replace('expected_', 'actual_');
                  const actualValue = observation.expected_vs_actual[actualKey];
                  const label = key
                    .replace('expected_', '')
                    .replace(/_/g, ' ')
                    .replace('pct', '(%)');
                  return (
                    <tr key={key} className="border-b border-slate-800/50 last:border-0">
                      <td className="py-2 text-slate-300 capitalize">{label}</td>
                      <td className="py-2 font-mono text-slate-300">{value}%</td>
                      <td className="py-2 font-mono text-slate-300">{actualValue ?? '-'}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex items-start gap-2 italic text-sm text-slate-300 border-l-2 border-success/40 pl-3">
          <span className="text-success">“</span>
          {observation.learned}
          <span className="text-success">”</span>
        </div>
      </div>

      {isHold && isLast && (
        <div className="mt-4 flex items-center gap-2 text-sm text-success bg-success/5 border border-success/30 rounded-lg px-4 py-3">
          <CheckCircle2 size={16} />
          Agent 认为当前策略最优，结束循环
        </div>
      )}
    </div>
  );
}

function MetricBadge({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-slate-900/60 rounded-lg px-3 py-2">
      <p className="text-[10px] text-muted">{label}</p>
      <p className="text-sm font-mono text-slate-100">{value}</p>
    </div>
  );
}

// ------------------------------------------------------------------
// DecisionTimeline 决策时间线
// ------------------------------------------------------------------

interface DecisionTimelineProps {
  iterations: AgentIteration[];
  expandedMap: Record<number, boolean>;
  onToggleExpand: (iteration: number) => void;
  durations: StepDurations;
}

function DecisionTimeline({ iterations, expandedMap, onToggleExpand, durations }: DecisionTimelineProps) {
  const latestRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (latestRef.current && iterations.length > 0) {
      latestRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [iterations]);

  if (iterations.length === 0) {
    return (
      <div className="card p-10 flex flex-col items-center justify-center text-center min-h-[400px]">
        <BrainCircuit size={56} className="text-muted mb-4" />
        <p className="text-muted">点击上方按钮运行 Agent，查看完整 ReAct 决策链路</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {iterations.map((it, idx) => (
        <div key={it.iteration} ref={idx === iterations.length - 1 ? latestRef : undefined}>
          <IterationCard
            iteration={it}
            isLast={idx === iterations.length - 1}
            expanded={!!expandedMap[it.iteration]}
            onToggleExpand={() => onToggleExpand(it.iteration)}
            durations={durations}
          />
        </div>
      ))}
    </div>
  );
}

// ------------------------------------------------------------------
// AgentMemory Agent 记忆侧边栏
// ------------------------------------------------------------------

interface AgentMemoryProps {
  memory: AgentMemoryEntry[];
  expandedMap: Record<number, boolean>;
  onToggle: (idx: number) => void;
}

function AgentMemory({ memory, expandedMap, onToggle }: AgentMemoryProps) {
  const recent = memory.slice(-10).reverse();

  return (
    <div className="card p-4 h-full flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <History size={18} className="text-accent" />
        <h3 className="text-base font-semibold text-slate-100">Agent 记忆</h3>
        <span className="ml-auto text-xs text-muted">最近 {recent.length} 条</span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 pr-1">
        {recent.length === 0 && (
          <p className="text-center text-muted text-sm py-6">暂无决策历史</p>
        )}

        {recent.map((entry, idx) => {
          const originalIdx = memory.length - 1 - idx;
          const theme = actionColor(entry.action);
          const expanded = !!expandedMap[originalIdx];
          return (
            <div
              key={originalIdx}
              className="bg-slate-800/40 border border-slate-700/30 rounded-lg p-3 transition-colors hover:border-slate-600"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span
                    className={cn(
                      'inline-block px-2 py-0.5 rounded text-[10px] font-medium border mb-1',
                      theme.bg,
                      theme.text,
                      theme.border
                    )}
                  >
                    {actionLabel(entry.action)}
                  </span>
                  <p className="text-xs text-muted">
                    {new Date(entry.timestamp).toLocaleString('zh-CN')}
                  </p>
                </div>
                <button onClick={() => onToggle(originalIdx)} className="text-muted hover:text-slate-100">
                  {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </button>
              </div>

              <p className="mt-2 text-xs text-slate-300 line-clamp-2">{entry.learned}</p>

              {expanded && (
                <div className="mt-3 space-y-2 animate-fade-in-slide-up">
                  <div>
                    <p className="text-[10px] text-muted">Parameters</p>
                    <pre className="text-[10px] text-slate-300 bg-slate-900 p-2 rounded overflow-auto">
                      {JSON.stringify(entry.parameters, null, 2)}
                    </pre>
                  </div>
                  <div>
                    <p className="text-[10px] text-muted">Result</p>
                    <pre className="text-[10px] text-slate-300 bg-slate-900 p-2 rounded overflow-auto">
                      {JSON.stringify(entry.result, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}


// ------------------------------------------------------------------
// GaugeChart 半圆置信度仪表
// ------------------------------------------------------------------

function GaugeChart({ value, label }: { value: number; label: string }) {
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

// ------------------------------------------------------------------
// AgentStatusPanel Agent 状态监控
// ------------------------------------------------------------------

interface AgentStatusPanelProps {
  status: AgentStatus | null;
  memory: AgentMemoryEntry[];
  metricsBefore: PerformanceMetrics | null;
  metricsAfter: PerformanceMetrics | null;
}

function AgentStatusPanel({ status, memory, metricsBefore, metricsAfter }: AgentStatusPanelProps) {
  const strategy = status?.strategy || { target_cpa: 50, max_cpm: 20, daily_budget: 1000 };
  const successRate = useMemo(() => computeSuccessRate(memory), [memory]);
  const confidence = useMemo(() => calculateConfidence(successRate, memory.length), [successRate, memory.length]);

  const spendProgress = Math.min(
    100,
    ((metricsAfter?.spend || 0) / strategy.daily_budget) * 100
  );
  const cpm =
    metricsAfter && metricsAfter.impressions > 0
      ? (metricsAfter.spend / metricsAfter.impressions) * 1000
      : 0;
  const cpa =
    metricsAfter && metricsAfter.clicks > 0
      ? metricsAfter.spend / metricsAfter.clicks
      : 0;
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
        <KpiStat
          label="最新动作"
          value={status?.last_action ? actionLabel(status.last_action) : '-'}
        />
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
  icon: React.ReactNode;
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
        <div
          className={cn('h-full rounded-full transition-all duration-700', color)}
          style={{ width: `${progress}%` }}
        />
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
  const displayAfter = isPercent ? formatPercent(after) : after.toFixed(2);
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

// ------------------------------------------------------------------
// AgentLoop 主页面
// ------------------------------------------------------------------

function AgentLoop() {
  const [dsps, setDsps] = useState<DSPStatus[]>([]);
  const [selectedCampaign, setSelectedCampaign] = useState('');
  const [strategy, setStrategy] = useState({ target_cpa: 50, max_cpm: 20, daily_budget: 1000 });
  const [loopCount, setLoopCount] = useState(3);
  const [running, setRunning] = useState(false);
  const [iterations, setIterations] = useState<AgentIteration[]>([]);
  const [metricsBefore, setMetricsBefore] = useState<PerformanceMetrics | null>(null);
  const [metricsAfter, setMetricsAfter] = useState<PerformanceMetrics | null>(null);
  const [memory, setMemory] = useState<AgentMemoryEntry[]>([]);
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedThink, setExpandedThink] = useState<Record<number, boolean>>({});
  const [expandedMemory, setExpandedMemory] = useState<Record<number, boolean>>({});
  const [durations, setDurations] = useState<StepDurations>({ think: 120, act: 60, observe: 90 });

  // 获取 DSP / Campaign 列表
  useEffect(() => {
    apiRequest<DSPStatus[]>('/rtb/dsps')
      .then((data) => {
        setDsps(data);
        if (data.length > 0 && !selectedCampaign) {
          setSelectedCampaign(data[0].name);
        }
      })
      .catch((err) => console.error('获取 DSP 列表失败:', err));
  }, []);

  // Campaign 切换时拉取 Agent 状态与记忆
  useEffect(() => {
    if (!selectedCampaign) return;
    fetchStatusAndMemory(selectedCampaign);
  }, [selectedCampaign]);

  const fetchStatusAndMemory = async (campaignId: string) => {
    try {
      const [s, m] = await Promise.all([
        apiRequest<AgentStatus>(`/agent/${campaignId}/status`),
        apiRequest<AgentMemoryResponse>(`/agent/${campaignId}/memory`),
      ]);
      setStatus(s);
      setStrategy(s.strategy);
      setMemory(m.memory);
    } catch (err) {
      console.error('获取 Agent 状态失败:', err);
    }
  };

  const handleRun = async () => {
    if (!selectedCampaign) return;
    setRunning(true);
    setError(null);
    setIterations([]);
    setExpandedThink({});
    setMetricsBefore(null);
    setMetricsAfter(null);

    const start = performance.now();
    try {
      // 1. 更新策略
      await apiRequest(`/agent/${selectedCampaign}/strategy`, {
        method: 'POST',
        body: JSON.stringify(strategy),
      });

      // 2. 运行决策循环
      const runRes = await apiRequest<AgentRunResponse>(`/agent/${selectedCampaign}/run`, {
        method: 'POST',
        body: JSON.stringify({ max_iterations: loopCount }),
      });

      const end = performance.now();
      const totalMs = Math.max(1, end - start);
      const stepMs = Math.round(totalMs / Math.max(1, runRes.iterations.length * 3));
      setDurations({
        think: Math.round(stepMs * 1.2),
        act: Math.round(stepMs * 0.8),
        observe: Math.round(stepMs * 1.0),
      });

      setIterations(runRes.iterations);
      setMetricsBefore(runRes.metrics_before);
      setMetricsAfter(runRes.metrics_after);

      // 3. 刷新状态与记忆
      await fetchStatusAndMemory(selectedCampaign);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Agent 运行失败');
    } finally {
      setRunning(false);
    }
  };

  const toggleThink = (iteration: number) => {
    setExpandedThink((prev) => ({ ...prev, [iteration]: !prev[iteration] }));
  };

  const toggleMemory = (idx: number) => {
    setExpandedMemory((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  return (
    <div className="space-y-4 pb-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-100">Agent Loop</h1>
        <p className="text-muted mt-1">可视化 AI Agent 的 Think → Act → Observe 完整决策链路</p>
      </header>

      <AgentControls
        dsps={dsps}
        selectedCampaign={selectedCampaign}
        onSelectCampaign={setSelectedCampaign}
        strategy={strategy}
        onStrategyChange={setStrategy}
        loopCount={loopCount}
        onLoopCountChange={setLoopCount}
        onRun={handleRun}
        running={running}
      />

      {error && (
        <div className="card p-4 border-danger/40 bg-danger/5 flex items-start gap-3">
          <AlertCircle size={20} className="text-danger flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm text-danger font-medium">运行出错</p>
            <p className="text-sm text-slate-300 mt-1">{error}</p>
          </div>
          <button onClick={() => setError(null)} className="text-muted hover:text-slate-100">
            <X size={16} />
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-10 gap-4">
        <div className="lg:col-span-7 space-y-4">
          <DecisionTimeline
            iterations={iterations}
            expandedMap={expandedThink}
            onToggleExpand={toggleThink}
            durations={durations}
          />
        </div>
        <div className="lg:col-span-3">
          <AgentMemory memory={memory} expandedMap={expandedMemory} onToggle={toggleMemory} />
        </div>
      </div>

      <AgentStatusPanel
        status={status}
        memory={memory}
        metricsBefore={metricsBefore}
        metricsAfter={metricsAfter}
      />
    </div>
  );
}

export default AgentLoop;
