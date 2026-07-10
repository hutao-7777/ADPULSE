import { useEffect } from 'react';
import { Database, Layers, Sparkles } from 'lucide-react';

import { cn } from '../utils/cn';
import { useDataSourceStore } from '../stores/dataSourceStore';

export default function DataSourceSwitcher() {
  const {
    activeSource,
    availableSources,
    setActiveSource,
    fetchAvailableSources,
    hasRealData,
  } = useDataSourceStore();

  useEffect(() => {
    fetchAvailableSources();
    const interval = setInterval(fetchAvailableSources, 30000);
    return () => clearInterval(interval);
  }, [fetchAvailableSources]);

  if (!hasRealData()) {
    return (
      <div className="px-3 py-2 text-xs text-slate-500 flex items-center gap-1.5">
        <Sparkles size={12} />
        <span>Mock 数据</span>
      </div>
    );
  }

  const sourcesWithAll = [
    ...availableSources,
    { name: 'all', label: '全部数据', record_count: 0 },
  ];

  return (
    <div className="px-2 py-2">
      <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1.5 px-1">
        数据源
      </div>
      <div className="flex flex-col gap-1">
        {sourcesWithAll.map((source) => (
          <button
            key={source.name}
            onClick={() => setActiveSource(source.name)}
            className={cn(
              'flex items-center gap-2 px-2 py-1.5 rounded text-xs transition-colors text-left',
              activeSource === source.name
                ? 'bg-blue-500/20 text-blue-400 font-medium'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            )}
          >
            {source.name === 'mock' && <Sparkles size={13} />}
            {source.name === 'all' && <Layers size={13} />}
            {source.name !== 'mock' && source.name !== 'all' && <Database size={13} />}
            <span className="flex-1">{source.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
