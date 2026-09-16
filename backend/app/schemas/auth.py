from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    identifier: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    password: str = Field(min_length=1)


class TokenPayload(BaseModel):
    user_id: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
