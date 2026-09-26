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


class UsuarioBase(BaseModel):
    nombre: str = Field(min_length=2, max_length=150)
    correo: str = Field(min_length=3, max_length=254)
    tipo: TipoUsuario

    @field_validator("nombre")
    @classmethod
    def normalizar_nombre(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("correo")
    @classmethod
    def normalizar_correo(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized.count("@") != 1 or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Debe ser un correo válido")
        return normalized


class UsuarioCreate(UsuarioBase):
    contrasena: str = Field(min_length=8, max_length=72)
    telefono: str | None = Field(default=None, max_length=30)
    colegiatura: str | None = Field(default=None, max_length=50)
    especialidad: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_veterinarian_profile(self) -> Self:
        if self.tipo == TipoUsuario.VETERINARIO and not self.colegiatura:
            raise ValueError("La colegiatura es obligatoria para un veterinario")
        return self


class UsuarioUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=150)
    correo: EmailStr | None = None
    contrasena: str | None = Field(default=None, min_length=8, max_length=72)
    tipo: TipoUsuario | None = None
    telefono: str | None = Field(default=None, max_length=30)
    colegiatura: str | None = Field(default=None, max_length=50)
    especialidad: str | None = Field(default=None, max_length=100)

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


class UsuarioRead(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telefono: str | None = None
    colegiatura: str | None = None
    especialidad: str | None = None


class UsuarioLogin(BaseModel):
    correo: EmailStr
    contrasena: str
