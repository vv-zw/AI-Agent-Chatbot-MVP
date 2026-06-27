# AI Agent Chatbot MVP

一个可本地运行的全栈 AI Chatbot MVP，包含 FastAPI 后端、React + Vite + TypeScript + Tailwind CSS 前端、SQLite 持久化、会话管理、消息管理、Mock LLM、工具调用和统一 API 契约。

项目默认使用 Mock 模式，无需任何真实 API Key，也能完整演示聊天、会话、上下文、时间工具、计算工具、待办工具和前端工具调用展示。现在也支持在页面上切换到 DeepSeek / OpenAI-compatible 真实 API 模式，并可为每个会话选择不同的 Chatbot 助手角色。

## 功能概览

- FastAPI 后端，统一 `/api/v1` API 前缀。
- React + Vite + TypeScript 前端。
- SQLite 本地持久化会话、消息、工具调用和待办。
- Mock LLM 默认启用，稳定支持工具调用演示。
- 支持基于 SSE 的分段回复、工具阶段事件和前端增量展示，并保留普通发送 fallback。
- 运行时 LLM Provider 切换：`mock` / `openai`。
- OpenAI-compatible Provider 支持 DeepSeek 普通聊天。
- 会话级助手角色切换，预置通用、代码、写作、面试 4 个角色。
- 角色 system prompt 同时作用于 Mock 和真实 Provider 上下文。
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
│  │  ├─ services/            # 助手角色定义等业务服务
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

## Docker 一键启动

在项目根目录执行：

```bash
docker-compose up --build
```

默认使用 Mock 模式，无需真实 API Key，也不会读取或提交本地 `.env`。启动后访问：

- 前端：http://localhost:5173
- 后端 API 文档：http://localhost:8000/docs
- 后端健康检查：http://localhost:8000/api/v1/health

停止服务：

```bash
docker-compose down
```

后端 SQLite 数据默认持久化到 Docker volume `backend-data`。如需同时删除容器和该 volume：

```bash
docker-compose down -v
```

如需在容器中配置真实 DeepSeek / OpenAI-compatible API，可通过环境变量覆盖后端服务配置，例如：

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=your_deepseek_api_key
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
```

不要把真实 API Key 写入仓库文件。真实 API 模式当前适合普通聊天验证；工具调用演示仍推荐使用默认 Mock 模式。

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

## 助手角色切换

项目预置 4 个会话级角色：

| role_id | 角色 | 侧重点 |
|---|---|---|
| `general` | 通用助手 | 日常问答和任务处理 |
| `code` | 代码助手 | 代码解释、调试和工程建议 |
| `writing` | 写作助手 | 表达优化、结构整理和润色 |
| `interview` | 面试助手 | 面试题讲解、项目复盘和回答组织 |

每个角色都包含独立的 `system_prompt`。发送消息时，后端会读取当前会话的 `role_id`，将对应 system prompt 放在上下文首条：Mock 模式据此展示可识别的角色化回复，真实 Provider 则将该 system 消息随普通聊天上下文一并发送。

页面侧栏的“新会话助手”用于选择下一条新会话的角色；页头的“助手角色”展示当前会话角色。修改已有会话时，页面会提示推荐新建会话；确认继续后，会通过 `PATCH /api/v1/sessions/{session_id}/role` 保存，已有消息不会删除。

助手角色与 Provider 是两个独立维度：

- **LLM 模式**决定回复由 Mock 规则还是 DeepSeek / OpenAI-compatible 模型生成。
- **助手角色**决定当前会话采用哪一套 system prompt 和回答侧重点。

角色 API：

```http
GET /api/v1/roles
PATCH /api/v1/sessions/{session_id}/role
```

创建会话时可指定角色；省略后默认为 `general`：

```json
{
  "title": "代码讨论",
  "role_id": "code"
}
```

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
| `GET` | `/api/v1/roles` | 获取预置助手角色 |
| `GET` | `/api/v1/sessions` | 获取会话列表 |
| `POST` | `/api/v1/sessions` | 创建会话 |
| `GET` | `/api/v1/sessions/{session_id}` | 获取会话详情 |
| `PATCH` | `/api/v1/sessions/{session_id}/role` | 修改当前会话角色 |
| `POST` | `/api/v1/sessions/{session_id}/messages` | 普通发送消息（保留为 fallback） |
| `POST` | `/api/v1/sessions/{session_id}/messages/stream` | 发送消息并返回 SSE 事件流 |

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

## 流式输出

前端默认开启“流式输出”，发送后会立即显示用户消息，并逐段追加 Agent 回复。发送期间按钮、会话切换和角色切换会禁用；工具调用时展示“处理中 / 成功 / 失败”阶段，流结束后 assistant 消息变为完成状态。取消输入框下方的“流式输出已开启”复选框，即可改用原有普通接口作为 fallback。

流式接口使用 `POST /api/v1/sessions/{session_id}/messages/stream`。之所以采用 POST 而不是浏览器原生 `EventSource` 的 GET，是为了继续使用与普通发送相同的 JSON 请求体：

```json
{
  "content": "帮我计算 (8 + 4) / 3",
  "provider": "mock"
}
```

响应类型为 `text/event-stream`，事件按以下顺序出现：

| 事件 | 含义 |
|---|---|
| `user_message_saved` | 用户消息已保存，返回正式消息记录 |
| `tool_call_start` | 工具调用开始，包含 `status=pending` 的工具记录 |
| `tool_call_result` | 工具执行结束，包含结果或结构化错误 |
| `assistant_delta` | assistant 回复文本片段，前端直接追加 |
| `assistant_done` | 流正常结束，返回与普通接口一致的完整 `ChatResponse` |
| `error` | 流内错误，使用统一 `{ "error": { "code", "message", "details" } }` 契约 |

服务端保证每条流以 `assistant_done` 或 `error` 结束；前端也会把没有终止事件的连接识别为中断，解除发送状态并显示错误，避免界面卡死。工具调用、`tool_calls` 记录和 `role=tool` 消息仍由原 Agent 流程统一持久化。

当前实现优先保证 Mock 模式的可演示性：Mock 回复按固定长度切片并加入很短的片段间隔。真实 OpenAI-compatible 模式也可使用该接口，但当前是在完整模型响应返回后再分段下发，并非上游模型原生 token 流；后续可在不改变前端事件契约的前提下升级 Provider 原生流式调用。

## Mock 工具调用示例

在 Mock 模式下可以输入：

先在“助手角色”中分别选择代码、写作或面试助手，再发送同一句“请给我一些建议”，可观察回复中的“技术视角”“表达视角”或“面试视角”；通用助手保持普通 Mock 回复。

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


## 多工具编排

Mock 模式支持一次请求触发 0 个、1 个或多个工具。例如：

```text
现在几点？顺便帮我算一下 128 * 36 + 520
帮我记一个待办：明天提交笔试项目，然后告诉我现在几点
帮我记一个待办：提交 README，然后看看我有哪些待办
```

执行与错误处理策略：

- 工具按用户请求中的任务顺序串行执行；因此“创建待办 + 查询待办”会先创建，后查询。
- 每个工具使用独立参数，分别校验、执行并写入 `tool_calls`；每个结果都保存为一条 `role=tool` 消息。
- 某一步参数非法、执行失败或工具未注册时，该步记录为 `failed`，后续工具继续执行。
- 最终 assistant 回复会汇总所有成功和失败结果；前端按执行顺序展示带步骤序号的多张工具卡片。


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

后端自动化测试：

```powershell
cd backend
.\.venv\Scripts\activate
pytest
```

如果当前 PowerShell 未激活虚拟环境，也可以执行：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest --basetemp=.tmp/pytest
```

