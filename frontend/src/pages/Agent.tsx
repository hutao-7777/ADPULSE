function Agent() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-100">智能 Agent</h1>
        <p className="text-muted mt-1">可视化展示出价 Agent 的 ReAct 决策链路</p>
      </header>

      <div className="card p-6 min-h-[500px] flex items-center justify-center">
        <p className="text-muted">Agent 推理可视化将在这里展示</p>
      </div>
    </div>
  );
}

export default Agent;
