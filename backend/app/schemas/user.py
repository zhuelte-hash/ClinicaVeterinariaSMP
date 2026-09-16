from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.models.user import TipoUsuario


<<<<<<< Updated upstream
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str | None = None
=======
class UsuarioBase(BaseModel):
    nombre: str = Field(min_length=2, max_length=150)
    correo: EmailStr
    tipo: TipoUsuario

    @field_validator("nombre")
    @classmethod
    def normalizar_nombre(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("correo")
    @classmethod
    def normalizar_correo(cls, value: EmailStr) -> str:
        return str(value).lower()
>>>>>>> Stashed changes


class UsuarioCreate(UsuarioBase):
    contrasena: str = Field(min_length=8, max_length=72)


<<<<<<< Updated upstream
class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = None
    full_name: str | None = None
    password: str | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None
=======
class UsuarioUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=150)
    correo: EmailStr | None = None
    contrasena: str | None = Field(default=None, min_length=8, max_length=72)
    tipo: TipoUsuario | None = None

    @field_validator("nombre")
    @classmethod
    def normalizar_nombre(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value is not None else None

    @field_validator("correo")
    @classmethod
    def normalizar_correo(cls, value: EmailStr | None) -> str | None:
        return str(value).lower() if value is not None else None

    @model_validator(mode="after")
    def rechazar_nulos_explicitos(self) -> Self:
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} no puede ser nulo")
        return self
>>>>>>> Stashed changes


class UsuarioRead(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
<<<<<<< Updated upstream
    is_active: bool
    is_superuser: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
=======


class UsuarioLogin(BaseModel):
    correo: EmailStr
    contrasena: str
>>>>>>> Stashed changes
