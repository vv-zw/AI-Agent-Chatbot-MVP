# AI Agent Chatbot MVP

一个本地优先的全栈 AI Chatbot 骨架，采用 React + FastAPI + SQLite。当前阶段重点是清晰、可运行的工程结构、API 契约、数据库模型和后续 Agent 工具调用扩展点。

## 目录

```text
.
├─ backend/               FastAPI、SQLModel、LLM/工具扩展层
├─ frontend/              React、Vite、TypeScript、Tailwind CSS
├─ docs/architecture.md   架构与核心流程说明
└─ .env.example           环境变量示例（不包含真实密钥）
```

## 本地启动

### 后端

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy ..\.env.example .env
uvicorn app.main:app --reload
```

打开 `http://127.0.0.1:8000/docs` 查看 OpenAPI 文档。

### 前端

```bash
cd frontend
npm install
npm run dev
```

打开 `http://localhost:5173`。

## 环境变量

- `LLM_PROVIDER=mock`：默认模式，无需 API Key。
- `LLM_PROVIDER=openai`：OpenAI-compatible API 模式。
- `OPENAI_API_KEY`：仅在 OpenAI-compatible 模式下需要。
- `OPENAI_BASE_URL`：兼容服务地址。
- `OPENAI_MODEL`：模型名称。
- `CONTEXT_MESSAGE_LIMIT`：每轮发送给 LLM 的最近消息数量。
- `VITE_API_BASE_URL`：前端访问后端的 API 根地址。

## Mock 模式与工具调用

Mock provider 后续会根据关键词稳定地产生普通回复或工具调用，便于离线演示。工具由后端 Agent 层选择和执行，前端只展示过程，不直接触发工具。

预留工具：

- `get_current_time`
- `calculator`
- `todo_tool`

详细流程见 [docs/architecture.md](docs/architecture.md) 和 [docs/tool-calling-design.md](docs/tool-calling-design.md)。

## 技术选型

- React + Vite + TypeScript：快速、类型明确的前端开发体验。
- Tailwind CSS：低成本构建一致的 MVP 界面。
- FastAPI + SQLModel：API 契约和持久化模型都具备良好类型支持。
- SQLite：零外部依赖，适合笔试和本地演示。
- Provider/Tool Registry 抽象：隔离模型厂商与工具实现。

## AI 使用方式

项目允许通过 OpenAI-compatible API 驱动回复与工具选择；默认 Mock provider 保证无密钥也能验收。所有模型输出都应在服务端经过参数校验后再执行工具。

## 当前骨架已实现

- 会话列表、新建、查询与切换所需 API。
- 消息读取和 Mock 聊天闭环。
- sessions、messages、tool_calls、todos 数据模型。
- 统一成功数据模型与结构化错误格式。
- 前端基础会话栏、消息区、输入状态与错误展示。

## 已知限制与后续优化

- 当前 Mock LLM 使用确定性规则完成基础回复和单次工具路由；真实 OpenAI provider 仍是明确的扩展位。
- 尚未加入流式输出、鉴权、分页游标、并发写保护和生产级迁移工具。
- 当前已实现工具参数 schema、白名单执行、调用状态持久化和 session 级 Todo 隔离；完整 Todo CRUD 与工具重试策略仍待后续实现。
- SQLite 建表使用 `create_all`；生产环境应改为 Alembic 迁移。

