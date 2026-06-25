# AI Agent Chatbot MVP

## 1. 项目简介

AI Agent Chatbot MVP 是一个可本地运行的全栈 AI Chatbot 笔试项目，支持基础聊天、多轮上下文、会话管理、SQLite 持久化、后端工具调用和前端工具调用展示。

项目默认使用确定性的 Mock LLM，因此没有真实 API Key 也能演示核心流程。工具不是由用户点击按钮直接触发，而是由 Mock LLM 根据输入自动判断，再由后端白名单执行器校验、执行并保存结果。会话、消息、工具调用记录和待办事项均持久化到 SQLite。

> 当前真实可用的 LLM Provider 只有 `mock`。项目保留了 OpenAI-compatible 环境变量和 Provider 抽象，但尚未实现真实模型 HTTP 调用。

## 2. 功能说明

当前已实现：

- 基础聊天与 Mock 助手回复。
- 会话创建、列表、切换和详情加载。
- 当前会话内的多轮上下文；Mock 模式可记住最近上下文中的项目名称。
- 用户、助手和内部 `tool` 消息持久化。
- 工具调用参数、结果、状态和错误持久化。
- 无需 API Key 的 Mock LLM。
- `get_current_time` 时间工具。
- `calculator` 安全四则运算工具。
- `todo_tool` 当前会话待办创建与查询。
- 前端工具调用卡片、加载状态和基础错误提示。
- 前后端空输入及最长 10,000 字符校验。
- 统一成功响应与结构化错误响应。
- pytest 后端测试，以及前端 typecheck、lint、build 脚本。

未实现能力见“已知限制”和“后续优化方向”。

## 3. 技术栈

| 层级 | 技术 |
|---|---|
| 前端 | React 19、Vite 6、TypeScript 5、Tailwind CSS 3 |
| 后端 | Python、FastAPI、Uvicorn、Pydantic / pydantic-settings |
| 数据 | SQLite、SQLModel（底层使用 SQLAlchemy） |
| 测试与校验 | pytest、FastAPI TestClient、TypeScript、ESLint、Vite build |
| LLM | Mock LLM；预留 OpenAI-compatible 配置与 Provider 接口 |

设置 `LLM_PROVIDER=openai` 当前不会发起真实模型请求：缺少 Key 时返回配置错误，提供 Key 后返回 Provider 尚未支持的错误。

## 4. 项目结构

```text
AI Agent Chatbot MVP/
├── backend/
│   ├── app/
│   │   ├── agents/              # Agent 编排与上下文构建
│   │   ├── api/v1/routes/       # /api/v1 路由
│   │   ├── core/                # 配置、数据库、异常处理
│   │   ├── llm/                 # LLM 抽象与 Mock Provider
│   │   ├── models/              # SQLModel 数据模型
│   │   ├── schemas/             # Pydantic API 契约
│   │   ├── tools/               # 工具白名单、参数模型和执行器
│   │   └── main.py              # FastAPI 入口
│   ├── scripts/smoke_check.py
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── lib/api.ts
│   │   ├── types/api.ts
│   │   └── App.tsx
│   ├── .env.example
│   ├── package.json
│   └── vite.config.ts
├── docs/
│   ├── architecture.md
│   └── tool-calling-design.md
├── .env.example                 # 前后端变量汇总示例
├── .gitignore
└── README.md
```

运行后生成的 `backend/data/chatbot.db`、本地 `.env`、虚拟环境、`node_modules` 和 `dist` 均已被 Git 忽略。

## 5. 本地启动

### 5.1 后端

建议从项目根目录进入 `backend` 后执行；默认数据库路径相对于该目录创建。

```bash
cd backend
python -m venv .venv
```

Windows 激活：

```bash
.venv\Scripts\activate
```

macOS / Linux 激活：

```bash
source .venv/bin/activate
```

安装依赖并复制配置：

```bash
pip install -r requirements.txt
```

Windows：

```bash
copy .env.example .env
```

macOS / Linux：

```bash
cp .env.example .env
```

启动：

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API 文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/api/v1/health`

### 5.2 前端

另开终端：

```bash
cd frontend
npm install
```

Windows：

```bash
copy .env.example .env
```

macOS / Linux：

```bash
cp .env.example .env
```

启动：

```bash
npm run dev
```

Vite 配置端口为 `5173`，通常访问 `http://localhost:5173`。若端口被占用，以终端输出为准，并同步调整后端 `CORS_ORIGINS`。

## 6. 环境变量

### 后端 `backend/.env.example`

