from enum import StrEnum

from pydantic import BaseModel


class UserRoleName(StrEnum):
    admin = "admin"
    operator = "operator"
    observer = "observer"


class LoginRequest(BaseModel):
    login: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUser(BaseModel):
    id: int
    login: str
    role: UserRoleName


class TokenPayload(BaseModel):
    sub: str
    role: UserRoleName