后端测试使用独立的内存 SQLite 测试库，并在每个测试前后清理数据，不会污染本地 `backend/chatbot.db`。测试默认强制使用 Mock Provider，不依赖 DeepSeek / OpenAI API Key。

Windows 环境下如系统临时目录权限受限，可显式执行 `python -m pytest --basetemp=.tmp/pytest`；仓库内 `backend/pytest.ini` 也已默认将 pytest 临时目录和缓存目录放到项目内 `.tmp/`。

当前自动化测试覆盖：


- `GET /api/v1/health`、会话创建、列表、详情、删除。
- Mock 普通消息、多轮上下文、空输入、超长输入、session 不存在。
- Provider 查询与切换、非法 provider、无 API Key 时 Mock 模式仍可用。
- 时间工具、计算工具、待办创建与查询。
- calculator 非法表达式、除零错误和结构化失败结果。
- 工具调用记录落库到 `tool_calls`，工具结果保存为 `role=tool` 消息。
- 消息发送响应包含前端展示工具调用所需的 `tool_calls` 信息。
- todo、消息和工具调用不跨 session 泄露。
- 旧 SQLite schema 迁移兼容性。
- 角色列表、默认/指定/非法角色、会话角色持久化和 Mock 角色差异。
- SSE 流式普通回复、工具阶段事件、统一错误事件，以及普通发送接口回归。

前端构建检查：

```powershell
cd frontend
npm run build
```

前端类型检查：

```powershell
cd frontend
npm run typecheck
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
12. 新建会话前选择不同助手角色，确认会话列表和页头显示正确。
13. 在 Mock 模式下用同一问题验证不同角色的回复侧重点。

## 已知限制

- 真实 API 模式当前只保证普通聊天。
- Mock LLM 基于规则和关键词，不等同真实模型推理能力。
- 多工具按顺序编排执行，暂不支持并行工具调用。
- Todo 仅支持创建和查询。
- 真实 Provider 的 SSE 当前是完整响应后的分段下发，尚未接入上游模型原生 token 流。
- 未实现登录、多用户隔离、权限系统和生产级限流。
