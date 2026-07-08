import { useState, type SVGProps } from 'react';
import { Activity, Minus, Plus, X } from 'lucide-react';

import { apiRequest } from '../../utils/api';
import { cn } from '../../utils/cn';
import { MOCK_CAMPAIGNS } from './utils';

interface TestFormProps {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export default function TestForm({ open, onClose, onCreated }: TestFormProps) {
  const [name, setName] = useState('');
  const [campaignId, setCampaignId] = useState(MOCK_CAMPAIGNS[0].id);
  const [metric, setMetric] = useState<'ctr' | 'conversion_rate' | 'roi'>('ctr');
  const [trafficSplit, setTrafficSplit] = useState(50);
  const [variants, setVariants] = useState([
    { name: 'control', pct: 50 },
    { name: 'variant_a', pct: 50 },
  ]);
  const [submitting, setSubmitting] = useState(false);

  if (!open) return null;

  const addVariant = () => {
    setVariants((prev) => [
      ...prev,
      { name: `variant_${String.fromCharCode(98 + prev.length - 1)}`, pct: 0 },
    ]);
  };

  const removeVariant = (idx: number) => {
    setVariants((prev) => prev.filter((_, i) => i !== idx));
  };

  const updateVariant = (idx: number, field: 'name' | 'pct', value: string | number) => {
    setVariants((prev) => prev.map((v, i) => (i === idx ? { ...v, [field]: value } : v)));
  };

  const totalPct = variants.reduce((sum, v) => sum + v.pct, 0);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return alert('请输入测试名称');
    if (totalPct !== 100) return alert('Variant 流量占比之和必须等于 100%');

    setSubmitting(true);
    try {
      await apiRequest('/abtests', {
        method: 'POST',
        body: JSON.stringify({
          name,
          campaign_id: campaignId,
          metric_target: metric,
          traffic_split: trafficSplit / 100,
          variants_config: variants.map((v) => ({ name: v.name, traffic_pct: v.pct / 100 })),
        }),
      });
      onCreated();
      onClose();
      setName('');
      setVariants([
        { name: 'control', pct: 50 },
        { name: 'variant_a', pct: 50 },
      ]);
    } catch (err) {
      alert(err instanceof Error ? err.message : '创建失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="card w-full max-w-lg max-h-[90vh] overflow-y-auto p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold text-slate-100">新建 A/B 测试</h2>
          <button onClick={onClose} className="text-muted hover:text-slate-100">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs text-muted mb-1.5">测试名称</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-accent"
              placeholder="例如：落地页按钮文案测试"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-muted mb-1.5">关联 Campaign</label>
              <select
                value={campaignId}
                onChange={(e) => setCampaignId(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-accent"
              >
                {MOCK_CAMPAIGNS.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-muted mb-1.5">目标指标</label>
              <select
                value={metric}
                onChange={(e) => setMetric(e.target.value as typeof metric)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-accent"
              >
                <option value="ctr">CTR</option>
                <option value="conversion_rate">Conversion Rate</option>
                <option value="roi">ROI</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs text-muted mb-1.5">实验流量比例: {trafficSplit}%</label>
            <input
              type="range"
              min={0}
              max={100}
              value={trafficSplit}
              onChange={(e) => setTrafficSplit(parseInt(e.target.value))}
              className="w-full accent-accent"
            />
            <p className="text-[10px] text-muted mt-1">剩余流量将走 control variant</p>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs text-muted">Variant 配置</label>
              <button
                type="button"
                onClick={addVariant}
                className="text-xs text-accent hover:text-blue-400 flex items-center gap-1"
              >
                <Plus size={12} /> 添加
              </button>
            </div>
            <div className="space-y-2">
              {variants.map((variant, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <input
                    value={variant.name}
                    onChange={(e) => updateVariant(idx, 'name', e.target.value)}
                    className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-accent"
                    placeholder="variant name"
                  />
                  <div className="w-24 relative">
                    <input
                      type="number"
                      min={0}
                      max={100}
                      value={variant.pct}
                      onChange={(e) => updateVariant(idx, 'pct', parseInt(e.target.value) || 0)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-accent pr-6"
                    />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted">%</span>
                  </div>
                  {variants.length > 2 && (
                    <button
                      type="button"
                      onClick={() => removeVariant(idx)}
                      className="p-2 text-muted hover:text-danger"
                    >
                      <Minus size={16} />
                    </button>
                  )}
                </div>
              ))}
            </div>
            <p className={cn('text-[10px] mt-1', totalPct === 100 ? 'text-success' : 'text-warning')}>
              流量占比总计: {totalPct}% {totalPct !== 100 && '(需等于 100%)'}
            </p>
          </div>

          <div className="pt-2 flex justify-end gap-3">
            <button type="button" onClick={onClose} className="btn-secondary text-sm">
              取消
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="btn-primary text-sm flex items-center gap-2 disabled:opacity-60"
            >
              {submitting ? <Loader className="w-3.5 h-3.5 animate-spin" /> : <Plus size={14} />}
              创建测试
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Loader(props: SVGProps<SVGSVGElement> & { className?: string }) {
  return <Activity {...props} className={cn('animate-spin', props.className)} />;
}
