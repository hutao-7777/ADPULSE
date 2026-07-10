import { Database, Layers } from 'lucide-react';

import { useDataSourceStore } from '../stores/dataSourceStore';

export default function DataSourceBadge() {
  const { activeSource } = useDataSourceStore();

  if (activeSource === 'mock') return null;

  const isAll = activeSource === 'all';

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-500/20 text-green-400 border border-green-500/30">
      {isAll ? <Layers size={11} /> : <Database size={11} />}
      {isAll ? '全部数据' : 'iPinYou 真实数据'}
    </span>
  );
}
