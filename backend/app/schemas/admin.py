import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.clinic import EstadoCita
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
    categoria_id: int | None = None
    sku: str | None = Field(default=None, min_length=2, max_length=50)
    nombre: str | None = Field(default=None, min_length=2, max_length=150)
    precio_venta: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    stock_minimo: int | None = Field(default=None, ge=0)
    imagen_url: str | None = Field(default=None, min_length=1, max_length=500)


class InventoryStockUpdate(BaseModel):
    stock_actual: int = Field(ge=0)


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


class AdminCategoryRead(BaseModel):
    id: int
    nombre: str
    productos: int = 0


class AdminCategoryCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str = Field(min_length=2, max_length=100)


class AdminCategoryUpdate(AdminCategoryCreate):
    pass


class AdminClientRead(BaseModel):
    id: int
    nombre: str
    correo: str
    telefono: str | None
    direccion: str | None
    mascotas: int
    citas: int
    ultima_cita: datetime.datetime | None


class AdminAppointmentRead(BaseModel):
    id: int
    fecha_hora_programada: datetime.datetime
    estado: str
    cliente_nombre: str
    mascota_nombre: str
    servicio_nombre: str
    veterinario_nombre: str | None
    veterinario_id: int | None
    fecha_hora_fin_programada: datetime.datetime
    nota_coordinacion: str | None


class AdminNotificationRead(BaseModel):
    id: int
    usuario_id: int
    usuario_nombre: str
    tipo: str
    titulo: str
    mensaje: str
    leida: bool
    fecha_creacion: datetime.datetime


class AdminNotificationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    usuario_id: int
    tipo: str = Field(min_length=1, max_length=50)
    titulo: str = Field(min_length=1, max_length=150)
    mensaje: str = Field(min_length=1, max_length=500)


class AdminSettingsRead(BaseModel):
    nombre: str
    correo: str
    telefono: str
    direccion: str
    umbral_stock_bajo: int
    recordatorios_citas: bool
    alertas_stock: bool


class AdminSettingsUpdate(AdminSettingsRead):
    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str = Field(min_length=2, max_length=150)
    correo: EmailStr
    telefono: str = Field(max_length=50)
    direccion: str = Field(max_length=250)
    umbral_stock_bajo: int = Field(ge=0, le=1000000)


class AdminAppointmentUpdate(BaseModel):
    estado: EstadoCita | None = None
    fecha_hora_programada: datetime.datetime | None = None
    veterinario_id: int | None = None
    nota_coordinacion: str | None = Field(default=None, max_length=500)

    @field_validator("fecha_hora_programada")
    @classmethod
    def require_timezone(cls, value: datetime.datetime | None) -> datetime.datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("La fecha debe incluir zona horaria")
        return value

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        for field in ("estado", "fecha_hora_programada"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} no puede ser nulo")
        return self


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
