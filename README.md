# AI Agent Chatbot MVP

一个可本地运行的全栈 AI Chatbot MVP，包含 FastAPI 后端、React + Vite + TypeScript + Tailwind CSS 前端、SQLite 持久化、会话管理、消息管理、Mock LLM、工具调用和统一 API 契约。

项目默认使用 Mock 模式，无需任何真实 API Key，也能完整演示聊天、会话、上下文、时间工具、计算工具、待办工具和前端工具调用展示。现在也支持在页面上切换到 DeepSeek / OpenAI-compatible 真实 API 模式，用于普通聊天验证。

## 功能概览

- FastAPI 后端，统一 `/api/v1` API 前缀。
- React + Vite + TypeScript 前端。
- SQLite 本地持久化会话、消息、工具调用和待办。
- Mock LLM 默认启用，稳定支持工具调用演示。
- 运行时 LLM Provider 切换：`mock` / `openai`。
- OpenAI-compatible Provider 支持 DeepSeek 普通聊天。
- 统一响应格式：成功 `{ "data": ... }`，失败 `{ "error": { "code", "message", "details" } }`。

## 目录结构

```text
AI Agent Chatbot MVP/
├─ backend/
│  ├─ app/
│  │  ├─ agents/              # Agent 编排与上下文构建
│  │  ├─ api/v1/routes/       # /api/v1 路由
│  │  ├─ core/                # 配置、数据库、错误处理、Provider 状态
│  │  ├─ llm/                 # Mock 与 OpenAI-compatible Provider
│  │  ├─ models/              # SQLModel 数据模型
│  │  ├─ schemas/             # Pydantic API 契约
│  │  └─ tools/               # 工具白名单与执行器
│  ├─ tests/
│  ├─ .env.example
│  └─ requirements.txt
├─ frontend/
│  ├─ src/
│  │  ├─ components/
│  │  ├─ lib/api.ts
│  │  ├─ types/api.ts
│  │  └─ App.tsx
│  ├─ .env.example
│  └─ package.json
├─ docs/
├─ .env.example
└─ README.md
```

## Windows 启动后端

在项目根目录打开 PowerShell：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

后端启动后可访问：

- API 文档：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/api/v1/health

## Windows 启动前端

另开一个 PowerShell，回到项目根目录：

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

默认访问：http://localhost:5173

如果 Vite 提示端口被占用，以终端输出地址为准；如改前端端口，需要同步调整后端 `backend/.env` 中的 `CORS_ORIGINS`。

## 后端环境配置

配置文件只放在 `backend/.env`，不要把真实 `.env` 提交到 GitHub。

### Mock 模式

Mock 是默认推荐演示模式：

```env
LLM_PROVIDER=mock
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
```

特点：

- 无需 API Key。
- 可完整体验普通聊天、会话、上下文、时间工具、计算工具、待办工具和工具调用展示。
- 适合评审、笔试演示和离线开发。

### DeepSeek 真实模式

如需体验真实模型，在 `backend/.env` 中填写：

```env
LLM_PROVIDER=mock
OPENAI_API_KEY=your_deepseek_api_key
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
```

说明：

- `LLM_PROVIDER` 仍建议保持 `mock`，项目启动后在前端页面切换到“真实 API”。
- 真实 Key 只放在 `backend/.env`。
- 前端不输入、不保存、不传递任何 API Key。
- 不要提交 `backend/.env`。
- 真实 API 模式当前支持普通聊天。
- 工具调用推荐切回 Mock 模式完整演示。

## 如何切换 LLM 模式

启动前后端后，聊天页面顶部会显示当前模式：

- `Mock 模式`
- `真实 API`

操作方式：

