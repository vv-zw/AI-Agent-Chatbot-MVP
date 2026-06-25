import re
from typing import Any

from app.llm.base import LLMResult, ToolCallRequest


TODO_CREATE_PATTERN = re.compile(r"帮我记一个待办\s*[：:]\s*(.+)", re.DOTALL)
CALCULATION_PATTERN = re.compile(r"(?<!\w)([-+*/().\d\s]*\d\s*[-+*/]\s*[-+*/().\d\s]+)")


class MockLLMProvider:
    def complete(self, messages: list[dict[str, str]]) -> LLMResult:
        latest = messages[-1]["content"].strip() if messages else ""

        todo_match = TODO_CREATE_PATTERN.search(latest)
        if todo_match:
            return LLMResult(
                tool_call=ToolCallRequest(
                    name="todo_tool",
                    arguments={"action": "create", "title": todo_match.group(1).strip()},
                )
            )

        if "我有哪些待办" in latest or "我的待办" in latest:
            return LLMResult(
                tool_call=ToolCallRequest(
                    name="todo_tool",
                    arguments={"action": "list"},
                )
            )

        if any(keyword in latest for keyword in ("现在几点", "今天日期", "星期几")):
            return LLMResult(
                tool_call=ToolCallRequest(name="get_current_time", arguments={})
            )

        calculation = CALCULATION_PATTERN.search(latest)
        if calculation:
            return LLMResult(
                tool_call=ToolCallRequest(
                    name="calculator",
                    arguments={"expression": calculation.group(1).strip()},
                )
            )
        if latest.startswith(("计算", "算一下", "帮我算")):
            expression = re.sub(r"^(计算|算一下|帮我算)\s*[：:]?\s*", "", latest)
            return LLMResult(
                tool_call=ToolCallRequest(
                    name="calculator",
                    arguments={"expression": expression},
                )
            )

        return LLMResult(content=f"[Mock] 我收到了：{latest}")

    def complete_with_tool_result(
        self,
        messages: list[dict[str, str]],
        tool_name: str,
        result: dict[str, Any],
    ) -> str:
        if result.get("status") == "failed":
            return (
                f"工具 {tool_name} 调用失败："
                f"{result.get('error_message') or '请检查参数后重试。'}"
            )

        tool_result = result.get("result")
        if not isinstance(tool_result, dict):
            return f"工具 {tool_name} 已执行完成。"

        if tool_name == "get_current_time":
            return (
                f"当前日期是 {tool_result['date']}，时间是 {tool_result['time']}，"
                f"{tool_result['weekday']}（{tool_result['timezone']}）。"
            )
        if tool_name == "calculator":
            return (
                f"计算结果：{tool_result['expression']} = {tool_result['value']}"
            )
        if tool_name == "todo_tool" and tool_result.get("action") == "create":
            return f"已记下待办：{tool_result['todo']['title']}"
        if tool_name == "todo_tool" and tool_result.get("action") == "list":
            todos = tool_result.get("todos", [])
            if not todos:
                return "当前会话还没有待办事项。"
            lines = [f"{index}. {todo['title']}" for index, todo in enumerate(todos, 1)]
            return "当前会话的待办：\n" + "\n".join(lines)
        return f"工具 {tool_name} 已执行完成：{tool_result}"
