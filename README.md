# AdPulse SDK Platform

一个面向发布商的广告 SDK 管理平台，支持 Mediation、In-App Bidding、流量质量分析和归因追踪。

---

## 快速启动

### 1. 后端
```bash
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt

# 启动（首次运行自动创建 SQLite 数据库 + 种子数据）
$env:SECRET_KEY="adpulse-local-dev-secret-key-min-32-characters"
$env:ENABLE_PUBLIC_REGISTRATION="true"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
首次启动自动写入演示数据：
- 演示用户：demo@adpulse.com（免密登录）
- 演示媒体主 Demo Media + 2 个应用、3 个广告位、3 个广告网络
- 演示事件数据（曝光、点击、转化）

### 2. 前端（静态构建）
```bash
cd frontend
npm install

$env:VITE_API_URL="http://localhost:8000"
npx vite build --minify false

python ..\working_server.py
```
浏览器打开 http://localhost:5173 即可使用。

### 3. SDK Demo
打开 sdk/demo.html 查看 SDK 集成效果。

---

## SDK 集成
```html
<script src="https://cdn.adpulse.com/sdk/adpulse.js"></script>
<script>AdPulse.init("PUBLISHER_KEY");</script>
<div data-adpulse data-slot="AD_UNIT_ID"></div>
<script>AdPulse.showAd("#container", { slot: "AD_UNIT_ID" });</script>
```
详见 sdk/README.md。

---

## 架构
```
用户浏览器 -> Web SDK -> Backend (FastAPI, :8000) -> SQLite
                                               -> Frontend (React, :5173)
```
SDK 请求路径：
- POST /v1/bid - 竞价
- POST /v1/events/* - 事件上报
- GET /v1/sdk/config/* - SDK 配置

---

## API 概览

### SDK 端接口 (/v1)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /v1/bid | In-App Bidding 竞价 |
| POST | /v1/events/impression | 曝光上报 |
| POST | /v1/events/click | 点击上报 |
| POST | /v1/events/conversion | 转化上报 |
| POST | /v1/events/batch | 批量事件上报 |
| GET | /v1/sdk/config/{id} | SDK 配置 |
| POST | /v1/attribution/match/{id} | 单个转化归因 |
| POST | /v1/attribution/match-all | 批量归因 |
| POST | /v1/attribution/create-and-match | 创建+归因 |
| POST | /v1/attribution/compare/{id} | 归因算法对比 |
| GET | /v1/attribution/report | 归因报告 |

### 管理端接口 (/api)
| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | /api/publishers | 媒体主 CRUD |
| GET/POST | /api/publishers/{id}/apps | 应用管理 |
| GET/POST | /api/ad-units | 广告位 CRUD |
| GET/POST | /api/ad-units/{id}/sources | Mediation 源配置 |
| PATCH | /api/ad-units/{id}/waterfall | Waterfall 排序 |
| PATCH | /api/ad-units/{id}/bidding-config | Bidding 配置 |
| PATCH/DELETE | /api/ad-units/sources/{id} | 广告源操作 |
| GET | /api/dashboard/summary | KPI 概览 |
| GET | /api/dashboard/trend | KPI 趋势 |
| GET | /api/report/summary | 报表导出 |
| POST | /api/traffic/assess/{id} | 流量质量评估 |
| GET | /api/traffic/ad-unit/{id}/trend | 质量趋势 |
| GET | /api/traffic/ad-unit/{id}/alerts | 质量告警 |
| GET/POST/DELETE | /api/auth/api-keys | API 密钥管理 |

所有接口返回格式：{code: 0, message: "success", data: ...}

---

## 目录结构
```
adpulse/
├── sdk/                    # 客户端 SDK
│   ├── adpulse.js          # Web SDK 核心
│   ├── pixel.js            # 追踪像素
│   ├── demo.html           # 集成演示
│   └── README.md           # SDK 文档
├── backend/app/
│   ├── api/                # FastAPI 路由
│   │   ├── publishers.py   # 媒体主 + 应用 CRUD
│   │   ├── ad_units.py     # 广告位 + Mediation
│   │   ├── events.py       # 事件上报
│   │   ├── bidding.py      # In-App Bidding
│   │   ├── sdk_config.py   # SDK 配置
│   │   ├── attribution.py  # 归因匹配
│   │   ├── dashboard.py    # KPI 看板
│   │   ├── traffic.py      # 流量质量分析
│   │   ├── report.py       # 报表
│   │   └── auth.py         # 认证 + API Key
│   ├── models/             # SQLAlchemy 模型
│   ├── services/           # 业务逻辑
│   ├── core/               # 配置/数据库/种子数据
│   └── main.py             # 入口
├── frontend/src/
│   ├── pages/              # 页面组件
│   ├── components/         # 通用组件
│   ├── stores/             # Zustand 状态管理
│   └── lib/                # API 客户端
├── working_server.py       # 前端静态文件服务器
├── docker-compose.yml
└── README.md
```

---

## 技术栈
| 层 | 技术 |
|----|------|
| 后端 | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async) |
| 数据库 | SQLite |
| 前端 | React 18, TypeScript, Vite |
| 样式 | Tailwind CSS + Recharts |
| SDK | 原生 JavaScript（零依赖） |

## 模型关系
```
Publisher -> App -> AdUnit -> AdSource -> AdNetwork
                   Mediation Config (Waterfall + Bidding)
ImpressionEvent / ClickEvent -> ConversionEvent -> InstallMatcher -> AttributionResult
```

## 认证说明
本地开发模式已绕过登录，所有页面无需登录即可访问。
后端自动返回 demo@adpulse.com 用户身份。
