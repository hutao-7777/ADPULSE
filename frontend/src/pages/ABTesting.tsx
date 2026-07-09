import { useEffect, useState } from 'react';

import { apiRequest } from '../utils/api';
import TestDetail from '../components/abtesting/TestDetail';
import TestForm from '../components/abtesting/TestForm';
import TestList from '../components/abtesting/TestList';
import type { ABTest, AnomalyAlert, TestResults } from '../components/abtesting/types';

function ABTesting() {
  const [tests, setTests] = useState<ABTest[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [results, setResults] = useState<TestResults | null>(null);
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
          winner: null,
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
      const test = tests.find((t) => t.id === id);
      const control = analysis.control || {};
      const comparisons: any[] = analysis.comparisons || [];
      const startDate = test?.start_date ? new Date(test.start_date) : null;
      const daysRunning = startDate
        ? Math.max(1, Math.ceil((Date.now() - startDate.getTime()) / 86400000))
        : 0;

      const buildVariant = (name: string, data: any, isControl: boolean): any => ({
        name,
        traffic_pct: isControl ? 100 - comparisons.reduce((sum, _c) => sum + (data.traffic_pct || 0), 0) : data.traffic_pct || 0,
        impressions: data.n || 0,
        clicks: 0,
        conversions: 0,
        revenue: 0,
        ctr: 0,
        conversion_rate: data.mean || 0,
        roi: 0,
        lift_pct: isControl ? 0 : data.relative_lift_pct || 0,
        p_value: isControl ? 1 : data.p_value_ttest || 1,
        is_significant: isControl ? false : data.is_significant || false,
        sample_size_reached: (data.n || 0) >= (test?.min_sample_size || 0),
        confidence_interval: isControl ? [0, 0] : (data.confidence_interval_95 || [0, 0]),
        power: isControl ? 0 : data.power || 0,
      });

      const variants = [buildVariant(control.name || 'control', control, true)];
      comparisons.forEach((c: any) => {
        variants.push(buildVariant(c.variant_name, c, false));
      });

      setResults({
        test_info: {
          name: test?.name || '',
          status: test?.status || 'draft',
          metric_target: test?.metric_target || 'conversion_rate',
          start_date: test?.start_date || null,
          days_running: daysRunning,
        },
        variants,
        recommendation: analysis.recommendation || '持续观察实验数据，等待样本量达到统计要求后再做决策。',
      });
      setAnomaly(null);
    } catch (err) {
      console.error('获取测试详情失败:', err);
    } finally {
      setLoadingDetail(false);
    }
  };

  useEffect(() => {
    fetchTests();
  }, []);

  useEffect(() => {
    if (selectedId) fetchDetail(selectedId);
  }, [selectedId]);

  const handleStart = async () => {
    if (!selectedId) return;
    try {
      await apiRequest(`/abtests/${selectedId}/start`, { method: 'POST' });
      fetchTests();
      fetchDetail(selectedId);
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
      setAnomaly(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : '删除失败');
    }
  };

  return (
    <div className="h-[calc(100vh-48px)] flex flex-col">
      <header className="mb-4">
        <h1 className="text-2xl font-bold text-slate-100">A/B 测试</h1>
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
            anomaly={anomaly}
            loading={loadingDetail}
            onStart={handleStart}
            onStop={handleStop}
            onDelete={handleDelete}
            onRefresh={() => selectedId && fetchDetail(selectedId)}
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
