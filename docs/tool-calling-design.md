# AI 工具调用设计

## 1. 目标与边界

本项目的工具调用链路遵守现有统一 API 契约：成功响应为 `{ "data": ... }`，错误响应为 `{ "error": { "code", "message", "details" } }`，消息发送接口保持为 `POST /api/v1/sessions/{session_id}/messages`。

工具由后端白名单注册、校验和执行。前端只展示后端返回的调用记录，不直接执行工具，也不接受用户指定模块路径或可执行代码。

## 2. 整体流程

1. API 校验 session 和用户消息，将 `role=user` 消息写入数据库。
2. Context Builder 按当前 `session_id` 读取最近消息，包含 `user`、`assistant`、`tool` 三种角色。
3. LLM Provider 返回普通文本或一个规范化 tool call。
4. Agent 根据 `tool_name` 查询静态 Tool Registry 白名单。
5. Registry 使用工具对应的 Pydantic input model 校验参数。
6. Agent 先创建 `pending` 的 `tool_calls` 记录，再执行工具。
7. 执行成功时保存结果并更新为 `succeeded`；失败时保存稳定错误码、用户可理解错误信息并更新为 `failed`。
8. 无论成功或失败，都创建一条 `role=tool` message，内容包含工具名、参数、状态、结果和错误摘要。
9. 工具消息重新进入上下文，Provider 基于工具结果生成最终 assistant message。
10. API 在 `data.tool_calls` 中返回本轮工具调用，供前端工具卡片展示。

工具参数错误或未注册工具属于“本轮工具执行失败”，不会让非法 LLM tool call 导致服务崩溃。HTTP 请求仍按既有成功契约返回本轮 user message、assistant message 和 `failed` tool call。

## 3. Mock LLM 如何决定调用工具

`backend/app/llm/mock.py` 使用确定性规则，便于离线测试：

- 包含“现在几点”“今天日期”“星期几”时调用 `get_current_time`。
- 检测到四则运算表达式，或以“计算”“算一下”“帮我算”开头时调用 `calculator`。
- “帮我记一个待办：...”调用 `todo_tool` 的 `create` 动作。
- “我有哪些待办”或“我的待办”调用 `todo_tool` 的 `list` 动作。
- 其他输入返回普通 Mock 文本。

Mock Provider 与未来真实 Provider 使用相同的内部 `ToolCallRequest`，Agent 不根据 Provider 来源切换执行逻辑。

## 4. 工具注册与 schema

注册表位于 `backend/app/tools/registry.py`。每个 `ToolDefinition` 明确定义：

- `name`：白名单工具名。
- `description`：提供给 LLM 的用途说明。
- `input_model` / `parameters_schema`：Pydantic 参数模型及其 JSON Schema。
- `executor`：固定执行函数。
- `result_description`：成功返回说明。
- `failure_description`：失败情况说明。

`ToolRegistry.llm_schemas()` 可输出 LLM 使用的 `name`、`description`、`parameters`。重复注册会被拒绝，调用时只按内存中的静态字典查找，不动态导入模块。

### 4.1 get_current_time

用途：获取指定时区的当前日期、时间和星期。

参数：

- `timezone: string`，可选，默认 `Asia/Shanghai`，使用 IANA 时区名称。

成功结果：

```json
{
  "date": "2026-06-25",
  "time": "14:30:00",
  "timezone": "Asia/Shanghai",
  "weekday": "星期四"
}
```

失败：时区名称未知、字段类型错误或出现未声明字段时，tool call 状态为 `failed`，错误码为 `TOOL_ARGUMENT_INVALID`。

### 4.2 calculator

用途：计算受限四则运算表达式。

参数：

- `expression: string`，必填，长度 1 到 200。

允许字符只有数字、括号、小数点、空格、`+`、`-`、`*`、`/`。实现使用 Python AST 白名单节点和 `Decimal` 计算，不使用 `eval`，不允许名称、属性、函数调用、下标、幂运算或任意代码。

成功结果：

```json
{
  "expression": "(12.5 + 7.5) / 4",
  "value": "5"
}
```

失败：非法字符、语法错误、参数缺失、参数类型错误、除零均返回 `TOOL_ARGUMENT_INVALID` 和清晰错误信息。

### 4.3 todo_tool create

用途：为当前会话创建待办。

参数：

- `action: "create"`，必填。
- `title: string`，create 动作必填，最大 500 字符，不能为空白。

成功结果包含 `action` 和新建 `todo` 的 `id`、`title`、`status`、`created_at`。

失败：缺少 title、title 类型错误、空标题或多余字段时返回 `TOOL_ARGUMENT_INVALID`。

### 4.4 todo_tool list

用途：列出当前会话的待办。

参数：

