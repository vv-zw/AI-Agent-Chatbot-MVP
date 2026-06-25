import ast
import operator
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as datetime_timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlmodel import Session, select

from app.models import Todo


class ToolNotFoundError(Exception):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Tool is not registered: {name}")


class ToolArgumentError(Exception):
    def __init__(self, details: Any) -> None:
        self.details = details
        super().__init__("Tool arguments are invalid.")


class ToolExecutionError(Exception):
    pass


@dataclass(frozen=True)
class ToolContext:
    db: Session
    session_id: UUID


class CurrentTimeInput(BaseModel):
    timezone: str = "Asia/Shanghai"


class CalculatorInput(BaseModel):
    expression: str = Field(min_length=1, max_length=200)

    @field_validator("expression")
    @classmethod
    def validate_expression_characters(cls, value: str) -> str:
        expression = value.strip()
        if not re.fullmatch(r"[0-9().+\-*/\s]+", expression):
            raise ValueError("表达式只能包含数字、括号、小数点、空格和加减乘除符号。")
        return expression


class TodoInput(BaseModel):
    action: Literal["create", "list"]
    title: str | None = Field(default=None, max_length=500)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        title = value.strip()
        if not title:
            raise ValueError("待办标题不能为空。")
        return title


ToolHandler = Callable[[ToolContext, BaseModel], dict[str, Any]]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    input_model: type[BaseModel]
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        self._tools[definition.name] = definition

    def names(self) -> tuple[str, ...]:
        return tuple(self._tools)

    def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> dict[str, Any]:
        definition = self._tools.get(name)
        if definition is None:
            raise ToolNotFoundError(name)
        try:
            validated = definition.input_model.model_validate(arguments)
        except ValidationError as exc:
            raise ToolArgumentError(exc.errors(include_url=False)) from exc
        try:
            return definition.handler(context, validated)
        except ToolArgumentError:
            raise
        except Exception as exc:
            raise ToolExecutionError(str(exc) or "工具执行失败。") from exc


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
    raise ToolArgumentError({"reason": "表达式包含不支持的语法。"})


def get_current_time(_: ToolContext, payload: BaseModel) -> dict[str, Any]:
    data = CurrentTimeInput.model_validate(payload)
    try:
        timezone = ZoneInfo(data.timezone)
    except ZoneInfoNotFoundError as exc:
        if data.timezone != "Asia/Shanghai":
            raise ToolArgumentError(
                {"timezone": data.timezone, "reason": "未知时区。"}
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
        raise ToolArgumentError({"reason": "表达式格式不正确。"}) from exc
    except ZeroDivisionError as exc:
        raise ToolArgumentError({"reason": "除数不能为零。"}) from exc
    normalized = format(value.normalize(), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return {"expression": data.expression, "value": normalized or "0"}


def todo_tool(context: ToolContext, payload: BaseModel) -> dict[str, Any]:
    data = TodoInput.model_validate(payload)
    if data.action == "create":
        if data.title is None:
            raise ToolArgumentError({"title": "创建待办时必须提供标题。"})
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
tool_registry.register(ToolDefinition("get_current_time", CurrentTimeInput, get_current_time))
tool_registry.register(ToolDefinition("calculator", CalculatorInput, calculator))
tool_registry.register(ToolDefinition("todo_tool", TodoInput, todo_tool))


def list_tool_names() -> tuple[str, ...]:
    return tool_registry.names()