import { useEffect, useRef } from 'react';
import { BrainCircuit, CheckCircle2, ChevronDown, ChevronUp, Code, Eye, Zap } from 'lucide-react';

import { cn } from '../../utils/cn';
import { actionColor, actionLabel, FlowArrow, formatCurrency, formatPercent, MetricBadge } from './utils';
import type { AgentIteration, StepDurations } from './types';

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
        <h3 className="text-base font-semibold text-slate-100">Iteration #{iteration.iteration}</h3>
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
            {Object.keys(action.parameters).length > 0 ? JSON.stringify(action.parameters) : '无参数'}
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

interface DecisionTimelineProps {
  iterations: AgentIteration[];
  expandedMap: Record<number, boolean>;
  onToggleExpand: (iteration: number) => void;
  durations: StepDurations;
}

export default function AgentStep({
  iterations,
  expandedMap,
  onToggleExpand,
  durations,
}: DecisionTimelineProps) {
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
