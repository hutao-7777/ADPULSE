# AdPulse

AdPulse 是一个程序化广告投放平台的全栈演示项目，包含 RTB 竞价模拟、AI Agent 出价决策、A/B 测试、多触点归因分析和流量质量检测等模块。

> 本项目仅用于学习和技术交流，数据均为模拟生成，不涉及真实投放。

---

## 功能模块

- **Dashboard**：核心指标看板，展示 KPI、预算消耗、竞价趋势、A/B 测试与流量质量概览。
- **RTB 竞价引擎**：模拟单次/批量广告拍卖，支持 First Price / Second Price 结算，展示竞价日志与胜出 DSP。
- **Agent Loop**：可视化 ReAct 决策链路（Think → Act → Observe），支持策略配置与记忆回看。
- **A/B 测试**：创建实验、自动分流、统计显著性检验、置信区间与异常检测。
- **多触点归因**：支持 First Touch、Last Touch、Linear、Time Decay、Position Based、Shapley 近似 6 种归因模型。
- **流量质量检测**：基于 CTR/CVR、跳出率、停留时长、互动深度等指标输出质量等级与作弊告警。

---

## 技术栈

### 后端
- Python 3.11+
- FastAPI + Pydantic v2
- SQLAlchemy 2.0（async）+ SQLite（aiosqlite）
- NumPy / SciPy
- pytest + pytest-asyncio + httpx

### 前端
- React 18 + TypeScript
- Vite
- Tailwind CSS
- React Router v6
- Recharts
- Lucide React

---

## 项目结构

```
adpulse/
├── backend/
│   ├── app/
│   │   ├── agent/            # ReAct 出价 Agent
│   │   ├── api/              # FastAPI 路由
│   │   ├── core/             # 配置、数据库、seed 数据
│   │   ├── models/           # SQLAlchemy 模型
│   │   ├── schemas/          # Pydantic Schema
│   │   └── services/         # 业务引擎
│   ├── tests/                # 集成测试
│   ├── requirements.txt
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── utils/
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

后端默认运行在 http://localhost:8000，首次启动会自动创建 SQLite 数据库并写入 seed 数据。

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 http://localhost:5173。

---

## 运行测试

```bash
cd backend
source venv/bin/activate      # Windows: venv\Scripts\activate
pytest tests/test_api.py -v
```

当前包含 6 个集成测试：RTB 单次/批量拍卖、A/B 测试流程、Agent Loop、归因流程、流量质量评估。

---

## API 概览

| 模块 | 前缀 | 说明 |
|------|------|------|
| Dashboard | `/api/dashboard` | 聚合指标与趋势 |
| RTB | `/api/rtb` | 拍卖、DSP 列表 |
| A/B Test | `/api/abtests` | 实验创建、结果、异常检测 |
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

## 说明

- `.gitignore` 已排除 `venv/`、`node_modules/`、`.env`、`*.db`、`backend/uploads/` 等。
- 部分页面在未连接后端时会使用 mock 数据展示 UI。
- 本项目仅供学习和技术交流使用。