| 变量 | 默认值 | 用途 |
|---|---|---|
| `APP_NAME` | `AI Agent Chatbot MVP` | FastAPI 应用名称和 OpenAPI 标题。 |
| `APP_ENV` | `development` | 环境标识，当前仅作为配置保留。 |
| `APP_HOST` | `127.0.0.1` | 主机配置；直接运行 Uvicorn 时以命令行参数为准。 |
| `APP_PORT` | `8000` | 端口配置；直接运行 Uvicorn 时以命令行参数为准。 |
| `DATABASE_URL` | `sqlite:///./data/chatbot.db` | 数据库连接地址。 |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | 允许的前端来源，逗号分隔。 |
| `MAX_CONTEXT_MESSAGES` | `20` | 每次读取的最近上下文消息数。 |
| `MAX_USER_MESSAGE_LENGTH` | `10000` | 用户消息最大字符数。 |
| `LLM_PROVIDER` | `mock` | LLM Provider；当前可运行值为 `mock`。 |
| `OPENAI_API_KEY` | 空 | OpenAI-compatible 预留 Key；Mock 不需要。 |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible 根地址预留配置。 |
| `OPENAI_MODEL` | `gpt-4.1-mini` | OpenAI-compatible 模型名预留配置。 |

### 前端 `frontend/.env.example`

| 变量 | 默认值 | 用途 |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | 后端 API 根地址，必须包含 `/api/v1`。 |

不要提交真实 `.env` 或 API Key。Key 只允许放在后端；前端不保存 LLM Key；Mock 模式不需要 Key。

## 7. Mock 模式

```env
LLM_PROVIDER=mock
OPENAI_API_KEY=
```

Mock 模式可演示新建/切换会话、普通聊天、多轮上下文、时间与计算工具、待办创建与查询、工具卡片和 SQLite 持久化。

推荐依次测试：

```text
你好，介绍一下你自己
我这个项目叫 ToolMind Chatbot。
我刚刚说项目叫什么？
现在几点？
帮我算一下 128 * 36 + 520
帮我记一个待办：明天提交笔试项目
我有哪些待办？
```

Mock Provider 基于规则和关键词，用于稳定验收，不等同于真实模型推理。

## 8. 工具调用说明

### `get_current_time`

- 用途：获取当前日期、时间、时区和星期。
- 触发示例：`现在几点？`、`今天日期是什么？`、`星期几？`
- 参数：可选 `timezone` 字符串，默认 `Asia/Shanghai`，应为 IANA 时区名。
- 返回：`date`、`time`、`timezone`、`weekday`。
- 失败：未知时区、类型错误或多余字段产生 `TOOL_ARGUMENT_INVALID`。

```json
{
  "date": "2026-06-26",
  "time": "14:30:00",
  "timezone": "Asia/Shanghai",
  "weekday": "星期五"
}
```

### `calculator`

- 用途：安全四则运算。
- 触发示例：`帮我算一下 128 * 36 + 520`
- 参数：必填 `expression` 字符串，长度 1～200。
- 返回：原表达式 `expression` 和字符串结果 `value`。
- 失败：非法字符、语法、缺少参数、类型错误和除零均产生结构化失败。

安全限制：不使用 `eval`；只允许数字、小数点、空格、括号和 `+ - * /`；不允许变量、函数、属性、下标、幂运算或任意代码。

```json
{
  "expression": "128 * 36 + 520",
  "value": "5128"
}
```

### `todo_tool`

- 用途：创建或查询当前会话的待办。
- 创建示例：`帮我记一个待办：明天提交笔试项目`
- 查询示例：`我有哪些待办？`

创建参数：

```json
{"action": "create", "title": "明天提交笔试项目"}
```

查询参数：

```json
{"action": "list"}
```

`create` 返回新待办的 `id`、`title`、`status`、`created_at`；`list` 返回当前会话的 `todos`。标题缺失、为空、类型错误、多余字段，或 `list` 携带标题时产生 `TOOL_ARGUMENT_INVALID`。

Todo 的 `session_id` 由后端注入，LLM 不能指定其他会话，因此不同会话不会互相读取待办。当前不支持完成、编辑或删除。

### 调用流程

```text
用户输入
→ Mock LLM 判断是否需要工具
→ 后端校验 tool name 白名单和 arguments
→ 创建 pending tool_calls
→ Tool Executor 执行
→ 更新为 succeeded / failed
→ 保存 role=tool 的 message
→ 工具结果进入上下文
→ Mock LLM 生成 assistant 回复
→ 保存 assistant message
→ 前端展示工具调用卡片
```

工具参数错误或未注册工具不会执行动态代码，也不会使接口崩溃；消息接口仍返回 `201`，失败信息位于 `data.tool_calls`。

## 9. API 说明

所有业务接口统一使用 `/api/v1` 前缀。

| 方法 | 路径 | 用途 |
|---|---|---|
| `GET` | `/api/v1/health` | 服务与 Provider 状态。 |
| `GET` | `/api/v1/sessions` | 按更新时间倒序获取会话。 |
| `POST` | `/api/v1/sessions` | 创建会话。 |
| `GET` | `/api/v1/sessions/{session_id}` | 获取会话、消息和工具调用。 |
| `POST` | `/api/v1/sessions/{session_id}/messages` | 发送消息并执行一轮 Agent。 |

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

