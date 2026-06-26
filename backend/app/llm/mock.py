import re
from typing import Any

from app.llm.base import LLMResult, ToolCallRequest


TODO_CREATE_PATTERN = re.compile(r"帮我记一个待办\s*[：:]\s*(.+)", re.DOTALL)
CALCULATION_PATTERN = re.compile(r"(?<!\w)([-+*/().\d\s]*\d\s*[-+*/]\s*[-+*/().\d\s]+)")
PROJECT_NAME_PATTERN = re.compile(
    r"(?:我这个项目|项目)\s*(?:叫|名为)\s*([^\n。！？!?]+)"
)


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

        if any(
            keyword in latest
            for keyword in ("我有哪些待办", "我的待办", "待办列表", "列出待办")
        ) or latest in ("待办", "待办？", "待办事项", "待办事项？"):
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

        if "项目叫什么" in latest or "项目名称" in latest:
            for message in reversed(messages[:-1]):
                if message.get("role") != "user":
                    continue
                project_match = PROJECT_NAME_PATTERN.search(message.get("content", ""))
                if project_match:
                    return LLMResult(
                        content=f"你刚刚说这个项目叫 {project_match.group(1).strip()}。"
                    )
            return LLMResult(content="你还没有在当前会话中告诉我项目名称。")

        if any(
            keyword in latest
            for keyword in (
                "哪些工具",
                "有什么工具",
                "可以调用什么",
                "能调用什么",
                "工具可以调用",
                "哪些功能",
                "什么功能",
                "实现哪些功能",
                "能实现",
                "能做什么",
                "都能做什么",
                "可以完成哪些",
                "完成哪些工具调用",
                "哪些工具调用",
                "工具调用",
                "当前模式",
                "这个模式",
                "做什么",
                "功能",
                "能力",
                "工具",
                "能干嘛",
                "可以干嘛",
                "可以做",
                "会做",
                "会什么",
                "支持什么",
                "支持哪些",
                "可用工具",
            )
        ):
            return LLMResult(
                content=(
                    "Mock 模式目前可以演示基础聊天和 3 个本地工具：\n"
                    "1. get_current_time：查询当前日期、时间和星期。\n"
                    "2. calculator：计算只包含数字、括号和 + - * / 的四则表达式。\n"
                    "3. todo_tool：在当前会话里创建或列出待办。"
                )
            )

        if any(
            keyword in latest
            for keyword in (
                "介绍一下你自己",
                "介绍一下自己",
                "介绍自己",
                "你是谁",
                "你能做什么",
            )
        ):
            return LLMResult(
                content=(
                    "我是当前项目的 Mock AI 助手，可以进行基础对话，"
                    "也可以调用时间、计算器和待办工具。你可以问我当前时间、"
                    "让我计算四则表达式，或让我记录和查看当前会话里的待办。"
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
            return f"计算结果：{tool_result['expression']} = {tool_result['value']}"
        if tool_name == "todo_tool" and tool_result.get("action") == "create":
            return f"已记下待办：{tool_result['todo']['title']}"
        if tool_name == "todo_tool" and tool_result.get("action") == "list":
            todos = tool_result.get("todos", [])
            if not todos:
                return "当前会话还没有待办事项。"
            lines = [f"{index}. {todo['title']}" for index, todo in enumerate(todos, 1)]
            return "当前会话的待办：\n" + "\n".join(lines)
        return f"工具 {tool_name} 已执行完成：{tool_result}"
