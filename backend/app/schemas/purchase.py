from decimal import Decimal
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DatosCompra(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    nombreCompleto: str = Field(min_length=3, max_length=150)
    celular: str = Field(pattern=r"^[0-9]{9,15}$")
    correo: str = Field(default="", max_length=254)
    tipoEntrega: Literal["Recojo en clínica", "Delivery"]
    direccion: str = Field(default="", max_length=255)
    referencia: str = Field(default="", max_length=255)
    tipoComprobante: Literal["Boleta", "Factura"] = "Boleta"
    dni: str = Field(default="", pattern=r"^([0-9]{8})?$")
    ruc: str = Field(default="", pattern=r"^([0-9]{11})?$")
    razonSocial: str = Field(default="", max_length=180)

    @model_validator(mode="after")
    def validate_customer(self):
        if self.tipoEntrega == "Delivery" and len(self.direccion) < 5:
            raise ValueError("La dirección es obligatoria para delivery")
        if self.tipoComprobante == "Boleta" and not self.dni:
            raise ValueError("Ingresa el DNI")
        if self.tipoComprobante == "Factura" and (not self.ruc or len(self.razonSocial) < 3):
            raise ValueError("Ingresa RUC y razón social")
        return self


class ItemPedido(BaseModel):
    model_config = ConfigDict(extra="forbid")
    producto_id: int = Field(gt=0)
    cantidad: int = Field(ge=1, le=100)


class PedidoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    clave_idempotencia: UUID
    cliente: DatosCompra
    items: list[ItemPedido] = Field(min_length=1, max_length=50)
    metodo_pago: Literal["yape", "plin"]
    numero_operacion: str = Field(min_length=4, max_length=100)
    observaciones: str = Field(default="", max_length=1000)
    total_esperado: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class RevisionPedido(BaseModel):
    accion: Literal["APROBAR", "RECHAZAR"]
    motivo: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def validate_reason(self):
        self.motivo = self.motivo.strip()
        if self.accion == "RECHAZAR" and len(self.motivo) < 3:
            raise ValueError("Indica el motivo del rechazo (mínimo 3 caracteres)")
        return self


class DetallePedidoRead(BaseModel):
    producto_id: int
    nombre_producto: str
    imagen_url: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal


class PedidoRead(BaseModel):
    id: int
    codigo_pedido: str
    cliente_id: int
    fecha_pedido: datetime
    subtotal: Decimal
    descuento: Decimal
    costo_delivery: Decimal
    total: Decimal
    metodo_pago: str
    estado_pedido: Literal["PENDIENTE", "APROBADO", "RECHAZADO", "CANCELADO"]
    estado_pago: Literal["PAGO_ENVIADO", "VALIDADO", "RECHAZADO", "CANCELADO"]
    datos_cliente: DatosCompra
    numero_operacion: str
    observaciones: str
    comprobante_pago: str
    comprobante_tipo: str
    fecha_revision: datetime | None
    usuario_revisor_id: int | None
    motivo_rechazo: str | None
    venta_id: int | None
    detalles: list[DetallePedidoRead]