### 健康检查

```http
GET /api/v1/health
```

```json
{"data": {"status": "ok", "provider": "mock"}}
```

### 创建会话

```http
POST /api/v1/sessions
Content-Type: application/json

{"title": "测试会话"}
```

`title` 可省略，默认 `New conversation`，最长 120。默认标题会在第一条消息后更新为消息前 40 个字符。成功状态为 `201`：

```json
{
  "data": {
    "id": "2ec9de57-2da2-41b0-929e-c28b760de7f2",
    "title": "测试会话",
    "created_at": "2026-06-26T06:00:00Z",
    "updated_at": "2026-06-26T06:00:00Z"
  }
}
```

`GET /api/v1/sessions` 的 `data` 是上述会话对象数组，按 `updated_at` 倒序排列。

### 获取会话详情

```http
GET /api/v1/sessions/{session_id}
```

```json
{
  "data": {
    "id": "2ec9de57-2da2-41b0-929e-c28b760de7f2",
    "title": "测试会话",
    "created_at": "2026-06-26T06:00:00Z",
    "updated_at": "2026-06-26T06:01:00Z",
    "messages": [],
    "tool_calls": []
  }
}
```

`messages` 和 `tool_calls` 均按创建时间正序返回。

### 发送消息

```http
POST /api/v1/sessions/{session_id}/messages
Content-Type: application/json

{"content": "帮我算一下 128 * 36 + 520"}
```

`content` 会去除首尾空白，不能为空，默认最长 10,000 字符。成功状态为 `201`：

```json
{
  "data": {
    "user_message": {
      "id": "...",
      "session_id": "...",
      "role": "user",
      "content": "帮我算一下 128 * 36 + 520",
      "created_at": "2026-06-26T06:01:00Z"
    },
    "assistant_message": {
      "id": "...",
      "session_id": "...",
      "role": "assistant",
      "content": "计算结果：128 * 36 + 520 = 5128",
      "created_at": "2026-06-26T06:01:00Z"
    },
    "tool_calls": [
      {
        "id": "...",
        "session_id": "...",
        "assistant_message_id": "...",
        "tool_message_id": "...",
        "tool_name": "calculator",
        "arguments": {"expression": "128 * 36 + 520"},
        "result": {"expression": "128 * 36 + 520", "value": "5128"},
        "status": "succeeded",
        "error_code": null,
        "error_message": null,
        "created_at": "2026-06-26T06:01:00Z",
        "completed_at": "2026-06-26T06:01:00Z"
      }
    ]
  }
}
```

会话不存在时返回 `SESSION_NOT_FOUND` 和包含 `session_id` 的 `details`。

## 10. 数据存储说明

选择 SQLite 是因为零外部服务配置、方便本地评审、启动成本低，并满足持久化要求。默认文件：

```text
backend/data/chatbot.db
```

| 表 | 用途 |
|---|---|
| `sessions` | 会话标题与时间。 |
| `messages` | `user`、`assistant`、`tool` 消息。 |
| `tool_calls` | 工具参数、结果、状态、错误和消息关联。 |
| `todos` | 按会话隔离的待办。 |

一个 session 有多条 message、tool_call 和 todo；tool_call 可关联最终 assistant message 与内部 tool message。启动时使用 SQLModel `create_all` 建表，并包含少量旧 SQLite 结构兼容逻辑；当前未使用 Alembic。

## 11. 多轮上下文策略

每次发送消息时，后端保存用户消息，读取当前会话最近 `MAX_CONTEXT_MESSAGES` 条消息，再恢复为时间正序并按 `user`、`assistant`、`tool` role 组织上下文。工具执行后会保存 `role=tool` 消息并重新构建上下文，因此工具结果参与本轮最终回复和后续对话。

当前采用最近消息条数截断，不按 token 预算裁剪，也不生成摘要。后续可加入 token 预算、上下文摘要、长期记忆、向量检索，以及工具调用与结果成组截断。

## 12. 错误处理说明

| 场景 | 错误码或处理 |
|---|---|
| 空消息 | `EMPTY_MESSAGE`，HTTP 422 |
| 消息过长 | `MESSAGE_TOO_LONG`，HTTP 422 |
| 请求字段或空标题 | `VALIDATION_ERROR`，HTTP 422 |
| 会话不存在 | `SESSION_NOT_FOUND`，HTTP 404 |
| 路由不存在 | `ROUTE_NOT_FOUND`，HTTP 404 |
| 方法不支持 | `METHOD_NOT_ALLOWED`，HTTP 405 |
| LLM Key 缺失 | `LLM_CONFIGURATION_ERROR`，HTTP 503 |
| Provider 未支持 | `LLM_PROVIDER_UNSUPPORTED`，HTTP 503 |
| LLM 调用异常 | `LLM_CALL_FAILED`，HTTP 502 |
| LLM 空回复 | `LLM_EMPTY_RESPONSE`，HTTP 502 |
| 工具不存在 | `failed` + `TOOL_NOT_FOUND` |
| 工具参数、非法表达式、除零 | `failed` + `TOOL_ARGUMENT_INVALID` |
| 工具未知异常 | `failed` + `TOOL_EXECUTION_FAILED` |
| 未处理服务端异常 | `INTERNAL_SERVER_ERROR`，HTTP 500 |

