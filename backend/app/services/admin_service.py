import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.clinic import CategoriaProducto, Cita, ComprobanteVenta, EstadoPago, OrdenCobro, Producto, Proveedor, Mascota
from app.models.user import Cajero, Cliente, PermisoRol, TipoUsuario, Veterinario
from app.schemas.admin import (
    AdminAppointmentRead, AdminCatalogOption, AdminProductCatalog, AdminProductCreate,
    AdminProductRead,
    AdminProductUpdate,
    AdminSaleRead,
    AdminSalesDayRead,
    RolePermissionRead,
    RolePermissionUpdate,
)

CLINIC_TIMEZONE = ZoneInfo("America/Lima")
PERMISSION_MODULES = ("productos", "inventario", "ventas", "usuarios", "citas", "mascotas", "historias_clinicas")


class AdminNotFoundError(Exception):
    pass


class AdminConflictError(Exception):
    pass


class AdminService:
    def __init__(self, db: Session):
        self.db = db

    def get_products(self, include_inactive: bool = False) -> list[AdminProductRead]:
        statement = select(Producto).options(selectinload(Producto.categoria)).order_by(Producto.nombre)
        if not include_inactive:
            statement = statement.where(Producto.activo)
        return [self._product_read(item) for item in self.db.scalars(statement).all()]

    def update_product(self, product_id: int, data: AdminProductUpdate) -> AdminProductRead:
        product = self.db.get(Producto, product_id)
        if product is None:
            raise AdminNotFoundError
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(product, field, value)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise AdminConflictError("El SKU ya está registrado") from exc
        self.db.refresh(product)
        return self._product_read(product)

    def create_product(self, data: AdminProductCreate) -> AdminProductRead:
        if self.db.get(CategoriaProducto, data.categoria_id) is None or self.db.get(Proveedor, data.proveedor_id) is None:
            raise AdminNotFoundError
        product = Producto(**data.model_dump())
        self.db.add(product)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise AdminConflictError("El SKU ya está registrado") from exc
        self.db.refresh(product)
        return self._product_read(product)

    def get_product_catalog(self) -> AdminProductCatalog:
        return AdminProductCatalog(
            categorias=[AdminCatalogOption(id=item.id, nombre=item.nombre) for item in self.db.scalars(select(CategoriaProducto).order_by(CategoriaProducto.nombre)).all()],
            proveedores=[AdminCatalogOption(id=item.id, nombre=item.razon_social) for item in self.db.scalars(select(Proveedor).order_by(Proveedor.razon_social)).all()],
        )

    def deactivate_product(self, product_id: int) -> None:
        product = self.db.get(Producto, product_id)
        if product is None:
            raise AdminNotFoundError
        product.activo = False
        self.db.commit()

    def get_appointments(
        self, date: datetime.date | None = None, status: str | None = None
    ) -> list[AdminAppointmentRead]:
        statement = select(Cita).options(
            selectinload(Cita.mascota).selectinload(Mascota.cliente).selectinload(Cliente.usuario),
            selectinload(Cita.servicio),
            selectinload(Cita.veterinario).selectinload(Veterinario.usuario),
        )
        if date is not None:
            start = datetime.datetime.combine(date, datetime.time.min, tzinfo=CLINIC_TIMEZONE)
            end = start + datetime.timedelta(days=1)
            statement = statement.where(Cita.fecha_hora_programada >= start, Cita.fecha_hora_programada < end)
        if status:
            statement = statement.where(Cita.estado == status)
        appointments = self.db.scalars(statement.order_by(Cita.fecha_creacion.desc(), Cita.id.desc())).all()
        return [
            AdminAppointmentRead(
                id=item.id,
                fecha_hora_programada=item.fecha_hora_programada,
                estado=item.estado.value,
                cliente_nombre=item.mascota.cliente.usuario.nombre,
                mascota_nombre=item.mascota.nombre,
                servicio_nombre=item.servicio.nombre,
                veterinario_nombre=item.veterinario.usuario.nombre if item.veterinario else None,
            )
            for item in appointments
        ]

    def get_sales_day(self, date: datetime.date | None = None) -> AdminSalesDayRead:
        report_date = date or datetime.datetime.now(CLINIC_TIMEZONE).date()
        start = datetime.datetime.combine(report_date, datetime.time.min, tzinfo=CLINIC_TIMEZONE)
        end = start + datetime.timedelta(days=1)
        statement = select(OrdenCobro).join(OrdenCobro.comprobante_venta).options(
            selectinload(OrdenCobro.comprobante_venta),
            selectinload(OrdenCobro.cajero).selectinload(Cajero.usuario),
            selectinload(OrdenCobro.cliente).selectinload(Cliente.usuario),
        ).where(
            OrdenCobro.estado_pago == EstadoPago.VALIDADO_CONFIRMADO,
            ComprobanteVenta.fecha_emision >= start,
            ComprobanteVenta.fecha_emision < end,
        ).order_by(ComprobanteVenta.fecha_emision.desc())
        sales = [
            AdminSaleRead(
                id=item.id,
                codigo_orden=item.codigo_orden,
                fecha_emision=item.comprobante_venta.fecha_emision,
                cajero_nombre=item.cajero.usuario.nombre,
                cliente_nombre=item.cliente.usuario.nombre if item.cliente else None,
                total=item.monto_total,
                medio_pago=item.medio_pago,
            )
            for item in self.db.scalars(statement).all()
        ]
        return AdminSalesDayRead(
            fecha=report_date,
            total=sum((sale.total for sale in sales), Decimal("0.00")),
            ventas=sales,
        )

    def get_role_permissions(self) -> list[RolePermissionRead]:
        records = {(item.rol, item.modulo): item for item in self.db.scalars(select(PermisoRol)).all()}
        return [
            self._permission_read(records.get((role, module)), role, module)
            for role in TipoUsuario for module in PERMISSION_MODULES
        ]

    def update_role_permission(self, role: TipoUsuario, module: str, data: RolePermissionUpdate) -> RolePermissionRead:
        if module not in PERMISSION_MODULES:
            raise ValueError("Módulo de permiso no válido")
        permission = self.db.scalar(select(PermisoRol).where(PermisoRol.rol == role, PermisoRol.modulo == module))
        if permission is None:
            permission = PermisoRol(rol=role, modulo=module)
            self.db.add(permission)
        for field, value in data.model_dump().items():
            setattr(permission, field, value)
        self.db.commit()
        self.db.refresh(permission)
        return RolePermissionRead.model_validate(permission)

    @staticmethod
    def _product_read(product: Producto) -> AdminProductRead:
        return AdminProductRead(
            id=product.id, sku=product.sku, nombre=product.nombre,
            precio_venta=product.precio_venta, stock_actual=product.stock_actual,
            stock_minimo=product.stock_minimo, activo=product.activo,
            imagen_url=product.imagen_url, categoria_id=product.categoria_id,
            categoria_nombre=product.categoria.nombre,
        )

    @staticmethod
    def _permission_read(permission: PermisoRol | None, role: TipoUsuario, module: str) -> RolePermissionRead:
        if permission is not None:
            return RolePermissionRead.model_validate(permission)
        # The pre-existing administrator role remains fully operational until explicit configuration.
        full_access = role == TipoUsuario.ADMINISTRADOR
        return RolePermissionRead(
            rol=role, modulo=module, puede_ver=full_access, puede_crear=full_access,
            puede_editar=full_access, puede_eliminar=full_access, puede_aprobar=full_access,
        )
