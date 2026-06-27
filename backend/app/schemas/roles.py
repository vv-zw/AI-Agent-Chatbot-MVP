from pydantic import BaseModel


class RoleRead(BaseModel):
    role_id: str
    name: str
    description: str
    system_prompt: str
    icon: str | None = None
    color: str | None = None
