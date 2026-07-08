import type { ABTest, CampaignOption } from './types';

export function cnLocal(...classes: (string | false | undefined)[]) {
  return classes.filter(Boolean).join(' ');
}

export function formatDate(iso: string | null): string {
  if (!iso) return '-';
  return new Date(iso).toLocaleString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function getStatusBadge(status: ABTest['status']) {
  const map: Record<string, { label: string; className: string; pulse?: boolean }> = {
    draft: { label: '草稿', className: 'bg-slate-600/20 text-slate-300 border-slate-500/30' },
    running: { label: '运行中', className: 'bg-success/15 text-success border-success/40', pulse: true },
    stopped: { label: '已停止', className: 'bg-danger/15 text-danger border-danger/40' },
    completed: { label: '已完成', className: 'bg-accent/15 text-accent border-accent/40' },
  };
  return map[status] || map.draft;
}

export function metricLabel(metric: string): string {
  const map: Record<string, string> = {
    ctr: 'CTR',
    conversion_rate: 'Conversion Rate',
    roi: 'ROI',
  };
  return map[metric] || metric;
}

export function formatMetric(value: number, metric: string): string {
  if (metric === 'ctr' || metric === 'conversion_rate') return `${(value * 100).toFixed(2)}%`;
  if (metric === 'roi') return `${value.toFixed(2)}x`;
  return value.toFixed(2);
}

export const MOCK_CAMPAIGNS: CampaignOption[] = [
  { id: '12345678-1234-1234-1234-123456789abc', name: '夏季促销活动' },
  { id: '22345678-1234-1234-1234-123456789abc', name: '品牌认知推广' },
  { id: '32345678-1234-1234-1234-123456789abc', name: '新品首发' },
];
