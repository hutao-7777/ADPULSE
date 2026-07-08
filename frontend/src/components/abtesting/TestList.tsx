import { ChevronRight, Plus } from 'lucide-react';

import { cn } from '../../utils/cn';
import type { ABTest } from './types';
import { getStatusBadge, metricLabel } from './utils';

interface TestListProps {
  tests: ABTest[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  loading?: boolean;
}

export default function TestList({ tests, selectedId, onSelect, onNew, loading }: TestListProps) {
  return (
    <div className="card p-4 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-slate-100">测试列表</h2>
        <button onClick={onNew} className="btn-primary flex items-center gap-1.5 text-sm px-3 py-1.5">
          <Plus size={14} />
          新建测试
        </button>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 pr-1">
        {loading && (
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-24 bg-slate-800/50 rounded-lg animate-pulse" />
            ))}
          </div>
        )}

        {!loading && tests.length === 0 && (
          <div className="text-center py-10 text-muted text-sm">暂无 A/B 测试</div>
        )}

        {tests.map((test) => {
          const badge = getStatusBadge(test.status);
          return (
            <button
              key={test.id}
              onClick={() => onSelect(test.id)}
              className={cn(
                'w-full text-left p-4 rounded-xl border transition-all',
                selectedId === test.id
                  ? 'bg-accent/10 border-accent/50'
                  : 'bg-slate-800/30 border-slate-700/30 hover:border-slate-600 hover:bg-slate-800/50'
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-medium text-slate-100 line-clamp-1">{test.name}</p>
                <span
                  className={cn(
                    'flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium border shrink-0',
                    badge.className
                  )}
                >
                  {badge.pulse && (
                    <span className="relative flex h-1.5 w-1.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
                      <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-success" />
                    </span>
                  )}
                  {badge.label}
                </span>
              </div>

              <div className="mt-2 flex items-center gap-3 text-xs text-muted">
                <span>目标: {metricLabel(test.metric_target)}</span>
                <span>·</span>
                <span>
                  {test.start_date
                    ? `运行 ${Math.max(
                        0,
                        Math.floor((Date.now() - new Date(test.start_date).getTime()) / 86400000)
                      )} 天`
                    : '未开始'}
                </span>
              </div>

              <div className="mt-2 flex items-center gap-1 text-xs text-accent">
                <span>领先: {test.winner || '-'}</span>
                <ChevronRight size={12} />
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
