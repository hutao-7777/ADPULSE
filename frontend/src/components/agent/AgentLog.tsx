import { ChevronDown, ChevronUp, History } from 'lucide-react';

import { cn } from '../../utils/cn';
import { actionColor, actionLabel } from './utils';
import type { AgentMemoryEntry } from './types';

interface AgentLogProps {
  memory: AgentMemoryEntry[];
  expandedMap: Record<number, boolean>;
  onToggle: (idx: number) => void;
}

export default function AgentLog({ memory, expandedMap, onToggle }: AgentLogProps) {
  const recent = memory.slice(-10).reverse();

  return (
    <div className="card p-4 h-full flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <History size={18} className="text-accent" />
        <h3 className="text-base font-semibold text-slate-100">Agent 记忆</h3>
        <span className="ml-auto text-xs text-muted">最近 {recent.length} 条</span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 pr-1">
        {recent.length === 0 && <p className="text-center text-muted text-sm py-6">暂无决策历史</p>}

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
