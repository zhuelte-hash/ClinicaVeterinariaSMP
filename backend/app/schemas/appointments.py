import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.clinic import EstadoCita


class PetCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    especie: str = Field(min_length=2, max_length=80)
    raza: str | None = Field(default=None, max_length=100)

    @field_validator("nombre", "especie", "raza")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        normalized = " ".join(value.split()) if value is not None else None
        return normalized or None


class PetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    especie: str
    raza: str | None


class ServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    descripcion: str | None
    precio_referencial: Decimal
    duracion_estimada_min: int


class AppointmentCreate(BaseModel):
    mascota_id: int
    servicio_id: int
    fecha_hora_programada: datetime.datetime
    motivo: str | None = Field(default=None, max_length=500)
    es_urgente: bool = False

    @field_validator("fecha_hora_programada")
    @classmethod
    def require_timezone(cls, value: datetime.datetime) -> datetime.datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("La fecha debe incluir zona horaria")
        return value

    @field_validator("motivo")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        normalized = " ".join(value.split()) if value is not None else None
        return normalized or None


class AppointmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha_hora_programada: datetime.datetime
    estado: EstadoCita
    es_urgente: bool
    motivo: str | None
    fecha_creacion: datetime.datetime
    mascota: PetRead
    servicio: ServiceRead
