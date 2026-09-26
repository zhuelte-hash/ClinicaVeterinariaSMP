import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.clinic import EstadoCita


class PetCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    especie: str = Field(min_length=2, max_length=80)
    raza: str | None = Field(default=None, max_length=100)
    sexo: str | None = Field(default=None, max_length=20)
    fecha_nacimiento: datetime.date | None = None
    peso_actual: Decimal | None = Field(default=None, ge=0, max_digits=7, decimal_places=2)
    caracteristicas: str | None = Field(default=None, max_length=2000)

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
    sexo: str | None
    fecha_nacimiento: datetime.date | None
    peso_actual: Decimal | None
    caracteristicas: str | None


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
    veterinario_id: int
    fecha_hora_programada: datetime.datetime
    motivo: str | None = Field(default=None, max_length=500)
    es_urgente: bool = False
    telefono_contacto: str | None = Field(default=None, max_length=30)
    preferencia_contacto: str | None = Field(default=None, max_length=20)

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
    fecha_actualizacion: datetime.datetime
    fecha_hora_propuesta: datetime.datetime | None
    telefono_contacto: str | None
    preferencia_contacto: str | None
    nota_coordinacion: str | None
    veterinario_id: int | None
    mascota: PetRead
    servicio: ServiceRead


class AvailabilitySlot(BaseModel):
    fecha_hora: datetime.datetime
    veterinario_id: int
    veterinario_nombre: str


class VeterinarianAppointmentRead(AppointmentRead):
    cliente_id: int
    cliente_nombre: str
    cliente_correo: str


class AppointmentCoordinationUpdate(BaseModel):
    estado: EstadoCita
    fecha_hora_propuesta: datetime.datetime | None = None
    nota_coordinacion: str | None = Field(default=None, max_length=500)

    @field_validator("estado")
    @classmethod
    def require_veterinarian_state(cls, value: EstadoCita) -> EstadoCita:
        allowed = {
            EstadoCita.CONTACTANDO_CLIENTE,
            EstadoCita.ESPERANDO_RESPUESTA,
            EstadoCita.REQUIERE_OTRO_HORARIO,
            EstadoCita.CONFIRMADA,
            EstadoCita.CANCELADA,
            EstadoCita.CLIENTE_NO_RESPONDIO,
            EstadoCita.ATENDIDA,
        }
        if value not in allowed:
            raise ValueError("Estado no permitido para coordinación veterinaria")
        return value

    @field_validator("fecha_hora_propuesta")
    @classmethod
    def proposed_time_requires_timezone(
        cls, value: datetime.datetime | None
    ) -> datetime.datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("La fecha propuesta debe incluir zona horaria")
        return value


class AppointmentSummary(BaseModel):
    pendientes: int
    confirmadas: int
    atendidas: int
    proximas: int


class ScheduleRead(BaseModel):
    id: int
    dia_semana: int
    hora_inicio: datetime.time
    hora_fin: datetime.time
    activo: bool

    model_config = ConfigDict(from_attributes=True)


class ScheduleUpdate(BaseModel):
    dia_semana: int = Field(ge=0, le=5)
    hora_inicio: datetime.time
    hora_fin: datetime.time
    activo: bool = True

    @field_validator("hora_fin")
    @classmethod
    def end_after_start(cls, value: datetime.time, info):
        start = info.data.get("hora_inicio")
        if start is not None and value <= start:
            raise ValueError("La hora final debe ser posterior a la hora inicial")
        return value


class ScheduleBlockCreate(BaseModel):
    fecha_hora_inicio: datetime.datetime
    fecha_hora_fin: datetime.datetime
    motivo: str = Field(min_length=2, max_length=255)

    @field_validator("fecha_hora_inicio", "fecha_hora_fin")
    @classmethod
    def require_timezone(cls, value: datetime.datetime) -> datetime.datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("La fecha debe incluir zona horaria")
        return value


class ScheduleBlockRead(ScheduleBlockCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ClinicalRecordCreate(BaseModel):
    motivo_consulta: str | None = Field(default=None, max_length=5000)
    anamnesis: str | None = Field(default=None, max_length=5000)
    observaciones: str | None = Field(default=None, max_length=5000)
    diagnostico: str | None = Field(default=None, max_length=5000)
    tratamiento: str | None = Field(default=None, max_length=5000)
    peso: Decimal | None = Field(default=None, ge=0, max_digits=7, decimal_places=2)
    temperatura: Decimal | None = Field(default=None, gt=0, max_digits=5, decimal_places=2)
    historial_alergias: str | None = Field(default=None, max_length=5000)
    vacunas: str | None = Field(default=None, max_length=5000)
    desparasitaciones: str | None = Field(default=None, max_length=5000)
    medicamentos: str | None = Field(default=None, max_length=5000)
    procedimientos: str | None = Field(default=None, max_length=5000)
    examenes_resultados: str | None = Field(default=None, max_length=5000)
    proxima_fecha_control: datetime.date | None = None


class ClinicalRecordRead(BaseModel):
    id: int
    cita_id: int | None
    mascota_id: int
    tipo: str
    fecha_inicio: datetime.datetime
    fecha_fin: datetime.datetime | None
    observaciones: str | None
    motivo_consulta: str | None
    anamnesis: str | None
    diagnostico: str | None
    tratamiento: str | None
    peso: Decimal | None
    temperatura: Decimal | None
    historial_alergias: str | None
    vacunas: str | None
    desparasitaciones: str | None
    medicamentos: str | None
    procedimientos: str | None
    examenes_resultados: str | None
    proxima_fecha_control: datetime.date | None
    veterinario_id: int
    veterinario_nombre: str
    servicio_nombre: str


class NotificationRead(BaseModel):
    id: int
    cita_id: int | None
    tipo: str
    titulo: str
    mensaje: str
    leida: bool
    fecha_creacion: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
