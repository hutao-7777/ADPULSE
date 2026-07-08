import { useState } from 'react';
import { BrainCircuit, ChevronDown, ChevronUp, Loader2, Settings2 } from 'lucide-react';

import { cn } from '../../utils/cn';
import type { DSPStatus } from './types';

interface AgentConfigProps {
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

export default function AgentConfig({
  dsps,
  selectedCampaign,
  onSelectCampaign,
  strategy,
  onStrategyChange,
  loopCount,
  onLoopCountChange,
  onRun,
  running,
}: AgentConfigProps) {
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
