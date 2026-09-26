import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.user import TipoUsuario


class AdminProductRead(BaseModel):
    id: int
    sku: str
    nombre: str
    precio_venta: Decimal
    stock_actual: int
    stock_minimo: int
    activo: bool
    imagen_url: str
    categoria_id: int
    categoria_nombre: str


class AdminProductUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=2, max_length=50)
    nombre: str | None = Field(default=None, min_length=2, max_length=150)
    precio_venta: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    stock_minimo: int | None = Field(default=None, ge=0)
    imagen_url: str | None = Field(default=None, min_length=1, max_length=500)


class AdminProductCreate(BaseModel):
    categoria_id: int
    proveedor_id: int
    sku: str = Field(min_length=2, max_length=50)
    nombre: str = Field(min_length=2, max_length=150)
    precio_venta: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    stock_actual: int = Field(ge=0)
    stock_minimo: int = Field(default=0, ge=0)
    imagen_url: str = Field(default="/logo.png", max_length=500)


class AdminCatalogOption(BaseModel):
    id: int
    nombre: str


class AdminProductCatalog(BaseModel):
    categorias: list[AdminCatalogOption]
    proveedores: list[AdminCatalogOption]


class AdminAppointmentRead(BaseModel):
    id: int
    fecha_hora_programada: datetime.datetime
    estado: str
    cliente_nombre: str
    mascota_nombre: str
    servicio_nombre: str
    veterinario_nombre: str | None


class AdminSaleRead(BaseModel):
    id: int
    codigo_orden: str
    fecha_emision: datetime.datetime
    cajero_nombre: str
    cliente_nombre: str | None
    total: Decimal
    medio_pago: str | None


class AdminSalesDayRead(BaseModel):
    fecha: datetime.date
    total: Decimal
    ventas: list[AdminSaleRead]


class RolePermissionRead(BaseModel):
    rol: TipoUsuario
    modulo: str
    puede_ver: bool
    puede_crear: bool
    puede_editar: bool
    puede_eliminar: bool
    puede_aprobar: bool

    model_config = ConfigDict(from_attributes=True)


class RolePermissionUpdate(BaseModel):
    puede_ver: bool = False
    puede_crear: bool = False
    puede_editar: bool = False
    puede_eliminar: bool = False
    puede_aprobar: bool = False

    @model_validator(mode="after")
    def actions_require_view(self):
        if any((self.puede_crear, self.puede_editar, self.puede_eliminar, self.puede_aprobar)):
            self.puede_ver = True
        return self