- `action: "list"`，必填。
- list 动作不接受 title。

成功结果包含 `action` 和 `todos` 数组。查询条件固定使用 Agent 注入的当前 `session_id`，LLM 和用户参数不能指定其他 session，因此不会跨会话读取待办。

## 5. 白名单与参数校验

安全边界如下：

- 工具只能通过 `ToolRegistry.register()` 静态注册。
- 未注册名称转换为 `TOOL_NOT_FOUND`，不会执行动态 import。
- 不执行用户输入代码或 shell 命令。
- 所有 input model 配置 `extra="forbid"`，拒绝未声明字段。
- 字符串关键字段采用严格类型校验，避免数字等值被隐式转换。
- Pydantic 错误详情移除原始 input、异常 context 和文档 URL后再持久化，避免不可序列化对象和内部信息泄露。
- executor 的未知异常统一映射为 `TOOL_EXECUTION_FAILED`，对外不返回内部异常文本或堆栈。

## 6. 失败结果

项目优先沿用现有 `ToolCallRead` 契约，不新增不兼容根字段。失败调用示例：

```json
{
  "tool_name": "calculator",
  "arguments": {"expression": "1 / 0"},
  "result": {
    "error": {
      "code": "TOOL_ARGUMENT_INVALID",
      "details": {"reason": "除数不能为零。"}
    }
  },
  "status": "failed",
  "error_code": "TOOL_ARGUMENT_INVALID",
  "error_message": "除数不能为零。"
}
```

数据库既有成功状态值为 `succeeded`，失败值为 `failed`。前端将其分别展示为“成功”和“失败”，没有修改既有字段名或枚举值。

## 7. 持久化

`tool_calls` 保存：

- `session_id`
- 数据库列 `message_id`（模型字段 `assistant_message_id`）
- `tool_message_id`
- `tool_name`
- `arguments`
- `result`
- `status`
- `error_code`
- `error_message`
- `created_at`
- `completed_at`

Todo 数据单独保存在 `todos` 表，并带有强制的 `session_id`。

## 8. 工具结果进入上下文

每次工具执行后都会保存 `role=tool` message。message 内容为 JSON，包含：

- `tool_name`
- `arguments`
- `status`
- `result`
- `error_code`
- `error_message`

`build_context()` 不过滤 tool role，因此后续多轮请求和本轮最终回答都能读取工具结果。message metadata 还保存 `tool_call_id`、`tool_name` 和 `status`，便于关联和排查。

## 9. 前端展示

后端消息接口继续返回：

```json
{
  "data": {
    "user_message": {},
    "assistant_message": {},
    "tool_calls": []
  }
}
```

`frontend/src/types/api.ts` 已有与 `ToolCallRead` 对齐的类型，`frontend/src/lib/api.ts` 保留统一 `data` 解包和 `error` 解析。`MessageTimeline` 的工具卡片展示：

- 工具名称
- 参数 JSON
- pending / 成功 / 失败状态
- 返回结果
- `error_message` 和 `error_code`

当前字段已满足展示要求，因此本次不改变前端 API 类型和响应结构。

## 10. 测试覆盖

后端测试覆盖：时间工具成功、calculator 成功、非法表达式、除零、错误参数类型、todo 创建与查询、todo session 隔离、未注册工具、畸形 arguments、tool_calls 持久化、role=tool message 持久化、上下文读取 tool message，以及消息 API 返回前端可展示数据。

前端通过 `npm run typecheck`、`npm run build` 和 `npm run lint` 验证类型、构建与静态规则。

## 11. 手动验证

启动后端和前端后，可依次发送：

1. `你好，简单介绍一下你自己。`
2. `我这个项目叫 ToolMind Chatbot。`
3. `我刚刚说项目叫什么？`
4. `现在几点？`
5. `帮我算一下 128 * 36 + 520`
6. `帮我算一下 1 / 0`
7. `帮我记一个待办：明天提交笔试项目`
8. `我有哪些待办？`

另建一个会话后发送“我有哪些待办？”，结果应为空。刷新页面后，结构化工具卡片仍应从数据库恢复；持久化的 `role=tool` 消息作为内部上下文保留，不重复渲染为普通聊天气泡。

## 12. 当前限制与后续优化

- 当前一次 LLM 决策只执行一个工具调用，尚未支持并行或连续多工具循环。
- Mock LLM 使用规则匹配，不具备真实语义理解。
- 真实 OpenAI-compatible Provider 尚未接入当前骨架。
- SQLite 初始化主要依赖 `create_all` 和有限兼容迁移；生产环境应使用 Alembic。
- 尚未实现工具超时、取消、重试、幂等键、权限分级和调用配额。
- 上下文目前按消息条数截断，后续可改为 token budget，并保证相关 tool call/message 成组保留。
