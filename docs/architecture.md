# AdPulse 架构设计文档

> 版本：v1.0.0
> 状态：面向学习与技术交流的全栈程序化广告演示平台

## 1. 设计目标

AdPulse 是一个面向 DSP/SSP 生态的实时竞价（RTB）广告投放平台，核心能力包括：

- **RTB 引擎**：在 100ms（p99）内完成竞价决策，支持 Second-Price Auction（Vickrey）。
- **A/B 实验引擎**：一致性哈希分流、双样本 t 检验 / Mann-Whitney U 检验、power analysis、MDE 计算。
- **归因引擎**：有序 touchpoint 记录、可配置归因窗口、Monte Carlo Shapley Value 近似。
- **AI Bidding Agent**：基于 ReAct 循环的确定性工具调用演示（当前未调用真实 LLM API）。
- **安全与治理**：JWT Access/Refresh、RBAC、API Key、CORS 白名单、审计日志（当前未启用认证中间件）。

---

## 2. 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python 3.11+、FastAPI、Pydantic v2 |
| 数据库 | SQLite（aiosqlite）+ SQLAlchemy 2.0 async；无 Alembic |
| 统计/ML | SciPy、NumPy、statsmodels |
| LLM | OpenAI / Anthropic Claude（当前为确定性 ReAct 模拟，未调用真实 API）|
| 测试 | pytest、pytest-asyncio、httpx |
| 前端 | React 18、TypeScript、Vite |
| 部署 | Docker（multi-stage）、docker-compose、GitHub Actions |
| 代码质量 | black、isort、flake8、mypy、pre-commit |

---

## 3. 系统架构概览

```mermaid
flowchart TB
    subgraph Client["客户端层"]
        WEB["React 18 SPA"]
        DSP["DSP / API 接入"]
    end

    subgraph Gateway["网关层"]
        NGINX["Nginx（反向代理 / 静态资源）"]
    end

    subgraph App["应用层"]
        API["FastAPI Application"]
        AUTH["Auth & RBAC"]
        RTB["RTB Engine"]
        AB["A/B Test Engine"]
        ATT["Attribution Engine"]
        AGENT["Bidding Agent"]
    end

    subgraph Data["数据层"]
        DB[("SQLite")]
    end

    subgraph Ext["外部依赖"]
        LLM["OpenAI / Claude API"]
    end

    WEB -->|HTTPS| NGINX
    DSP -->|HTTPS / API Key| NGINX
    NGINX -->|/api/*| API
    API --> AUTH
    API --> RTB
    API --> AB
    API --> ATT
    API --> AGENT
    RTB --> DB
    AB --> DB
    ATT --> DB
    AGENT --> DB
    AGENT --> LLM
```

---

## 4. 领域模型与 ER 图

### 4.1 核心实体

| 实体 | 说明 |
|------|------|
| `users` | 平台用户，支持 RBAC 角色 |
| `roles` / `permissions` / `user_permissions` | RBAC 角色与权限 |
| `api_keys` | DSP 接入用的 API Key |
| `refresh_tokens` | JWT Refresh Token 持久化 |
| `advertisers` | 广告主 |
| `campaigns` | 广告投放计划 |
| `creatives` | 创意素材 |
| `audience_segments` | 人群包 |
| `bidding_strategies` | 出价策略 |
| `auction_requests` | 竞价请求日志 |
| `auction_bids` | 出价记录 |
| `auction_wins` | 竞价胜出记录 |
| `experiments` | A/B 实验 |
| `variants` | 实验变体 |
| `assignments` | 用户-实验分配 |
| `experiment_metrics` | 实验指标采集 |
| `conversions` | 转化事件 |
| `touchpoints` | 归因 touchpoint（有序） |
| `attribution_results` | 归因结果 |
| `agent_configs` | Agent 配置 |
| `agent_memories` | Agent 记忆 |
| `agent_runs` | Agent 执行记录 |

### 4.2 ER 图

