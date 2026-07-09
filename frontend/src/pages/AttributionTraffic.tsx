import { useEffect, useState } from 'react';
import { Activity, RefreshCw, TrendingUp, User } from 'lucide-react';

import { apiRequest } from '../utils/api';
import { mockAttribution, mockFraudAlerts, mockTrafficQuality } from '../utils/mockData';
import AttributionPanel from '../components/attribution-traffic/AttributionPanel';
import TrafficPanel from '../components/attribution-traffic/TrafficPanel';
import { CAMPAIGNS } from '../components/attribution-traffic/utils';
import type {
  AttributionResult,
  FraudAlert,
  TrafficQuality,
} from '../components/attribution-traffic/types';

function AttributionTraffic() {
  const [selectedCampaignId, setSelectedCampaignId] = useState(CAMPAIGNS[0].id);
  const [userId, setUserId] = useState('demo-user-001');
  const [activeModel, setActiveModel] = useState('first_touch');
  const [attribution, setAttribution] = useState<AttributionResult | null>(null);
  const [quality, setQuality] = useState<TrafficQuality>(mockTrafficQuality as TrafficQuality);
  const [alerts, setAlerts] = useState<FraudAlert[]>(mockFraudAlerts as FraudAlert[]);
  const [loadingAttribution, setLoadingAttribution] = useState(false);
  const [loadingTraffic, setLoadingTraffic] = useState(false);

  useEffect(() => {
    loadMockData();
  }, []);

  const loadMockData = () => {
    setAttribution(mockAttribution as AttributionResult);
    setActiveModel('first_touch');
    setQuality(mockTrafficQuality as TrafficQuality);
    setAlerts(mockFraudAlerts as FraudAlert[]);
  };

  const initSampleJourney = async () => {
    setLoadingAttribution(true);
    try {
      const conversionValue = 1000;
      const baseTime = new Date();
      const touchpointInputs = [
        { channel: 'display', event_type: 'impression', offsetHours: -96 },
        { channel: 'search_ads', event_type: 'impression', offsetHours: -72 },
        { channel: 'display', event_type: 'click', offsetHours: -48 },
        { channel: 'social_media', event_type: 'click', offsetHours: -24 },
      ];

      const touchpoints = touchpointInputs.map((tp, idx) => ({
        channel: tp.channel,
        campaign_id: selectedCampaignId,
        timestamp: new Date(baseTime.getTime() + tp.offsetHours * 3600000).toISOString(),
        cost: 0,
        metadata: { event_type: tp.event_type, seq: idx + 1 },
      }));

      const conversionTime = new Date(baseTime.getTime() + 3600000).toISOString();

      const journey = await apiRequest<{ journey_id: string; touchpoints: { id: string; channel: string; timestamp: string; metadata: { seq?: number } }[] }>(
        '/attribution/journeys',
        {
          method: 'POST',
          body: JSON.stringify({
            user_id: userId,
            touchpoints,
            conversion: { timestamp: conversionTime, value: conversionValue, currency: 'USD' },
          }),
        }
      );

      const calc = await apiRequest<{ journey_id: string; models: Record<string, Record<string, number>> }>(
        `/attribution/journeys/${journey.journey_id}/compute`,
        {
          method: 'POST',
          body: JSON.stringify({ models: ['first_touch', 'last_touch', 'linear', 'time_decay', 'shapley'] }),
        }
      );

      const journeySteps = journey.touchpoints
        .sort((a, b) => (a.metadata.seq || 0) - (b.metadata.seq || 0))
        .map((tp, idx) => ({
          seq: idx + 1,
          channel: tp.channel,
          event_type: 'click',
          event_time: tp.timestamp,
          credits: calc.models['linear'],
        }));

      setAttribution({
        journey: journeySteps,
        conversion_value: conversionValue,
        models: calc.models,
        model_credits: calc.models,
        summary: `Journey ${journey.journey_id} analyzed across ${Object.keys(calc.models).length} models.`,
      });
    } catch (err) {
      console.error('归因分析失败:', err);
      alert('后端归因调用失败，已回退到模拟数据');
      loadMockData();
    } finally {
      setLoadingAttribution(false);
    }
  };

  const assessTraffic = async () => {
    setLoadingTraffic(true);
    try {
      const rawMetrics = {
        impressions: 12000,
        clicks: 300,
        conversions: 24,
        bounce_count: 90,
        total_dwell_sec: 4800,
        interaction_events: 2100,
        unique_users: 280,
        click_timestamps: [1, 2, 3, 4, 5],
        ip_distribution: { '192.168.1.1': 150 },
      };

      const score = await apiRequest<TrafficQuality>('/traffic/assess', {
        method: 'POST',
        body: JSON.stringify({
          campaign_id: selectedCampaignId,
          raw_metrics: rawMetrics,
        }),
      });
      setQuality(score);

      const alertsData = await apiRequest<FraudAlert[]>(`/traffic/alerts/${selectedCampaignId}`);
      setAlerts(alertsData);
    } catch (err) {
      console.error('流量评估失败:', err);
      alert('后端流量评估失败，已回退到模拟数据');
      setQuality(mockTrafficQuality as TrafficQuality);
      setAlerts(mockFraudAlerts as FraudAlert[]);
    } finally {
      setLoadingTraffic(false);
    }
  };

  const resolveAlert = async (alertId: string) => {
    try {
      await apiRequest(`/traffic/alerts/${alertId}/resolve`, { method: 'POST' });
      setAlerts((prev) => prev.map((a) => (a.id === alertId ? { ...a, status: 'resolved' } : a)));
    } catch (err) {
      console.error('解决告警失败:', err);
    }
  };

  return (
    <div className="space-y-4 pb-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-100">归因分析 & 流量质量</h1>
        <p className="text-muted mt-1">多触点归因模型对比与实时流量质量监测</p>
      </header>

      {/* 控制面板 */}
      <div className="card p-4 flex flex-col lg:flex-row items-end gap-4">
        <div className="flex-1">
          <label className="block text-xs text-muted mb-1.5">Campaign</label>
          <select
            value={selectedCampaignId}
            onChange={(e) => setSelectedCampaignId(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-accent"
          >
            {CAMPAIGNS.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex-1">
          <label className="block text-xs text-muted mb-1.5 flex items-center gap-1">
            <User size={12} />
            用户 ID
          </label>
          <input
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-accent"
          />
        </div>
        <button
          onClick={initSampleJourney}
          disabled={loadingAttribution}
          className="btn-primary flex items-center gap-2 text-sm disabled:opacity-60"
        >
          {loadingAttribution ? <RefreshCw size={14} className="animate-spin" /> : <TrendingUp size={14} />}
          初始化示例并计算归因
        </button>
        <button
          onClick={assessTraffic}
          disabled={loadingTraffic}
          className="btn-secondary flex items-center gap-2 text-sm disabled:opacity-60"
        >
          {loadingTraffic ? <RefreshCw size={14} className="animate-spin" /> : <Activity size={14} />}
          评估流量质量
        </button>
        <button onClick={loadMockData} className="btn-secondary text-sm">
          模拟数据
        </button>
      </div>

      <AttributionPanel
        attribution={attribution}
        activeModel={activeModel}
        onModelChange={setActiveModel}
      />

      <TrafficPanel quality={quality} alerts={alerts} onResolve={resolveAlert} />
    </div>
  );
}

export default AttributionTraffic;
