from decimal import Decimal

import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.clinic import EstadoPago


class CajaAbrir(BaseModel):
    fondo_inicial: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class CajaCerrar(BaseModel):
    efectivo_contado: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class CajaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cajero_id: int
    fondo_inicial: Decimal
    total_ingresos_validados: Decimal
    estado_caja: str
    fecha_apertura: datetime.datetime
    fecha_cierre: datetime.datetime | None
    efectivo_contado: Decimal | None
    diferencia: Decimal | None


class OrdenCajaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo_orden: str
    monto_total: Decimal
    estado_pago: EstadoPago
    medio_pago: str | None


class PagoPendienteRead(OrdenCajaRead):
    captura_imagen: str | None = None
    codigo_operacion: str | None = None


class PagoRechazar(BaseModel):
    motivo: str = Field(min_length=3, max_length=500)


class CajaResumen(BaseModel):
    caja: CajaRead | None
    ordenes_pendientes: int
    ordenes_validadas: int
    ordenes_recientes: list[OrdenCajaRead]
    ingresos_efectivo: Decimal = Decimal("0.00")
    ingresos_digitales: Decimal = Decimal("0.00")
    efectivo_esperado: Decimal = Decimal("0.00")


class CategoriaCajaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


class ProductoCajaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    nombre: str
    precio_venta: Decimal
    stock_actual: int
    categoria: CategoriaCajaRead


class ServicioCajaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    descripcion: str | None
    precio_referencial: Decimal
    duracion_estimada_min: int


class ClienteCajaRead(BaseModel):
    id: int
    nombre: str
    correo: str
    telefono: str | None


class VentaItemCreate(BaseModel):
    producto_id: int | None = None
    servicio_id: int | None = None
    cantidad: int = Field(ge=1, le=100)

    @model_validator(mode="after")
    def validate_item_type(self):
        if (self.producto_id is None) == (self.servicio_id is None):
            raise ValueError("Debe indicar un producto o un servicio")
        return self


class PagoCreate(BaseModel):
    medio: Literal["efectivo", "yape", "plin", "tarjeta"]
    monto: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class VentaCreate(BaseModel):
    cliente_id: int | None = None
    medio_pago: Literal["efectivo", "yape", "plin", "tarjeta"]
    items: list[VentaItemCreate] = Field(min_length=1, max_length=50)
    clave_idempotencia: str | None = Field(default=None, min_length=8, max_length=80)
    descuento: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    pagos: list[PagoCreate] | None = Field(default=None, min_length=1, max_length=4)
    efectivo_recibido: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    proceso_atencion_id: int | None = None

    @model_validator(mode="after")
    def validate_payments(self):
        if self.pagos:
            if len({payment.medio for payment in self.pagos}) != len(self.pagos):
                raise ValueError("No repitas un medio de pago")
            if self.medio_pago != self.pagos[0].medio:
                raise ValueError("El medio principal debe coincidir con el primer pago")
        return self


class BoletaDetalleRead(BaseModel):
    producto_id: int | None
    servicio_id: int | None
    codigo: str
    tipo: Literal["producto", "servicio"]
    nombre: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal


class BoletaRead(BaseModel):
    orden_id: int
    codigo_orden: str
    serie_correlativo: str
    fecha_emision: datetime.datetime
    cliente_nombre: str | None
    cliente_correo: str | None
    cajero_nombre: str
    medio_pago: str
    subtotal: Decimal
    igv: Decimal
    total: Decimal
    detalles: list[BoletaDetalleRead]
    descuento: Decimal = Decimal("0.00")
    estado: str = "PAGADA"
    pagos: list[PagoCreate] = []
    efectivo_recibido: Decimal | None = None
    vuelto: Decimal = Decimal("0.00")
    proceso_atencion_id: int | None = None


class AtencionCajaRead(BaseModel):
    id: int
    mascota_nombre: str
    servicio_nombre: str
    cliente_id: int