```mermaid
erDiagram
    USERS ||--o{ API_KEYS : owns
    USERS ||--o{ REFRESH_TOKENS : has
    USERS }o--o{ ROLES : belongs_to
    ROLES }o--o{ PERMISSIONS : grants
    USERS }o--o{ PERMISSIONS : directly_grants

    ADVERTISERS ||--o{ CAMPAIGNS : runs
    USERS ||--o{ ADVERTISERS : manages
    CAMPAIGNS ||--o{ CREATIVES : contains
    CAMPAIGNS ||--|| BIDDING_STRATEGIES : uses
    CAMPAIGNS }o--o{ AUDIENCE_SEGMENTS : targets

    CAMPAIGNS ||--o{ AUCTION_REQUESTS : receives
    AUCTION_REQUESTS ||--o{ AUCTION_BIDS : generates
    AUCTION_REQUESTS ||--o{ AUCTION_WINS : results_in
    CREATIVES ||--o{ AUCTION_BIDS : participates

    CAMPAIGNS ||--o{ EXPERIMENTS : tests
    EXPERIMENTS ||--o{ VARIANTS : has
    USERS ||--o{ ASSIGNMENTS : assigned_to
    EXPERIMENTS ||--o{ ASSIGNMENTS : assigns
    VARIANTS ||--o{ EXPERIMENT_METRICS : collects

    USERS ||--o{ CONVERSIONS : converts
    USERS ||--o{ TOUCHPOINTS : has
    CAMPAIGNS ||--o{ TOUCHPOINTS : generates
    CONVERSIONS ||--o{ ATTRIBUTION_RESULTS : attributed_by

    USERS ||--o{ AGENT_CONFIGS : configures
    USERS ||--o{ AGENT_RUNS : executes
    AGENT_RUNS ||--o{ AGENT_MEMORIES : recalls
```

---

## 5. 核心数据流

### 5.1 RTB 竞价流（目标 p99 < 100ms）

```mermaid
sequenceDiagram
    participant SSP as SSP / Bid Request
    participant NG as Nginx
    participant API as FastAPI
    participant Auth as API Key Auth
    participant RTB as RTB Engine
    participant DB as SQLite

    SSP->>NG: POST /api/rtb/auction
    NG->>API: proxy
    API->>Auth: validate API key
    Auth-->>API: ok
    API->>DB: fetch active campaigns / metadata
    DB-->>API: campaigns
    API->>RTB: filter & score
    RTB->>DB: get pacing/budget
    RTB->>RTB: Vickrey auction
    RTB-->>API: winner + second price
    API-->>NG: 200 bid response
    NG-->>SSP: bid response
```

**关键设计点**：

- 竞价相关元数据直接从 SQLite 读取。
- 预算与频次控制在服务内计算，当前参考实现未引入 Redis 分布式锁；后续如需水平扩展可引入缓存与分布式锁。
- 竞价结果同步写入 SQLite。
- Second-Price Auction：winner pays `max(second_highest_bid, reserve_price)`。

### 5.2 A/B 实验分流流

```mermaid
sequenceDiagram
    participant U as User
    participant API as FastAPI
    participant AB as A/B Engine
    participant DB as SQLite

    U->>API: request with user_id + experiment_id
    API->>AB: assign(user_id, experiment_id)
    AB->>AB: hash(user_id + experiment_id) % 100
    AB->>DB: check existing assignment
    alt not assigned
        AB->>AB: map bucket -> variant
        AB->>DB: persist assignment
    end
    AB-->>API: variant
    API-->>U: experience
```

### 5.3 归因引擎流

```mermaid
sequenceDiagram
    participant U as User
    participant API as FastAPI
    participant ATT as Attribution Engine
    participant DB as SQLite

    U->>API: conversion event
    API->>DB: insert conversion
    API->>ATT: attribute(user_id, conversion_id, window_config)
    ATT->>DB: fetch ordered touchpoints
    ATT->>ATT: filter by click_window / view_window
    ATT->>ATT: Monte Carlo Shapley (n=10000)
    ATT->>DB: insert attribution_results
    ATT-->>API: attribution breakdown
```