1. 默认进入页面时显示 Mock。
2. 点击“真实 API”会调用 `POST /api/v1/llm/provider`。
3. 如果 `backend/.env` 未配置完整真实 API，页面会展示友好错误，并继续停留在 Mock。
4. 配置 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL` 后，重启后端，再点击“真实 API”。
5. 切换成功后，普通聊天走 DeepSeek / OpenAI-compatible API。
6. 点击“Mock 模式”可随时切回，时间、计算、待办工具调用继续可用。

Provider API：

```http
GET /api/v1/llm/provider
POST /api/v1/llm/provider
```

查询返回示例：

```json
{
  "data": {
    "provider": "mock",
    "available_providers": ["mock", "openai"],
    "openai_configured": false
  }
}
```

切换请求示例：

```json
{
  "provider": "openai"
}
```

## 主要 API

所有业务接口均使用 `/api/v1` 前缀。

| 方法 | 路径 | 用途 |
|---|---|---|
| `GET` | `/api/v1/health` | 健康检查 |
| `GET` | `/api/v1/llm/provider` | 获取当前 LLM Provider |
| `POST` | `/api/v1/llm/provider` | 切换当前 LLM Provider |
| `GET` | `/api/v1/sessions` | 获取会话列表 |
| `POST` | `/api/v1/sessions` | 创建会话 |
| `GET` | `/api/v1/sessions/{session_id}` | 获取会话详情 |
| `POST` | `/api/v1/sessions/{session_id}/messages` | 发送消息 |

成功响应：

```json
{"data": {}}
```

失败响应：

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "错误提示",
    "details": {}
  }
}
```

## Mock 工具调用示例

在 Mock 模式下可以输入：

```text
你好，介绍一下你自己
我这个项目叫 ToolMind Chatbot。
我刚刚说项目叫什么？
现在几点？
帮我算一下 128 * 36 + 520
帮我记一个待办：明天提交笔试项目
我有哪些待办？
```

当前工具：

- `get_current_time`：获取当前日期、时间、时区、星期。
- `calculator`：安全四则运算，不使用 `eval`。
- `todo_tool`：按会话创建和查询待办。

## 真实 API 模式支持范围

真实 API 模式使用 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL` 调用 OpenAI-compatible `/chat/completions` 接口。

当前支持：

- 普通聊天。
- 上下文消息传递。
- DeepSeek OpenAI-compatible API。
- 超时、HTTP 错误、空响应、非法响应的统一错误返回。

当前限制：

- 真实 API 模式暂不实现模型 tool calling。
- 时间、计算、待办工具请使用 Mock 模式演示。
- 切换状态保存在后端进程内存中，服务重启后会回到 `backend/.env` 中的 `LLM_PROVIDER`；如果未配置则为 `mock`。

## 安全说明

- API Key 只能放在 `backend/.env` 或真实密钥管理系统中。
- API Key 不进入前端代码、前端 `.env`、浏览器 localStorage 或请求体。
- 前端只切换 provider，不接触密钥。
- 不要提交 `.env` 到 GitHub；仓库只保留 `.env.example`。
- 后端错误响应不会返回 API Key。
- 后端不要在日志中打印 API Key。

## 测试与验证

后端：

```powershell
cd backend
.\.venv\Scripts\activate
pytest
```

前端：

```powershell
cd frontend
npm run build
```

推荐手动验证：

1. 不配置真实 API Key，启动项目。
2. 默认 Mock 模式可用。
3. 普通聊天可用。
4. 时间工具可用。
5. 计算工具可用。
6. 待办工具可用。
7. 前端显示当前模式为 Mock。
8. 点击真实 API，未配置 Key 时显示友好错误。
9. 配置 DeepSeek Key 后重启后端，切换真实 API。
10. 普通聊天走真实模型。
11. 切回 Mock 后，工具调用仍可用。

## 已知限制

- 真实 API 模式当前只保证普通聊天。
- Mock LLM 基于规则和关键词，不等同真实模型推理能力。
- 每轮最多一次工具调用，不支持并行或连续多工具编排。
- Todo 仅支持创建和查询。
- 未实现 SSE / WebSocket 流式输出。
- 未实现登录、多用户隔离、权限系统和生产级限流。
