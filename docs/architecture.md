# AI Agent Chatbot MVP 架构设计

## 1. 目标与边界

本项目采用前后端分离的本地应用架构。第一阶段优先保证工程可运行、接口和数据边界稳定，并为多轮上下文、模型供应商切换和工具调用留下清晰扩展点。

```text
React/Vite
    │ HTTP JSON
    ▼
FastAPI /api/v1
    ├─ Session & Message Service
    ├─ Agent Orchestrator
    │   ├─ Context Builder
    │   ├─ LLM Provider (Mock / OpenAI-compatible)
    │   └─ Tool Registry
    └─ SQLModel → SQLite
```

前端不保存权威会话状态，也不直接执行工具。后端负责持久化、上下文组装、工具参数校验、执行和错误归一化。

## 2. 目录职责

```text
backend/app/
├─ api/v1/routes/     HTTP 路由，只处理协议和依赖注入
├─ agents/            单轮 Agent 编排与状态机
├─ core/              配置、数据库、异常处理
├─ llm/               Mock 与 OpenAI-compatible provider
├─ models/            SQLModel 持久化模型
├─ schemas/           Pydantic API 契约
└─ tools/             工具定义、参数模型、注册表和执行器

frontend/src/
├─ lib/api.ts         API 客户端和错误转换
├─ types/api.ts       与后端契约对应的 TypeScript 类型
├─ App.tsx            当前 MVP 页面组合
└─ styles.css         Tailwind 入口和全局样式
```

后续前端增长时，可继续拆出 `components/`、`features/chat/` 和状态管理层。

## 3. API 契约

API 前缀：`/api/v1`

| Method | Path | 用途 |
|---|---|---|
| GET | `/health` | 服务与 provider 状态 |
| GET | `/sessions` | 按更新时间倒序读取会话 |
| POST | `/sessions` | 新建会话 |
| GET | `/sessions/{session_id}` | 获取会话、消息和工具调用 |
| POST | `/sessions/{session_id}/messages` | 发送消息并获得本轮结果 |

成功响应统一包裹：

```json
{
  "data": {}
}
```

失败响应统一为：

```json
{
  "error": {
    "code": "SESSION_NOT_FOUND",
    "message": "Session does not exist.",
    "details": {
      "session_id": "..."
    }
  }
}
```

`code` 面向程序判断，`message` 面向用户或日志，`details` 保存字段错误、工具错误参数等结构化上下文。

## 4. 数据模型

### sessions

会话元数据：`id`、`title`、`created_at`、`updated_at`。

### messages

完整消息记录：`session_id`、`role`、`content`、`created_at`。`role` 仅允许 `user`、`assistant`、`tool`。

### tool_calls

记录工具执行生命周期和可观测信息：

- 工具名称与 JSON 参数。
- 对应 assistant/tool message。
- `pending / succeeded / failed` 状态。
- 结构化结果或 `error_code / error_message`。
- 创建与完成时间。

### todos

`todo_tool` 的业务数据，按会话隔离，包含内容、完成状态和时间字段。

当前使用 SQLModel `create_all` 初始化；若进入协作或生产阶段，应加入 Alembic。

## 5. 多轮上下文策略

每次聊天请求执行以下步骤：

1. 验证 session 存在并持久化新的 user message。
2. 按 `created_at DESC` 读取当前会话最近 `CONTEXT_MESSAGE_LIMIT` 条消息。
3. 在内存中反转为时间正序。
4. 添加系统提示，规范化 user / assistant / tool 消息。
5. 发送给当前 LLM provider。

第一版采用“最近 N 条”策略，行为明确且易于测试。后续可以改为 token budget，并在截断前生成会话摘要。工具消息必须与相关 assistant 工具调用一起保留，避免上下文出现不完整调用链。

## 6. 工具调用流程

```text
用户消息
  → Context Builder
  → LLM/Mock Router 判断是否调用工具
  → 根据 tool_name 查 Tool Registry
  → Pydantic 参数校验
  → 创建 pending tool_call
  → 执行工具
  → 保存 tool message 与 succeeded/failed 结果
  → 将工具结果追加给 LLM
  → 生成最终 assistant message
  → 一次性返回本轮消息与 tool_calls
```

关键约束：

- 前端没有“执行工具”接口或按钮，只展示后端返回的调用过程。
- `calculator` 使用受限表达式解析器，只允许数字、括号和四则运算，禁止 `eval`。
- 所有工具参数由 Pydantic schema 校验。
- 工具异常转换为稳定的结构化错误，不向模型或客户端暴露堆栈。
- todo 数据访问必须使用当前 session id，不能由模型任意指定其他会话。

后续若加入流式响应，可把 `tool_call.created`、`tool_call.completed`、`message.delta` 设计为 SSE 事件，但数据库仍是最终事实来源。

## 7. Mock 设计

Mock provider 的目的不是伪造智能，而是提供稳定、可重复、无需密钥的验收路径。

计划的规则优先级：

1. 时间相关关键词 → `get_current_time`。
2. 明确数学表达式或计算意图 → `calculator`。
3. 创建、查询、完成待办意图 → `todo_tool`。
4. 其他输入 → 可预测的普通文本回复。

Mock router 输出与 OpenAI-compatible provider 相同的内部 `AssistantDecision` 结构，因此 Agent 编排层无需区分来源。测试可以固定输入并断言工具名称、参数、持久化顺序和最终回复。

## 8. OpenAI-compatible 模式

当 `LLM_PROVIDER=openai` 时，provider 使用：

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_MODEL`

适配器只负责协议转换，不直接访问数据库或执行工具。启动时若选择 openai 但缺少 API Key，应快速失败并返回明确配置错误。任何真实密钥只能存在本地 `.env` 或密钥管理系统中，不得提交版本库。

## 9. 一致性与错误策略

单轮聊天中，用户消息、工具调用和最终回复应尽量在一个服务层事务边界中管理。耗时外部调用无法与 SQLite 形成真正的分布式事务，因此需要持久化 `pending` 状态，并允许后续将中断调用标记为 `failed`。

典型错误码：

- `VALIDATION_ERROR`
- `EMPTY_MESSAGE`
- `SESSION_NOT_FOUND`
- `LLM_CONFIGURATION_ERROR`
- `LLM_REQUEST_FAILED`
- `TOOL_NOT_FOUND`
- `TOOL_ARGUMENT_ERROR`
- `TOOL_EXECUTION_FAILED`

## 10. 下一阶段实现顺序

1. 将当前 route 中的 Mock 回声迁移到 Agent service。
2. 实现 Context Builder 和 provider factory。
3. 实现三个工具及参数 schema。
4. 实现“模型决策 → 工具执行 → 模型总结”的完整循环。
5. 增加 pytest、前端组件测试和 API 集成测试。
6. 视需要加入 SSE 流式输出、Alembic 和会话分页。

