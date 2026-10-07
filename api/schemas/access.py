from pydantic import BaseModel


class AccessResponse(BaseModel):
    username: str
    role: str
    allowed_domains: list[str]
