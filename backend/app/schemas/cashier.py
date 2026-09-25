from decimal import Decimal

import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.clinic import EstadoPago


class CajaAbrir(BaseModel):
    fondo_inicial: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class CajaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cajero_id: int
    fondo_inicial: Decimal
    total_ingresos_validados: Decimal
    estado_caja: str


class OrdenCajaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo_orden: str
    monto_total: Decimal
    estado_pago: EstadoPago
    medio_pago: str | None


class CajaResumen(BaseModel):
    caja: CajaRead | None
    ordenes_pendientes: int
    ordenes_validadas: int
    ordenes_recientes: list[OrdenCajaRead]


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


class VentaCreate(BaseModel):
    cliente_id: int
    medio_pago: Literal["efectivo", "yape", "plin", "tarjeta"]
    items: list[VentaItemCreate] = Field(min_length=1, max_length=50)


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
    cliente_nombre: str
    cliente_correo: str
    cajero_nombre: str
    medio_pago: str
    subtotal: Decimal
    igv: Decimal
    total: Decimal
    detalles: list[BoletaDetalleRead]
