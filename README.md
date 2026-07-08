# AdPulse

AdPulse 是一个面向程序化广告（Programmatic Advertising）的全栈智能投放平台演示项目。它整合了 RTB 实时竞价模拟、AI Agent 出价决策、A/B 测试引擎、多触点归因分析与流量质量检测等核心模块，帮助广告主在统一视图中完成数据监控、实验设计与策略优化。

> 本项目为演示/学习用途，采用模拟数据与规则引擎，适合作为广告技术（AdTech）产品的原型基础。

---

## 核心功能

- **Dashboard 数据看板**：展示 KPI、RTB 竞价趋势、DSP 预算消耗、创意评分分布与 A/B 测试概览。
- **RTB 竞价引擎**：单次/批量拍卖模拟，支持 First Price / Second Price，实时展示竞价日志与 DSP 胜出情况。
- **AI Agent 决策循环（Agent Loop）**：可视化 ReAct 决策链路（Think → Act → Observe），支持策略配置与决策记忆。
- **A/B 测试引擎**：创建实验、自动分流、统计显著性检验（t 检验）、置信区间、功效分析与异常检测。
- **多触点归因分析**：支持 First Touch、Last Touch、Linear、Time Decay、Position Based（U-Shaped）、Shapley 近似 6 种归因模型。
- **流量质量检测**：基于 CTR/CVR、跳出率、停留时长、互动深度与异常规则，输出质量等级与作弊告警。
- **创意管理**：保留 Creative 模型用于 campaign 关联（已移除旧的图片 AI 评分模块）。

---

## 技术栈

### 后端
- Python 3.11+
- FastAPI + Pydantic v2
- SQLAlchemy 2.0（async）+ SQLite（aiosqlite）
- NumPy / SciPy（统计检验）
- pytest + pytest-asyncio + httpx（测试）

### 前端
- React 18 + TypeScript
- Vite
- Tailwind CSS
- React Router v6
- Recharts（图表）
- Lucide React（图标）

---

## 项目结构

```
adpulse/
├── backend/
│   ├── app/
│   │   ├── agent/            # ReAct 出价 Agent
│   │   ├── api/              # FastAPI 路由（abtest/agent/attribution/rtb/traffic）
│   │   ├── core/             # 配置、数据库、seed 数据
│   │   ├── models/           # SQLAlchemy 模型
│   │   ├── schemas/          # Pydantic Schema
│   │   └── services/         # 业务引擎（attribution/traffic/ab_test/rtb）
│   ├── tests/                # 集成测试
│   ├── requirements.txt
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── components/       # Layout 等通用组件
│   │   ├── pages/            # 页面（Dashboard/RTBEngine/ABTesting/AgentLoop/AttributionTraffic）
│   │   └── utils/            # API 请求与 mock 数据
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
└── README.md
```

---

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/hutao-7777/ADPULSE.git
cd ADPULSE
```

### 2. 启动后端

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

后端默认运行在：http://localhost:8000

首次启动会自动创建 SQLite 数据库并写入 seed 数据。

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在：http://localhost:5173

---

## 运行测试

```bash
cd backend
source venv/bin/activate      # Windows: venv\Scripts\activate
pytest tests/test_api.py -v
```

当前包含 6 个集成测试：
- 单次/批量 RTB 拍卖
- A/B 测试完整流程
- Agent Loop 决策链路
- 多触点归因流程
- 流量质量评估

---

## API 概览

| 模块 | 前缀 | 说明 |
|------|------|------|
| Dashboard | `/api/dashboard` | 聚合指标与趋势 |
| RTB | `/api/rtb` | 单次/批量拍卖、DSP 列表 |
| A/B Test | `/api/abtests` | 实验创建、启动、结果、异常检测 |
| Agent | `/api/agent` | Agent 运行、记忆、策略 |
| Attribution | `/api/attribution` | 触点旅程、归因计算、模型对比 |
| Traffic | `/api/traffic` | 流量质量评估、趋势、告警 |

详细接口定义请参考 `backend/app/api/` 与 `backend/app/schemas/`。

---

## 环境变量

后端通过 `.env` 文件配置，示例：

```env
DATABASE_URL=sqlite+aiosqlite:///./adpulse.db
PROJECT_NAME=AdPulse
VERSION=0.1.0
DEBUG=false
CORS_ORIGINS=["*"]
```

---

## 注意事项

- `.gitignore` 已排除 `venv/`、`node_modules/`、`.env`、`*.db`、`backend/uploads/` 等文件。
- 项目使用 CPU 版本的 PyTorch，无需 GPU。
- 部分页面包含模拟数据，用于未连接后端时展示 UI。

---

## License

MIT
