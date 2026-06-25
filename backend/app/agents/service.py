import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from app.core.config import Settings
from app.core.errors import AppError
from app.llm.base import LLMProvider
from app.llm.mock import MockLLMProvider
from app.models import Message, MessageRole, SessionRecord, ToolCall, ToolCallStatus
from app.schemas.chat import ChatResponse, MessageRead, ToolCallRead
from app.tools.registry import (
    ToolArgumentError,
    ToolContext,
    ToolExecutionError,
    ToolNotFoundError,
    ToolRegistry,
    tool_registry,
)


def build_context(
    db: Session,
    session_id: UUID,
    limit: int,
) -> list[dict[str, str]]:
    recent = db.exec(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    ).all()
    return [
        {"role": message.role.value, "content": message.content}
        for message in reversed(recent)
    ]


def get_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "mock":
        return MockLLMProvider()
    if not settings.openai_api_key:
        raise AppError(
            code="LLM_CONFIGURATION_ERROR",
            message="当前 LLM Provider 缺少 API Key，请配置后重试。",
            status_code=503,
        )
    raise AppError(
        code="LLM_PROVIDER_UNSUPPORTED",
        message=f"当前版本尚未支持 LLM Provider：{settings.llm_provider}。",
        status_code=503,
    )


class AgentService:
    def __init__(
        self,
        settings: Settings,
        registry: ToolRegistry = tool_registry,
    ) -> None:
        self.settings = settings
        self.registry = registry

    def run(
        self,
        db: Session,
        session_record: SessionRecord,
        content: str,
    ) -> ChatResponse:
        provider = get_llm_provider(self.settings)
        user_message = Message(
            session_id=session_record.id,
            role=MessageRole.USER,
            content=content,
        )
        session_record.updated_at = datetime.now(timezone.utc)
        if session_record.title == "New conversation":
            session_record.title = content[:40]
        db.add(user_message)
        db.add(session_record)
        db.flush()

        context = build_context(
            db,
            session_record.id,
            self.settings.max_context_messages,
        )
        try:
            llm_result = provider.complete(context)
        except AppError:
            raise
        except Exception as exc:
            raise AppError(
                code="LLM_CALL_FAILED",
                message="LLM 调用失败，请稍后重试。",
                status_code=502,
            ) from exc

        tool_calls: list[ToolCall] = []
        if llm_result.tool_call is not None:
            tool_call = self._execute_tool(
                db=db,
                session_id=session_record.id,
                name=llm_result.tool_call.name,
                arguments=llm_result.tool_call.arguments,
            )
            tool_calls.append(tool_call)
            tool_message = Message(
                session_id=session_record.id,
                role=MessageRole.TOOL,
                content=self._build_tool_message_content(tool_call),
                metadata_json={
                    "tool_call_id": str(tool_call.id),
                    "tool_name": tool_call.tool_name,
                    "status": tool_call.status.value,
                },
            )
            db.add(tool_message)
            db.flush()
            tool_call.tool_message_id = tool_message.id
            db.add(tool_call)

            context = build_context(
                db,
                session_record.id,
                self.settings.max_context_messages,
            )
            try:
                assistant_content = provider.complete_with_tool_result(
                    context,
                    tool_call.tool_name,
                    self._tool_result_payload(tool_call),
                )
            except Exception as exc:
                raise AppError(
                    code="LLM_CALL_FAILED",
                    message="LLM 生成工具结果回复时失败，请稍后重试。",
                    status_code=502,
                ) from exc
        else:
            assistant_content = llm_result.content or ""

        if not assistant_content.strip():
            raise AppError(
                code="LLM_EMPTY_RESPONSE",
                message="LLM 未返回有效内容，请重试。",
                status_code=502,
            )

        assistant_message = Message(
            session_id=session_record.id,
            role=MessageRole.ASSISTANT,
            content=assistant_content.strip(),
        )
        db.add(assistant_message)
        db.flush()
        for tool_call in tool_calls:
            tool_call.assistant_message_id = assistant_message.id
            db.add(tool_call)

        db.commit()
        db.refresh(user_message)
        db.refresh(assistant_message)
        for tool_call in tool_calls:
            db.refresh(tool_call)

        return ChatResponse(
            user_message=MessageRead.model_validate(user_message),
            assistant_message=MessageRead.model_validate(assistant_message),
            tool_calls=[ToolCallRead.model_validate(item) for item in tool_calls],
        )

    def _execute_tool(
        self,
        db: Session,
        session_id: UUID,
        name: Any,
        arguments: Any,
    ) -> ToolCall:
        normalized_name = (
            name.strip()
            if isinstance(name, str) and name.strip()
            else "<invalid>"
        )
        normalized_arguments = (
            arguments
            if isinstance(arguments, dict)
            else {"_raw": arguments}
        )
        tool_call = ToolCall(
            session_id=session_id,
            tool_name=normalized_name,
            arguments=normalized_arguments,
        )
        db.add(tool_call)
        db.flush()
        try:
            result = self.registry.execute(
                normalized_name,
                arguments,
                ToolContext(db=db, session_id=session_id),
            )
        except ToolNotFoundError as exc:
            self._fail_tool_call(
                db,
                tool_call,
                "TOOL_NOT_FOUND",
                f"工具未注册或未启用：{exc.name}",
            )
        except ToolArgumentError as exc:
            self._fail_tool_call(
                db,
                tool_call,
                "TOOL_ARGUMENT_INVALID",
                str(exc),
                details=exc.details,
            )
        except ToolExecutionError as exc:
            self._fail_tool_call(
                db,
                tool_call,
                "TOOL_EXECUTION_FAILED",
                str(exc),
            )
        else:
            tool_call.result = result
            tool_call.status = ToolCallStatus.SUCCEEDED
            tool_call.completed_at = datetime.now(timezone.utc)
            db.add(tool_call)
            db.flush()
        return tool_call

    @staticmethod
    def _fail_tool_call(
        db: Session,
        tool_call: ToolCall,
        error_code: str,
        error_message: str,
        details: Any | None = None,
    ) -> None:
        tool_call.status = ToolCallStatus.FAILED
        tool_call.error_code = error_code
        tool_call.error_message = error_message[:1000]
        if details is not None:
            tool_call.result = {"error": {"code": error_code, "details": details}}
        tool_call.completed_at = datetime.now(timezone.utc)
        db.add(tool_call)
        db.flush()

    @staticmethod
    def _tool_result_payload(tool_call: ToolCall) -> dict[str, Any]:
        return {
            "status": tool_call.status.value,
            "tool_name": tool_call.tool_name,
            "arguments": tool_call.arguments,
            "result": tool_call.result,
            "error_code": tool_call.error_code,
            "error_message": tool_call.error_message,
        }

    @classmethod
    def _build_tool_message_content(cls, tool_call: ToolCall) -> str:
        return json.dumps(
            cls._tool_result_payload(tool_call),
            ensure_ascii=False,
            separators=(",", ":"),
        )