HTTP 错误统一返回 `{ "error": { "code", "message", "details" } }`。工具失败属于当前消息轮次的结构化结果，保存在 `data.tool_calls` 和内部 tool message 中，助手会返回相应失败提示。前端还会处理网络错误、非 JSON 响应和缺少 `data` 的非法响应。

## 13. 安全说明

- API Key 只能放在后端 `.env` 或密钥管理服务；前端不保存 LLM Key。
- `.env`、数据库、虚拟环境和构建产物已忽略，仓库只提供 `.env.example`。
- 用户输入有长度限制。
- 工具使用静态白名单，参数由 Pydantic 严格校验并拒绝多余字段。
- Todo 的 session ID 由后端注入，模型不能指定其他会话。
- Calculator 使用 AST 白名单和 `Decimal`，不执行 `eval`、Shell 或任意代码。
- 参数错误不会回显原始敏感输入；未知异常不向客户端暴露堆栈、路径或 API Key。
- 当前未实现用户认证、多用户权限隔离、限流和生产级访问控制。

## 14. 测试与验证

后端：

```bash
cd backend
pytest
```

可选冒烟检查：

```bash
python scripts/smoke_check.py
```

前端：

```bash
cd frontend
npm run typecheck
npm run lint
npm run build
```

手动验证：

1. 启动后端和前端。
2. 新建会话并发送普通消息。
3. 发送“现在几点？”。
4. 发送“帮我算一下 128 * 36 + 520”。
5. 发送“帮我记一个待办：明天提交笔试项目”。
6. 发送“我有哪些待办？”。
7. 新建/切换另一会话，确认待办不跨会话。
8. 刷新页面，确认会话、消息和工具卡片可恢复。
9. 发送“帮我算一下 1 / 0”，验证失败卡片和提示。

后端测试覆盖 API、上下文、工具成功/失败、持久化、会话隔离、统一错误、CORS 和旧 SQLite 结构兼容。

## 15. AI 使用说明

开发过程中使用了 ChatGPT、Codex 等 AI 工具辅助需求拆解、方案讨论、代码实现、重构、测试补充、联调修复和 README 整理。

AI 参与了架构与数据模型讨论、统一 API 契约、前端页面、后端接口、工具 schema、Mock LLM、错误处理和测试用例。人工负责确定 MVP 范围、优先保证 Mock 模式、选择 SQLite、确定工具白名单和 `/api/v1` 契约，审查 AI 生成代码，检查 API Key 不泄露，联调前后端，并验证核心演示流程。

本次文档整理还特别核实了真实 LLM 尚未接入，避免将预留配置夸大为已实现能力。最终范围、代码审查、运行验证和交付内容由开发者负责。

## 16. 已知限制

- 当前仅 Mock LLM 可运行；OpenAI-compatible Provider 仅预留配置和抽象。
- Mock LLM 基于规则，不具备真实模型推理能力。
- 每轮最多一次工具调用，不支持并行或连续多工具编排。
- Todo 仅支持创建和查询，不支持完成、编辑、删除。
- 未实现 SSE / WebSocket 流式输出。
- 上下文仅按最近消息数截断，没有摘要、token 预算或长期记忆。
- 未实现登录、多用户隔离、权限系统和生产级限流。
- 未实现工具超时、取消、重试、幂等和配额。
- 前端没有组件或端到端自动化测试。
- SQLite 与 `create_all` 适合本地演示，不适合高并发生产环境。
- 当前没有 Docker Compose 和线上 Demo。

## 17. 后续优化方向

- 实现真实 OpenAI-compatible Provider 和完整错误映射。
- 增加 SSE / WebSocket 流式输出。
- 支持连续/并行多工具、超时、取消和幂等。
- 扩展 Todo 完成、编辑和删除。
- 根据 OpenAPI 生成前端 TypeScript 类型。
- 增加文件上传、知识库检索和引用展示。
- 增加上下文摘要、长期记忆和向量检索。
- 增加认证、租户隔离、权限控制和限流。
- 引入 Alembic、结构化日志、监控和告警。
- 增加前端测试、端到端测试和 CI。
- 提供 Docker Compose 一键启动和线上 Demo。
