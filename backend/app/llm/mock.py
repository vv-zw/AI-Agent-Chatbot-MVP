import re
from typing import Any

from app.llm.base import LLMResult, ToolCallRequest


TODO_CREATE_PATTERN = re.compile(r"帮我记一个待办\s*[：:]\s*(.+)", re.DOTALL)
CALCULATION_PATTERN = re.compile(r"(?<!\w)([-+*/().\d\s]*\d\s*[-+*/]\s*[-+*/().\d\s]+)")
PROJECT_NAME_PATTERN = re.compile(
    r"(?:我这个项目|项目)\s*(?:叫|名为)\s*([^\n。！？!?]+)"
)
TIME_QUERY_PHRASES = (
    "现在几点",
    "几点了",
    "现在什么时间",
    "现在的时间",
    "当前时间",
    "今天日期",
    "今天几号",
    "星期几",
)
TIME_QUERY_EXACT = {"时间", "时间？", "时间?", "日期", "日期？", "日期?"}


def active_role(messages: list[dict[str, str]]) -> str:
    system_text = "\n".join(
        message.get("content", "")
        for message in messages
        if message.get("role") == "system"
    )
    if "代码助手" in system_text:
        return "code"
    if "写作助手" in system_text:
        return "writing"
    if "面试助手" in system_text:
        return "interview"
    return "general"


def role_intro(role: str) -> str:
    if role == "code":
        return "我是当前项目的 Mock 代码助手，会优先从问题原因、修改思路、关键代码和验证方式来协助你。"
    if role == "writing":
        return "我是当前项目的 Mock 写作助手，会优先帮你梳理结构、优化措辞并润色表达。"
    if role == "interview":
        return "我是当前项目的 Mock 面试助手，会优先按背景、思路、取舍、结果来组织回答。"
    return (
        "我是当前项目的 Mock AI 助手，可以进行基础对话，"
        "也可以调用时间、计算器和待办工具。你可以问我当前时间、"
        "让我计算四则表达式，或让我记录和查看当前会话里的待办。"
    )


def role_default_reply(role: str, latest: str) -> str:
    if role == "code":
        return (
            f"[Mock - 代码助手] 我收到：{latest}\n"
            "技术视角：我会先定位现象和原因，再给出修改建议、示例代码和验证步骤。"
        )
    if role == "writing":
        return (
            f"[Mock - 写作助手] 我收到：{latest}\n"
            "表达视角：我会先梳理核心观点，再优化结构、语气和措辞，让内容更顺。"
        )
    if role == "interview":
        return (
            f"[Mock - 面试助手] 我收到：{latest}\n"
            "面试视角：建议按背景、行动、结果、复盘来回答，突出你的判断和取舍。"
        )
    return f"[Mock] 我收到了：{latest}"


def role_response(role: str, content: str) -> str:
    labels = {
        "code": "[Mock - 代码助手]",
        "writing": "[Mock - 写作助手]",
        "interview": "[Mock - 面试助手]",
    }
    label = labels.get(role)
    return f"{label} {content}" if label else content


def is_time_query(content: str) -> bool:
    normalized = content.strip().replace(" ", "")
    if "时间复杂度" in normalized:
        return False
    return normalized in TIME_QUERY_EXACT or any(
        phrase in normalized for phrase in TIME_QUERY_PHRASES
    )


TODO_LIST_PHRASES = (
    "我有哪些待办", "我的待办", "待办列表", "列出待办",
)
TODO_FOLLOWUP_PATTERN = re.compile(
    r"[，,；;。]\s*(?:然后|再|并且|并)?\s*(?=(?:告诉|看看|查询|查|列|帮我|算|现在))"
)


def _first_phrase_position(content: str, phrases: tuple[str, ...]) -> int | None:
    positions = [content.find(phrase) for phrase in phrases if phrase in content]
    return min(positions) if positions else None


