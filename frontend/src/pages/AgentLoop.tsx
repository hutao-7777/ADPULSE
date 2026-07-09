import { useEffect, useState } from 'react';
import { AlertCircle, X } from 'lucide-react';

import { apiRequest } from '../utils/api';
import AgentConfig from '../components/agent/AgentConfig';
import AgentStep from '../components/agent/AgentStep';
import AgentLog from '../components/agent/AgentLog';
import AgentStatusPanel from '../components/agent/AgentStatusPanel';
import type {
  AgentConfigCreate,
  AgentConfigResponse,
  AgentIteration,
  AgentMemoryEntry,
  AgentRunApiResponse,
  AgentRunApiStep,
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

  const buildGoal = (campaign: string, cfg: typeof strategy) =>
    `Optimize bidding strategy for campaign "${campaign}". Target CPA: ${cfg.target_cpa}, max CPM: ${cfg.max_cpm}, daily budget: ${cfg.daily_budget}.`;

  const metricsFromOutput = (output: Record<string, unknown> | undefined): PerformanceMetrics => {
    const o = output || {};
    const impressions = Number(o.impressions ?? 0);
    const clicks = Number(o.clicks ?? 0);
    const spend = Number(o.spend ?? 0);
    const revenue = Number(o.revenue ?? 0);
    return {
      impressions,
      clicks,
      ctr: clicks > 0 && impressions > 0 ? clicks / impressions : Number(o.ctr ?? 0),
      spend,
      revenue,
      roi: Number(o.roi ?? 0),
      spend_ratio: Number(o.spend_ratio ?? 0),
    };
  };

  const mapRunResponse = (
    run: AgentRunApiResponse,
    campaign: string,
    cfg: typeof strategy
  ): {
    iterations: AgentIteration[];
    memory: AgentMemoryEntry[];
    metricsBefore: PerformanceMetrics;
    metricsAfter: PerformanceMetrics;
    status: AgentStatus;
  } => {
    const steps = run.steps || [];
    const iterations: AgentIteration[] = steps.map((s: AgentRunApiStep, idx: number) => {
      const tool = s.tool || 'maintain_strategy';
      const input = s.input || {};
      const output = s.output || {};
      const isLast = idx === steps.length - 1;
      const perf = metricsFromOutput(output);

      return {
        iteration: s.step,
        thought: {
          analysis:
            s.thought || `第 ${s.step} 步：Agent 正在分析当前市场与投放数据。`,
          data: {
            performance: perf,
            benchmark: {
              avg_cpm: Number(output.avg_cpm ?? 0),
              avg_ctr: Number(output.avg_ctr ?? 0),
              competition_level: 'medium',
            },
            derived: {
              win_rate: Number(output.win_rate ?? 0),
              avg_winning_cpm: Number(output.avg_cpm ?? 0),
              auction_count: Number(output.auction_count ?? 0),
            },
          },
        },
        action: {
          action: tool,
          parameters: input,
          reasoning: isLast
            ? `最终结论：${run.final_output || '完成决策循环'}`
            : `调用工具 "${tool}" 调整投放策略。`,
        },
        observation: {
          observation:
            Object.keys(output).length > 0
              ? `${tool} 返回结果：${JSON.stringify(output)}`
              : isLast
              ? run.final_output || '决策循环结束'
              : `观察 "${tool}" 执行后的市场反馈。`,
          expected_vs_actual: {},
          learned: run.final_output || '持续收集数据并优化出价策略。',
        },
      };
    });

    const memory: AgentMemoryEntry[] = steps.map((s: AgentRunApiStep) => ({
      timestamp: new Date().toISOString(),
      action: s.tool || 'maintain_strategy',
      parameters: s.input || {},
      result: s.output || {},
      expected_vs_actual: {},
      learned: run.final_output || '',
    }));

    const metricsBefore = metricsFromOutput(steps[0]?.output);
    const metricsAfter = metricsFromOutput(steps[steps.length - 1]?.output);

    const agentStatus: AgentStatus = {
      campaign_id: campaign,
      strategy: cfg,
      memory_size: memory.length,
      current_state: run.final_output ? 'completed' : 'running',
      last_action: steps[steps.length - 1]?.tool || null,
    };

    return { iterations, memory, metricsBefore, metricsAfter, status: agentStatus };
  };

  const handleRun = async () => {
    if (!selectedCampaign) return;
    setRunning(true);
    setError(null);
    setIterations([]);
    setExpandedThink({});
    setMetricsBefore(null);
    setMetricsAfter(null);
    setMemory([]);

    const start = performance.now();
    try {
      const goal = buildGoal(selectedCampaign, strategy);
      const configPayload: AgentConfigCreate = {
        name: selectedCampaign,
        goal,
        llm_provider: 'openai',
        llm_model: 'gpt-4o-mini',
        max_steps: loopCount,
      };

      const config = await apiRequest<AgentConfigResponse>('/agent/configs', {
        method: 'POST',
        body: JSON.stringify(configPayload),
      });

      const runRes = await apiRequest<AgentRunApiResponse>(`/agent/${config.id}/run`, {
        method: 'POST',
        body: JSON.stringify({ goal, max_steps: loopCount }),
      });

      const end = performance.now();
      const totalMs = Math.max(1, end - start);
      const stepMs = Math.round(totalMs / Math.max(1, runRes.steps.length * 3));
      setDurations({
        think: Math.round(stepMs * 1.2),
        act: Math.round(stepMs * 0.8),
        observe: Math.round(stepMs * 1.0),
      });

      const mapped = mapRunResponse(runRes, selectedCampaign, strategy);
      setIterations(mapped.iterations);
      setMemory(mapped.memory);
      setMetricsBefore(mapped.metricsBefore);
      setMetricsAfter(mapped.metricsAfter);
      setStatus(mapped.status);
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
