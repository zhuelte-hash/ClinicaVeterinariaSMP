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
    stock_actual: float
    stock_minimo: float
    activo: bool
    imagen_url: str
    categoria_id: int
    categoria_nombre: str
    proveedor_id: int
    descripcion: str | None = None
    especies: list[str] = Field(default_factory=list)
    unidad_medida: str = "unidad"
    fraccionable: bool = False
    costo_unitario: Decimal = Decimal("0")
    sucursal_id: int = 1


class ProductDescription(BaseModel):
    descripcion: str | None = Field(default=None, max_length=5000)
    especies: list[str] = Field(default_factory=list, max_length=12)
    unidad_medida: str = Field(default="unidad", min_length=1, max_length=15)
    fraccionable: bool = False
    costo_unitario: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=4)

    @field_validator("especies")
    @classmethod
    def normalize_species(cls, values: list[str]) -> list[str]:
        result = list(dict.fromkeys(value.strip().capitalize() for value in values))
        if any(not value or len(value) > 80 for value in result):
            raise ValueError("Cada especie debe contener entre 1 y 80 caracteres")
        return result


class AdminProductUpdate(ProductDescription):
    categoria_id: int | None = None
    proveedor_id: int | None = None
    sku: str | None = Field(default=None, min_length=2, max_length=50)
    nombre: str | None = Field(default=None, min_length=2, max_length=150)
    precio_venta: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    stock_minimo: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=3)
    imagen_url: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def non_null_product_fields(self):
        for field in self.model_fields_set - {"descripcion"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field} no puede ser nulo")
        return self


class InventoryStockUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    stock_actual: Decimal = Field(ge=0, max_digits=14, decimal_places=3)
    motivo: str = Field(min_length=3, max_length=500)
    stock_anterior: Decimal = Field(ge=0, max_digits=14, decimal_places=3)


class AdminProductCreate(ProductDescription):
    categoria_id: int
    proveedor_id: int
    sku: str = Field(min_length=2, max_length=50)
    nombre: str = Field(min_length=2, max_length=150)
    precio_venta: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    stock_actual: Decimal = Field(ge=0, max_digits=14, decimal_places=3)
    stock_minimo: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=3)
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


class SupplierWrite(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    razon_social: str = Field(min_length=2, max_length=180)


class SupplierRead(SupplierWrite):
    id: int
    productos: int = 0


class InventoryAdjustmentRead(BaseModel):
    id: int
    producto_id: int
    producto_nombre: str
    usuario_id: int
    usuario_nombre: str
    cantidad_anterior: float
    cantidad_nueva: float
    motivo: str
    fecha: datetime.datetime


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
    es_urgente: bool = False


class AppointmentReportRead(BaseModel):
    fecha_inicial: datetime.date
    fecha_final: datetime.date
    total: int
    urgentes: int
    por_estado: dict[str, int]


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