def plan_tool_calls(content: str) -> tuple[ToolCallRequest, ...]:
    """Build an ordered, independent tool plan from one Mock user request."""
    candidates: list[tuple[int, int, ToolCallRequest]] = []
    todo_match = TODO_CREATE_PATTERN.search(content)
    if todo_match:
        raw_title = todo_match.group(1).strip()
        title = TODO_FOLLOWUP_PATTERN.split(raw_title, maxsplit=1)[0].rstrip("，,；;。 ")
        candidates.append((todo_match.start(), 0, ToolCallRequest(
            name="todo_tool", arguments={"action": "create", "title": title}
        )))

    todo_list_position = _first_phrase_position(content, TODO_LIST_PHRASES)
    if todo_list_position is not None or content.strip() in (
        "待办", "待办？", "待办事项", "待办事项？",
    ):
        candidates.append((todo_list_position or 0, 1, ToolCallRequest(
            name="todo_tool", arguments={"action": "list"}
        )))

    time_position = _first_phrase_position(content, TIME_QUERY_PHRASES)
    if time_position is not None or content.strip().replace(" ", "") in TIME_QUERY_EXACT:
        candidates.append((time_position or 0, 2, ToolCallRequest(
            name="get_current_time", arguments={}
        )))

    calculation = CALCULATION_PATTERN.search(content)
    if calculation:
        candidates.append((calculation.start(), 3, ToolCallRequest(
            name="calculator", arguments={"expression": calculation.group(1).strip()}
        )))

    candidates.sort(key=lambda item: (item[0], item[1]))
    return tuple(item[2] for item in candidates)


class MockLLMProvider:
    def complete(self, messages: list[dict[str, str]]) -> LLMResult:
        latest = messages[-1]["content"].strip() if messages else ""
        role = active_role(messages)

        tool_calls = plan_tool_calls(latest)
        if tool_calls:
            return LLMResult(tool_calls=tool_calls)

        if latest.startswith(("计算", "算一下", "帮我算")):
            expression = re.sub(r"^(计算|算一下|帮我算)\s*[：:]?\s*", "", latest)
            if not any(character.isdigit() for character in expression):
                if any(keyword in expression for keyword in ("四则", "表达式", "算式")):
                    return LLMResult(content=role_response(
                        role, "请提供具体的四则表达式，例如：计算 (8 + 4) / 3。"
                    ))
                return LLMResult(content=role_default_reply(role, latest))
            return LLMResult(
                tool_calls=(ToolCallRequest(name="calculator", arguments={"expression": expression}),)
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
                content=role_response(
                    role,
                    (
                        "Mock 模式目前可以演示基础聊天和 3 个本地工具：\n"
                        "1. get_current_time：查询当前日期、时间和星期。\n"
                        "2. calculator：计算只包含数字、括号和 + - * / 的四则表达式。\n"
                        "3. todo_tool：在当前会话里创建或列出待办。"
                    ),
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
            return LLMResult(content=role_intro(role))

        return LLMResult(content=role_default_reply(role, latest))

    def complete_with_tool_result(
        self,
        messages: list[dict[str, str]],
        tool_name: str,
        result: dict[str, Any],
    ) -> str:
        return self.complete_with_tool_results(messages, [result])

    def complete_with_tool_results(
        self,
        messages: list[dict[str, str]],
        results: list[dict[str, Any]],
    ) -> str:
        role = active_role(messages)
        summaries = [self._summarize_tool_result(item) for item in results]
        if len(summaries) == 1:
            return role_response(role, summaries[0])
        failed_count = sum(item.get("status") == "failed" for item in results)
        succeeded_count = len(results) - failed_count
        heading = (
            f"已完成多工具编排：{succeeded_count} 项成功，{failed_count} 项失败。"
            if failed_count
            else f"已按顺序完成 {len(results)} 项工具调用："
        )
        details = "\n".join(f"{i}. {summary}" for i, summary in enumerate(summaries, 1))
        return role_response(role, f"{heading}\n{details}")

    @staticmethod
    def _summarize_tool_result(result: dict[str, Any]) -> str:
        tool_name = str(result.get("tool_name") or "<unknown>")
        if result.get("status") == "failed":
            reason = result.get("error_message") or "请检查参数后重试。"
            return f"工具 {tool_name} 调用失败：{reason}"
        tool_result = result.get("result")
        if not isinstance(tool_result, dict):
            return f"工具 {tool_name} 已执行完成。"
        if tool_name == "get_current_time":
            return (f"当前日期是 {tool_result['date']}，时间是 {tool_result['time']}，"
                    f"{tool_result['weekday']}（{tool_result['timezone']}）。")
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
