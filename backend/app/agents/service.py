import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from app.core.config import Settings
from app.core.errors import AppError
from app.core.llm_provider_state import runtime_llm_provider_state, validate_openai_config
from app.llm.base import LLMProvider
from app.llm.mock import MockLLMProvider
from app.llm.openai import OpenAICompatibleProvider
from app.models import Message, MessageRole, SessionRecord, ToolCall, ToolCallStatus
from app.schemas.chat import ChatResponse, MessageRead, ToolCallRead
from app.services.roles import get_role
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
    role_id: str | None = None,
) -> list[dict[str, str]]:
    recent = db.exec(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    ).all()
    role = get_role(role_id)
    return [
        {"role": "system", "content": role.system_prompt},
        *[
            {"role": message.role.value, "content": message.content}
            for message in reversed(recent)
        ],
    ]


def normalize_provider_name(provider_name: str | None = None) -> str:
    return (provider_name or runtime_llm_provider_state.provider).strip().lower()


def get_llm_provider(settings: Settings, provider_name: str | None = None) -> LLMProvider:
    normalized_provider = normalize_provider_name(provider_name)
    if normalized_provider == "mock":
        return MockLLMProvider()
    if normalized_provider == "openai":
        validate_openai_config(settings)
        return OpenAICompatibleProvider(settings)
    raise AppError(
        code="LLM_PROVIDER_UNSUPPORTED",
        message=f"当前版本尚未支持 LLM Provider：{normalized_provider}。",
        status_code=503,
    )


def is_mode_status_question(content: str) -> bool:
    normalized = content.strip().replace(" ", "")
    return any(
        keyword in normalized
        for keyword in (
            "现在是什么模式",
            "当前是什么模式",
            "现在用的什么模式",
            "当前用的什么模式",
            "现在是哪种模式",
            "当前是哪种模式",
            "模型模式是什么",
            "现在是什么模型模式",
            "当前是什么模型模式",
        )
    )


def build_mode_status_reply(provider_name: str) -> str:
    if provider_name == "mock":
        return (
            "当前是 **Mock 演示模式**。普通问答由本地 Mock 规则处理；"
            "时间、计算器和待办工具调用都是本地模拟演示，不会请求真实模型 API。"
        )
    if provider_name == "openai":
        return (
            "当前是 **真实接口模式**（DeepSeek / OpenAI-compatible）。"
            "普通聊天会请求真实模型；时间、计算器和待办工具请切回 Mock 演示模式使用。"
        )
    return f"当前模式未知：{provider_name}。"


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
        provider_name: str | None = None,
        user_message: Message | None = None,
    ) -> ChatResponse:
        normalized_provider = normalize_provider_name(provider_name)
        if user_message is None:
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

        tool_calls: list[ToolCall] = []
        if is_mode_status_question(content):
            assistant_content = build_mode_status_reply(normalized_provider)
        else:
            provider = get_llm_provider(self.settings, normalized_provider)
            context = build_context(
                db,
                session_record.id,
                self.settings.max_context_messages,
                session_record.role_id,
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

            requested_tool_calls = llm_result.normalized_tool_calls()
            if requested_tool_calls:
                for sequence, requested_call in enumerate(requested_tool_calls, 1):
                    tool_call = self._execute_tool(
                        db=db,
                        session_id=session_record.id,
                        name=requested_call.name,
                        arguments=requested_call.arguments,
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
                            "sequence": sequence,
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
                    session_record.role_id,
                )
                try:
                    result_payloads = [
                        self._tool_result_payload(item) for item in tool_calls
                    ]
                    complete_many = getattr(
                        provider,
                        "complete_with_tool_results",
                        None,
                    )
                    if callable(complete_many):
                        assistant_content = complete_many(context, result_payloads)
                    else:
                        last_call = tool_calls[-1]
                        assistant_content = provider.complete_with_tool_result(
                            context,
                            last_call.tool_name,
                            result_payloads[-1],
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


