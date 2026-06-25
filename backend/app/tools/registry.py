import ast
import operator
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as datetime_timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from sqlmodel import Session, select

from app.models import Todo


class ToolNotFoundError(Exception):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Tool is not registered: {name}")


class ToolArgumentError(Exception):
    def __init__(self, details: Any, message: str = "工具参数不合法。") -> None:
        self.details = details
        super().__init__(message)


class ToolExecutionError(Exception):
    def __init__(self, message: str = "工具执行失败。") -> None:
        super().__init__(message)


@dataclass(frozen=True)
class ToolContext:
    db: Session
    session_id: UUID


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CurrentTimeInput(ToolInput):
    timezone: str = Field(
        default="Asia/Shanghai",
        min_length=1,
        max_length=100,
        strict=True,
        description="IANA 时区名称，例如 Asia/Shanghai。",
    )


class CalculatorInput(ToolInput):
    expression: str = Field(
        min_length=1,
        max_length=200,
        strict=True,
        description="仅包含数字、括号、小数点、空格和 + - * / 的四则运算表达式。",
    )

    @field_validator("expression")
    @classmethod
    def validate_expression_characters(cls, value: str) -> str:
        expression = value.strip()
        if not re.fullmatch(r"[0-9().+\-*/\s]+", expression):
            raise ValueError("表达式只能包含数字、括号、小数点、空格和加减乘除符号。")
        return expression


class TodoInput(ToolInput):
    action: Literal["create", "list"]
    title: str | None = Field(
        default=None,
        max_length=500,
        strict=True,
        description="待办标题；action=create 时必填，action=list 时不应提供。",
    )

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        title = value.strip()
        if not title:
            raise ValueError("待办标题不能为空。")
        return title

    @model_validator(mode="after")
    def validate_action_arguments(self) -> "TodoInput":
        if self.action == "create" and self.title is None:
            raise ValueError("创建待办时必须提供 title。")
        if self.action == "list" and self.title is not None:
            raise ValueError("查询待办时不应提供 title。")
        return self


ToolExecutor = Callable[[ToolContext, BaseModel], dict[str, Any]]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_model: type[BaseModel]
    executor: ToolExecutor
    result_description: str
    failure_description: str

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return self.input_model.model_json_schema()

    def to_llm_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_schema,
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        if definition.name in self._tools:
            raise ValueError(f"工具已注册：{definition.name}")
        self._tools[definition.name] = definition

    def names(self) -> tuple[str, ...]:
        return tuple(self._tools)

    def definitions(self) -> tuple[ToolDefinition, ...]:
        return tuple(self._tools.values())

    def llm_schemas(self) -> list[dict[str, Any]]:
        return [definition.to_llm_schema() for definition in self._tools.values()]

    def execute(
        self,
        name: str,
        arguments: Any,
        context: ToolContext,
    ) -> dict[str, Any]:
        definition = self._tools.get(name)
        if definition is None:
            raise ToolNotFoundError(name)
        try:
            validated = definition.input_model.model_validate(arguments)
        except ValidationError as exc:
            raise ToolArgumentError(
                exc.errors(
                    include_url=False,
                    include_context=False,
                    include_input=False,
                )
            ) from exc
        try:
            return definition.executor(context, validated)
        except ToolArgumentError:
            raise
        except Exception as exc:
            raise ToolExecutionError() from exc


_BINARY_OPERATORS: dict[type[ast.operator], Callable[[Decimal, Decimal], Decimal]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_UNARY_OPERATORS: dict[type[ast.unaryop], Callable[[Decimal], Decimal]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _evaluate_node(node: ast.AST) -> Decimal:
    if isinstance(node, ast.Expression):
        return _evaluate_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return Decimal(str(node.value))
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        return _BINARY_OPERATORS[type(node.op)](
            _evaluate_node(node.left),
            _evaluate_node(node.right),
        )
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _UNARY_OPERATORS[type(node.op)](_evaluate_node(node.operand))
    raise ToolArgumentError(
        {"reason": "表达式包含不支持的语法。"},
        "表达式包含不支持的语法。",
    )


def get_current_time(_: ToolContext, payload: BaseModel) -> dict[str, Any]:
    data = CurrentTimeInput.model_validate(payload)
    try:
        timezone = ZoneInfo(data.timezone)
    except ZoneInfoNotFoundError as exc:
        if data.timezone != "Asia/Shanghai":
            raise ToolArgumentError(
                {"timezone": data.timezone, "reason": "未知时区。"},
                "时区参数不合法。",
            ) from exc
        timezone = datetime_timezone(timedelta(hours=8), name="Asia/Shanghai")
    current = datetime.now(timezone)
    weekdays = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")
    return {
        "date": current.date().isoformat(),
        "time": current.strftime("%H:%M:%S"),
        "timezone": data.timezone,
        "weekday": weekdays[current.weekday()],
    }


def calculator(_: ToolContext, payload: BaseModel) -> dict[str, Any]:
    data = CalculatorInput.model_validate(payload)
    try:
        tree = ast.parse(data.expression, mode="eval")
        value = _evaluate_node(tree)
    except (SyntaxError, InvalidOperation) as exc:
        raise ToolArgumentError(
            {"reason": "表达式格式不正确。"},
            "表达式格式不正确。",
        ) from exc
    except ZeroDivisionError as exc:
        raise ToolArgumentError(
            {"reason": "除数不能为零。"},
            "除数不能为零。",
        ) from exc
    normalized = format(value.normalize(), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return {"expression": data.expression, "value": normalized or "0"}


def todo_tool(context: ToolContext, payload: BaseModel) -> dict[str, Any]:
    data = TodoInput.model_validate(payload)
    if data.action == "create":
        assert data.title is not None
        todo = Todo(session_id=context.session_id, title=data.title)
        context.db.add(todo)
        context.db.flush()
        return {
            "action": "create",
            "todo": {
                "id": str(todo.id),
                "title": todo.title,
                "status": todo.status.value,
                "created_at": todo.created_at.isoformat(),
            },
        }

    todos = context.db.exec(
        select(Todo)
        .where(Todo.session_id == context.session_id)
        .order_by(Todo.created_at)
    ).all()
    return {
        "action": "list",
        "todos": [
            {
                "id": str(todo.id),
                "title": todo.title,
                "status": todo.status.value,
                "created_at": todo.created_at.isoformat(),
            }
            for todo in todos
        ],
    }


tool_registry = ToolRegistry()
tool_registry.register(
    ToolDefinition(
        name="get_current_time",
        description="获取指定时区的当前日期、时间和星期。",
        input_model=CurrentTimeInput,
        executor=get_current_time,
        result_description="返回 date、time、timezone、weekday。",
        failure_description="时区不存在或参数类型不合法时返回结构化失败。",
    )
)
tool_registry.register(
    ToolDefinition(
        name="calculator",
        description="安全计算只含数字、括号和加减乘除符号的四则运算表达式。",
        input_model=CalculatorInput,
        executor=calculator,
        result_description="返回原表达式 expression 和字符串形式的计算结果 value。",
        failure_description="非法字符、非法语法、参数缺失或除零时返回结构化失败。",
    )
)
tool_registry.register(
    ToolDefinition(
        name="todo_tool",
        description="在当前会话中创建待办，或列出当前会话的全部待办。",
        input_model=TodoInput,
        executor=todo_tool,
        result_description="create 返回 todo；list 返回仅属于当前 session 的 todos。",
        failure_description="action、title 不合法时返回结构化失败。",
    )
)


def list_tool_names() -> tuple[str, ...]:
    return tool_registry.names()
