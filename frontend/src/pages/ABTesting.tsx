import { useEffect, useState } from 'react';

import { apiRequest } from '../utils/api';
import DataSourceBadge from '../components/DataSourceBadge';
import TestDetail from '../components/abtesting/TestDetail';
import TestForm from '../components/abtesting/TestForm';
import TestList from '../components/abtesting/TestList';
import type {
  ABTest,
  AnomalyAlert,
  TestResults,
  TrendData,
  VariantStat,
} from '../components/abtesting/types';

function ABTesting() {
  const [tests, setTests] = useState<ABTest[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [results, setResults] = useState<TestResults | null>(null);
  const [trendData, setTrendData] = useState<TrendData | null>(null);
  const [anomaly, setAnomaly] = useState<AnomalyAlert | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [showModal, setShowModal] = useState(false);

  const selectedTest = tests.find((t) => t.id === selectedId) || null;

  const fetchTests = async () => {
    setLoadingList(true);
    try {
      const data = await apiRequest<any[]>('/abtests');
      setTests(
        data.map((t) => ({
          ...t,
          metric_target: t.success_metric || 'conversion_rate',
          winner: t.winner_variant_id || null,
        }))
      );
      if (data.length > 0 && !selectedId) {
        setSelectedId(data[0].id);
      }
    } catch (err) {
      console.error('获取测试列表失败:', err);
    } finally {
      setLoadingList(false);
    }
  };

  const fetchDetail = async (id: string) => {
    setLoadingDetail(true);
    try {
      const analysis = await apiRequest<any>(`/abtests/${id}/analysis`);
      const allVariants: any[] = analysis.variants || [];

      const variantStats: VariantStat[] = allVariants.map((v: any) => ({
        name: v.name,
        traffic_pct: v.traffic_pct || 0,
        impressions: v.impressions || 0,
        clicks: v.clicks || 0,
        conversions: v.conversions || 0,
        revenue: v.revenue || 0,
        users: v.users || 0,
        ctr: v.ctr || 0,
        conversion_rate: v.conversion_rate || 0,
        roi: v.revenue && v.users ? v.revenue / v.users : 0,
        lift_pct: 0,
        p_value: 1,
        is_significant: false,
        sample_size_reached: false,
        confidence_interval: [0, 0],
        power: 0,
      }));

      const comparisons = (analysis.comparisons || []).map((c: any) => ({
        variant_name: c.variant_name,
        control_name: c.control_name,
        relative_lift_pct: c.relative_lift_pct || 0,
        is_significant: c.is_significant || false,
      }));

      // Merge lift/significance into variant stats
      variantStats.forEach((vs) => {
        const comp = comparisons.find((c: any) => c.variant_name === vs.name);
        if (comp) {
          vs.lift_pct = comp.relative_lift_pct;
          vs.is_significant = comp.is_significant;
        }
      });

      const test = tests.find((t) => t.id === id);
      const startDate = test?.start_date ? new Date(test.start_date) : null;
      const daysRunning = startDate
        ? Math.max(1, Math.ceil((Date.now() - startDate.getTime()) / 86400000))
        : 0;

      setResults({
        test_info: {
          name: test?.name || '',
          status: test?.status || 'draft',
          metric_target: test?.metric_target || 'conversion_rate',
          start_date: test?.start_date || null,
          days_running: daysRunning,
        },
        variants: variantStats,
        recommendation:
          comparisons.length > 0 && comparisons.some((c: any) => c.is_significant)
            ? `${comparisons.find((c: any) => c.is_significant)?.variant_name} 表现显著优于 Control，建议推广该变体。`
            : '各变体差异尚未达到统计显著，建议继续运行实验积累样本。',
      });

      if (comparisons.length > 0 && test?.status === 'running') {
        const sig = comparisons.filter((c: any) => c.is_significant);
        if (sig.length > 0) {
          setAnomaly({
            variant: sig[0].variant_name,
            metric: test.metric_target,
            current_value: sig[0].treatment_value || 0,
            expected_range: [0, sig[0].control_value || 0],
            severity: 'warning',
          });
        } else {
          setAnomaly(null);
        }
      } else {
        setAnomaly(null);
      }
    } catch (err) {
      console.error('获取测试详情失败:', err);
    } finally {
      setLoadingDetail(false);
    }
  };

  const fetchTrend = async (id: string) => {
    try {
      const data = await apiRequest<TrendData>(`/abtests/${id}/trend`);
      setTrendData(data);
    } catch (err) {
      console.error('获取趋势数据失败:', err);
      setTrendData(null);
    }
  };

  useEffect(() => {
    fetchTests();
  }, []);

  useEffect(() => {
    if (selectedId) {
      fetchDetail(selectedId);
      fetchTrend(selectedId);
    }
  }, [selectedId]);

  useEffect(() => {
    if (!selectedId) return;
    const interval = setInterval(() => {
      fetchDetail(selectedId);
      fetchTrend(selectedId);
    }, 30000);
    return () => clearInterval(interval);
  }, [selectedId]);

  const handleStart = async () => {
    if (!selectedId) return;
    try {
      await apiRequest(`/abtests/${selectedId}/start`, { method: 'POST' });
      fetchTests();
      fetchDetail(selectedId);
      fetchTrend(selectedId);
    } catch (err) {
      alert(err instanceof Error ? err.message : '启动失败');
    }
  };

  const handleStop = async () => {
    if (!selectedId) return;
    try {
      await apiRequest(`/abtests/${selectedId}/stop`, { method: 'POST' });
      fetchTests();
      fetchDetail(selectedId);
      fetchTrend(selectedId);
    } catch (err) {
      alert(err instanceof Error ? err.message : '停止失败');
    }
  };

  const handleDelete = async () => {
    if (!selectedId || !confirm('确定删除该测试？')) return;
    try {
      await apiRequest(`/abtests/${selectedId}`, { method: 'DELETE' });
      setSelectedId(null);
      fetchTests();
      setResults(null);
      setTrendData(null);
      setAnomaly(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : '删除失败');
    }
  };

  return (
    <div className="h-[calc(100vh-48px)] flex flex-col">
      <header className="mb-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-slate-100">A/B 测试</h1>
          <DataSourceBadge />
        </div>
        <p className="text-muted mt-1">创建实验、分析统计结果并做出数据驱动决策</p>
      </header>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-10 gap-4 min-h-0">
        <div className="lg:col-span-3 min-h-0">
          <TestList
            tests={tests}
            selectedId={selectedId}
            onSelect={setSelectedId}
            onNew={() => setShowModal(true)}
            loading={loadingList}
          />
        </div>
        <div className="lg:col-span-7 min-h-0 overflow-y-auto pr-1 pb-2">
          <TestDetail
            test={selectedTest}
            results={results}
            trendData={trendData}
            anomaly={anomaly}
            loading={loadingDetail}
            onStart={handleStart}
            onStop={handleStop}
            onDelete={handleDelete}
            onRefresh={() => {
              if (selectedId) {
                fetchDetail(selectedId);
                fetchTrend(selectedId);
              }
            }}
          />
        </div>
      </div>

      <TestForm
        open={showModal}
        onClose={() => setShowModal(false)}
        onCreated={() => {
          fetchTests();
        }}
      />
    </div>
  );
}

export default ABTesting;