### 5.4 AI Bidding Agent 流

```mermaid
sequenceDiagram
    participant U as Operator
    participant API as FastAPI
    participant AG as Agent
    participant Mem as Memory Store
    participant LLM as OpenAI / Claude
    participant RTB as RTB Engine
    participant DB as SQLite

    U->>API: run agent
    API->>AG: execute(goal)
    AG->>Mem: search relevant memories
    Mem-->>AG: context
    AG->>LLM: function calling request
    loop ReAct Loop
        LLM-->>AG: tool_call
        AG->>RTB: tool: get_market_data / place_bid
        RTB-->>AG: observation
        AG->>Mem: store step
        AG->>LLM: next function call
    end
    AG->>DB: persist agent_runs
    AG-->>API: structured steps
```

---

## 6. 认证授权架构

### 6.1 JWT 双令牌

```mermaid
flowchart LR
    LOGIN["POST /auth/login"] -->|credentials| AUTH["Auth Service"]
    AUTH -->|issue| ACCESS["Access Token<br/>TTL: 15 min"]
    AUTH -->|issue| REFRESH["Refresh Token<br/>TTL: 7 days<br/>stored in DB"]
    ACCESS -->|Authorization: Bearer| API["Protected API"]
    REFRESH -->|POST /auth/refresh| AUTH
```

### 6.2 RBAC 模型

| 角色 | 权限示例 |
|------|----------|
| `admin` | 用户管理、全局配置、所有资源读写 |
| `advertiser` | 管理自有 campaign、creative、查看报表 |
| `viewer` | 只读查看 dashboard、报表 |

权限在数据库中以 `permissions.code` 形式存储（如 `campaign:read`、`campaign:write`），通过依赖注入在每个端点校验。

### 6.3 API Key

- `api_keys` 表存储 `key_hash`、`prefix`、`scopes`、`rate_limit`。
- RTB 接入端点强制 API Key 认证。
- Key 只在创建时明文返回一次。

### 6.4 CORS

- 配置文件/环境变量维护白名单列表。
- 开发环境可配置为 `allow_origins=["*"]`，生产环境建议仅开放指定域名。

---

## 7. 数据库与迁移

- **数据库**：SQLite，通过 `aiosqlite` 由 SQLAlchemy 2.0 async 访问。
- **ORM**：SQLAlchemy 2.0，使用 `Mapped` / `mapped_column` 类型注解。
- **建表**：应用启动时调用 `Base.metadata.create_all()` 自动建表；当前不使用 Alembic。
- **主键**：全部使用 `uuid.UUID`，`default=uuid.uuid4`。
- **时间戳**：统一使用 `datetime.utcnow`。

---

## 8. 缓存与并发

当前参考实现为单节点 SQLite 架构，未引入 Redis。所有读写直接访问 SQLite，状态由单进程事件循环内的 async/await 调度。后续如需水平扩展或降低 RTB 延迟，可引入：

- Redis 缓存活动 campaign 元数据；
- Redis 分布式锁进行预算扣减；
- Redis 进行实验分配缓存与 API Key 速率限制。

---

## 9. 部署架构

> **注意**：当前参考实现为单节点 SQLite 架构，仅用于演示与学习。后续如需生产级扩展，可引入 PostgreSQL、Redis、pgvector 等组件。

```mermaid
flowchart TB
    subgraph Infra["Docker Compose"]
        NG["Nginx"]
        BE["adpulse-backend<br/>FastAPI"]
        FE["adpulse-frontend<br/>React SPA"]
    end

    USER["用户"] --> NG
    DSP["DSP"] --> NG
    NG --> BE
    NG --> FE
    BE --> DB["SQLite（容器内或挂载卷）"]
```

### 9.1 容器清单

