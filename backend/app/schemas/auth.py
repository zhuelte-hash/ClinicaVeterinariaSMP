from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator

from app.schemas.user import UsuarioRead


class LoginRequest(BaseModel):
    identifier: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    password: str = Field(min_length=1)


class ClientRegisterRequest(BaseModel):
    nombre: str = Field(min_length=2, max_length=150)
    correo: EmailStr
    password: str = Field(min_length=8, max_length=72)
    telefono: str | None = Field(default=None, max_length=30)

    @field_validator("nombre")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("correo")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).lower()

    @field_validator("telefono")
    @classmethod
    def normalize_phone(cls, value: str | None) -> str | None:
        normalized = value.strip() if value is not None else None
        return normalized or None


class TokenPayload(BaseModel):
    user_id: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UsuarioRead
