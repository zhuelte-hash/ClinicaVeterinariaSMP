import datetime as dt
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Money = Decimal
PaymentMethod = Literal["efectivo", "yape", "plin", "tarjeta", "transferencia"]


class TextModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class Reason(TextModel):
    motivo: str = Field(min_length=3, max_length=500)


class DayHours(TextModel):
    dia: int = Field(ge=0, le=6)
    cerrado: bool = False
    inicio: dt.time = dt.time(8)
    fin: dt.time = dt.time(20)
    descanso_inicio: dt.time | None = dt.time(12)
    descanso_fin: dt.time | None = dt.time(13)

    @model_validator(mode="after")
    def valid_hours(self):
        if not self.cerrado and self.fin <= self.inicio:
            raise ValueError("La hora final debe ser posterior al inicio")
        if (self.descanso_inicio is None) != (self.descanso_fin is None) or (self.descanso_inicio and self.descanso_fin <= self.descanso_inicio):
            raise ValueError("Completa un intervalo de descanso válido o elimina ambos extremos")
        return self


class ExceptionHours(DayHours):
    fecha: dt.date
    motivo: str = Field(min_length=3, max_length=200)


class GalleryPhoto(TextModel):
    url: str = Field(pattern=r"^/uploads/instalaciones/[a-f0-9]+\.(jpg|png|webp)$")
    titulo: str = Field(min_length=3, max_length=150)


class ClinicPolicy(TextModel):
    horarios: list[DayHours] = Field(default_factory=lambda: [DayHours(dia=i, cerrado=i == 6) for i in range(7)], min_length=7, max_length=7)
    excepciones: list[ExceptionHours] = Field(default_factory=list, max_length=366)
    galeria: list[GalleryPhoto] = Field(default_factory=list, max_length=50)
    horas_cancelacion: int = Field(default=4, ge=0, le=168)
    horas_reprogramacion: int = Field(default=4, ge=0, le=168)
    dias_alerta_vencimiento: int = Field(default=30, ge=1, le=365)
    dias_recordatorio_vacuna: int = Field(default=3, ge=0, le=30)

    @model_validator(mode="after")
    def unique_days(self):
        if len({day.dia for day in self.horarios}) != 7 or len({day.fecha for day in self.excepciones}) != len(self.excepciones):
            raise ValueError("No repitas días o fechas de excepción")
        return self


class ServiceWrite(TextModel):
    codigo: str = Field(min_length=2, max_length=50, pattern=r"^[a-z0-9-]+$")
    nombre: str = Field(min_length=2, max_length=150)
    descripcion: str = Field(min_length=3, max_length=5000)
    precio_referencial: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    duracion_estimada_min: int = Field(ge=5, le=1440)
    activo: bool = True
    tipo: Literal["medica", "estetica"] = "medica"
    tipo_medico: Literal["consulta_general", "cirugia", "vacunacion", "desparasitacion", "laboratorio_e_imagen"] = "consulta_general"


class RescheduleRequest(Reason):
    fecha_propuesta: dt.datetime
    canal: Literal["web", "whatsapp"] = "web"

    @field_validator("fecha_propuesta")
    @classmethod
    def timezone(cls, value):
        if value.tzinfo is None:
            raise ValueError("Incluye la zona horaria")
        return value


class PrivateNotes(TextModel):
    notas: str = Field(max_length=10000)


class ReferralCreate(Reason):
    receptor_id: int = Field(ge=1)


class ReferralAnswer(TextModel):
    aceptar: bool
    respuesta: str = Field(min_length=3, max_length=5000)


class BranchWrite(TextModel):
    nombre: str = Field(min_length=2, max_length=150)
    direccion: str = Field(default="", max_length=250)
    telefono: str = Field(default="", max_length=30)
    activa: bool = True


class UnitWrite(TextModel):
    codigo: str = Field(min_length=1, max_length=15, pattern=r"^[a-z0-9]+$")
    nombre: str = Field(min_length=2, max_length=80)
    dimension: Literal["conteo", "masa", "volumen"]
    factor_base: Decimal = Field(gt=0, max_digits=14, decimal_places=6)
    fraccionable: bool = False


class ReceiveLine(TextModel):
    producto_id: int
    cantidad: Decimal = Field(gt=0, max_digits=14, decimal_places=3)
    costo_unitario: Decimal = Field(ge=0, max_digits=14, decimal_places=4)
    lote: str = Field(min_length=1, max_length=100)
    vencimiento: dt.date | None = None
    unidad: str | None = Field(default=None, max_length=15)


class ReceivePurchase(TextModel):
    proveedor_id: int
    documento: str = Field(min_length=3, max_length=100)
    detalles: list[ReceiveLine] = Field(min_length=1, max_length=200)


class ExpenseWrite(TextModel):
    categoria: str = Field(min_length=2, max_length=80)
    concepto: str = Field(min_length=3, max_length=500)
    monto: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    fecha: dt.date


class DiscountRequest(Reason):
    monto: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    cliente_id: int | None = None


class OrderItem(TextModel):
    producto_id: int | None = None
    servicio_id: int | None = None
    cantidad: Decimal = Field(gt=0, le=10000, max_digits=14, decimal_places=3)

    @model_validator(mode="after")
    def one_type(self):
        if (self.producto_id is None) == (self.servicio_id is None):
            raise ValueError("Indica un producto o servicio")
        return self


class PendingOrderCreate(TextModel):
    cliente_id: int
    detalles: list[OrderItem] = Field(min_length=1, max_length=50)
    proceso_id: int | None = None
    autorizacion_id: int | None = None
    clave_idempotencia: str = Field(min_length=8, max_length=80)


class InstallmentWrite(TextModel):
    monto: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    medio: PaymentMethod
    codigo_operacion: str | None = Field(default=None, max_length=100)
    canal: Literal["caja", "web", "whatsapp"] = "caja"
    clave_idempotencia: str = Field(min_length=8, max_length=150)


class TemplateWrite(TextModel):
    nombre_proveedor: str = Field(default="", max_length=150, pattern=r"^[a-z0-9_]*$")
    idioma: str = Field(default="es_PE", pattern=r"^[a-z]{2}(_[A-Z]{2})?$")
    contenido: str = Field(min_length=3, max_length=4000)
    variables: list[str] = Field(default_factory=list, max_length=15)
    activa: bool = True


class SurveyAnswer(TextModel):
    valoracion: int = Field(ge=1, le=5)
    comentario: str = Field(default="", max_length=2000)