| 服务 | 镜像 | 说明 |
|------|------|------|
| `backend` | 多阶段 Dockerfile | FastAPI 后端 |
| `frontend` | 多阶段 Dockerfile | React SPA（Nginx 提供静态资源）|

> 当前 `docker-compose.yml` 仅包含 `backend` 与 `frontend` 两个服务；本地开发时 Vite 开发服务器代理 `/api` 到后端，生产部署可再前置独立 Nginx 做统一入口。

### 9.2 CI/CD

- GitHub Actions 工作流：lint（black/isort/flake8/mypy）、test（pytest）、build image。
- 合并前必须全部通过。
- 多阶段 Dockerfile 减小最终镜像体积。

---

## 10. 关键算法说明

### 10.1 Second-Price Auction

```
winner = argmax(bids)
second_price = max(second_highest_bid, reserve_price)
winner_pays = second_price
```

- 若最高出价低于 reserve price，则无胜出者。
- 所有价格以 per-impression 存储，CPM 展示时乘以 1000。

### 10.2 A/B 测试统计

- **分流**：`bucket = hash(user_id + experiment_id) % 100`，保证同一用户始终落入同一桶。
- **检验**：双样本 t 检验（均值差异）、Mann-Whitney U 检验（非参数）。
- **输出**：p-value、置信区间、power、MDE。
- **样本量**：基于目标 power / significance / MDE 进行 power analysis。

### 10.3 Shapley Value 近似

- 对每次转化，收集窗口期内的有序 touchpoint 序列。
- 使用 Monte Carlo 排列采样 `n=10000` 次估计 Shapley Value。
- 结果按 campaign / creative 聚合。

---

## 11. 非功能需求

| 指标 | 目标 |
|------|------|
| RTB p99 延迟 | < 100ms |
| 核心模块测试覆盖率 | ≥ 85% |
| 数据库迁移 | 当前使用 `Base.metadata.create_all`，后续可迁移至 Alembic |
| 认证端点 | JWT + RBAC + API Key 已建模，当前未强制启用 |
| CORS | 通过环境变量配置白名单 |

---

## 12. 环境变量（摘要）

详见项目根目录 `.env.example`，主要包含：

- `DATABASE_URL`（SQLite 路径，如 `sqlite+aiosqlite:///./adpulse.db`）
- `SECRET_KEY`、`ALGORITHM`、`ACCESS_TOKEN_EXPIRE_MINUTES`、`REFRESH_TOKEN_EXPIRE_DAYS`
- `CORS_ORIGINS`（逗号分隔）
- `ENABLE_PUBLIC_REGISTRATION`
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`（可选，当前未调用真实 LLM）
- `LOG_LEVEL`

---

## 13. 目录结构（目标）

```
adpulse/
├── docs/
│   └── architecture.md
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── security.py
│   │   │   ├── exceptions.py
│   │   │   └── response.py
│   │   ├── models/
│   │   │   └── __init__.py
│   │   ├── schemas/
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── rtb.py
│   │   │   ├── abtest.py
│   │   │   ├── attribution.py
│   │   │   ├── agent.py
│   │   │   └── dashboard.py
│   │   └── services/
│   │       ├── rtb_engine.py
│   │       ├── ab_test_engine.py
│   │       ├── attribution_engine.py
│   │       ├── bidding_agent.py
│   │       └── auth_service.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── unit/
│   │   ├── integration/
│   │   └── perf/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── features/
│   │   │   ├── auth/
│   │   │   ├── rtb/
│   │   │   ├── abtest/
│   │   │   ├── attribution/
│   │   │   └── agent/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── stores/
│   │   ├── utils/
│   │   └── App.tsx
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .github/
│   └── workflows/
│       └── ci.yml
├── .env.example
├── README.md
└── AGENTS.md
```

---

## 14. 变更日志

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-07-09 | 1.0.0 | 初始架构设计；当前参考实现简化为 SQLite-only，移除 Redis、PostgreSQL、pgvector 与 Alembic |
