from dataclasses import dataclass

from app.core.errors import AppError


DEFAULT_ROLE_ID = "general"


@dataclass(frozen=True)
class ChatbotRole:
    role_id: str
    name: str
    description: str
    system_prompt: str
    icon: str
    color: str


PRESET_ROLES: tuple[ChatbotRole, ...] = (
    ChatbotRole(
        role_id="general",
        name="通用助手",
        description="适合日常问答和任务处理。",
        system_prompt=(
            "你是通用助手，适合日常问答和任务处理。回答要清晰、友好、直接，"
            "在需要时主动拆解步骤并给出可执行建议。"
        ),
        icon="TA",
        color="#6d5bd0",
    ),
    ChatbotRole(
        role_id="code",
        name="代码助手",
        description="更关注代码解释、调试和工程建议。",
        system_prompt=(
            "你是代码助手，更关注代码解释、调试和工程建议。回答时优先说明问题原因、"
            "修改思路、关键代码和验证方式。"
        ),
        icon="</>",
        color="#2563eb",
    ),
    ChatbotRole(
        role_id="writing",
        name="写作助手",
        description="更关注表达优化、结构整理和润色。",
        system_prompt=(
            "你是写作助手，更关注表达优化、结构整理和润色。回答时帮助用户梳理观点、"
            "优化措辞、调整语气，并给出更自然的表达版本。"
        ),
        icon="Aa",
        color="#b45309",
    ),
    ChatbotRole(
        role_id="interview",
        name="面试助手",
        description="更关注面试题讲解、项目复盘和回答组织。",
        system_prompt=(
            "你是面试助手，更关注面试题讲解、项目复盘和回答组织。回答时使用结构化框架，"
            "突出背景、思路、取舍、结果和可复盘的经验。"
        ),
        icon="QA",
        color="#0f766e",
    ),
)

_ROLE_MAP = {role.role_id: role for role in PRESET_ROLES}


def list_roles() -> list[ChatbotRole]:
    return list(PRESET_ROLES)


def get_role(role_id: str | None) -> ChatbotRole:
    normalized = (role_id or DEFAULT_ROLE_ID).strip().lower()
    role = _ROLE_MAP.get(normalized)
    if role is None:
        raise AppError(
            code="ROLE_NOT_FOUND",
            message="助手角色不存在。",
            status_code=422,
            details={"role_id": role_id},
        )
    return role


def validate_role_id(role_id: str | None) -> str:
    return get_role(role_id).role_id
