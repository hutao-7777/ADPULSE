import { useEffect, useState } from 'react';
import { AlertCircle, X } from 'lucide-react';

import { apiRequest } from '../utils/api';
import AgentConfig from '../components/agent/AgentConfig';
import AgentStep from '../components/agent/AgentStep';
import AgentLog from '../components/agent/AgentLog';
import AgentStatusPanel from '../components/agent/AgentStatusPanel';
import type {
  AgentIteration,
  AgentMemoryEntry,
  AgentMemoryResponse,
  AgentRunResponse,
  AgentStatus,
  DSPStatus,
  PerformanceMetrics,
  StepDurations,
} from '../components/agent/types';

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

  useEffect(() => {
    if (!selectedCampaign) return;
    fetchStatusAndMemory(selectedCampaign);
  }, [selectedCampaign]);

  const fetchStatusAndMemory = async (campaignId: string) => {
    try {
      const [s, m] = await Promise.all([
        apiRequest<AgentStatus>(`/agent-sim/${campaignId}/status`),
        apiRequest<AgentMemoryResponse>(`/agent-sim/${campaignId}/memory`),
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
      await apiRequest(`/agent-sim/${selectedCampaign}/strategy`, {
        method: 'POST',
        body: JSON.stringify(strategy),
      });

      const runRes = await apiRequest<AgentRunResponse>(`/agent-sim/${selectedCampaign}/run`, {
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

      <AgentConfig
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
          <AgentStep
            iterations={iterations}
            expandedMap={expandedThink}
            onToggleExpand={toggleThink}
            durations={durations}
          />
        </div>
        <div className="lg:col-span-3">
          <AgentLog memory={memory} expandedMap={expandedMemory} onToggle={toggleMemory} />
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
