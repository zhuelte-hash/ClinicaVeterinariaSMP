import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import distinct, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.clinic import AjusteInventario, CategoriaProducto, Cita, ComprobanteVenta, ConfiguracionClinica, EstadoCita, EstadoPago, EstadoProcesoAtencion, Notificacion, OrdenCobro, Producto, ProcesoAtencion, Proveedor, Mascota
from app.services.appointment_service import ACTIVE_BOOKING_STATES, AppointmentConflictError, AppointmentService, InvalidScheduleError
from app.models.user import Cajero, Cliente, PermisoRol, TipoUsuario, Usuario, Veterinario
from app.permissions import default_permission
from app.services.operation_utils import branch_id
from app.services.inventory_service import InventoryService
from app.schemas.admin import (
    AdminAppointmentRead, AdminCatalogOption, AdminProductCatalog, AdminProductCreate,
    AdminProductRead,
    AdminClientRead,
    AdminProductUpdate,
    InventoryStockUpdate,
    AdminCategoryCreate,
    AdminCategoryRead,
    AdminCategoryUpdate,
    AdminAppointmentUpdate,
    AdminNotificationCreate,
    AdminNotificationRead,
    AdminSettingsRead,
    AdminSettingsUpdate,
    AdminSaleRead,
    AdminSalesDayRead,
    RolePermissionRead,
    RolePermissionUpdate,
    SupplierWrite, SupplierRead, InventoryAdjustmentRead, AppointmentReportRead,
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
        statement = select(Producto).where(Producto.sucursal_id == branch_id(self.db)).options(selectinload(Producto.categoria)).order_by(Producto.nombre)
        if not include_inactive:
            statement = statement.where(Producto.activo)
        return [self._product_read(item) for item in self.db.scalars(statement).all()]

    def update_product(self, product_id: int, data: AdminProductUpdate) -> AdminProductRead:
        product = InventoryService(self.db).product(product_id)
        if product is None or not product.activo:
            raise AdminNotFoundError
        if data.categoria_id is not None and self.db.get(CategoriaProducto, data.categoria_id) is None:
            raise AdminNotFoundError
        if data.proveedor_id is not None and self.db.get(Proveedor, data.proveedor_id) is None:
            raise AdminNotFoundError
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(product, field, value)
        self._validate_unit(product)
        InventoryService(self.db).stock_alert(product)
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
        product = Producto(**data.model_dump(), sucursal_id=branch_id(self.db))
        self._validate_unit(product)
        self.db.add(product)
        try:
            initial = product.stock_actual
            product.stock_actual = 0
            self.db.flush()
            if initial:
                InventoryService(self.db).increase(product, initial, "Alta del producto", "ingreso", lot_code="INICIAL", cost=product.costo_unitario)
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

    def get_categories(self) -> list[AdminCategoryRead]:
        rows = self.db.execute(
            select(CategoriaProducto, func.count(Producto.id).label("productos"))
            .outerjoin(Producto, Producto.categoria_id == CategoriaProducto.id)
            .group_by(CategoriaProducto.id)
            .order_by(CategoriaProducto.nombre)
        ).all()
        return [AdminCategoryRead(id=item.id, nombre=item.nombre, productos=count) for item, count in rows]

    def create_category(self, data: AdminCategoryCreate) -> AdminCategoryRead:
        category = CategoriaProducto(nombre=data.nombre.strip())
        self.db.add(category)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise AdminConflictError("La categoría ya está registrada") from exc
        self.db.refresh(category)
        return AdminCategoryRead(id=category.id, nombre=category.nombre, productos=0)

    def update_category(self, category_id: int, data: AdminCategoryUpdate) -> AdminCategoryRead:
        category = self.db.get(CategoriaProducto, category_id)
        if category is None:
            raise AdminNotFoundError
        category.nombre = data.nombre.strip()
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise AdminConflictError("La categoría ya está registrada") from exc
        self.db.refresh(category)
        count = self.db.scalar(select(func.count(Producto.id)).where(Producto.categoria_id == category.id)) or 0
        return AdminCategoryRead(id=category.id, nombre=category.nombre, productos=count)

    def delete_category(self, category_id: int) -> None:
        category = self.db.get(CategoriaProducto, category_id)
        if category is None:
            raise AdminNotFoundError
        if self.db.scalar(select(func.count(Producto.id)).where(Producto.categoria_id == category_id)):
            raise AdminConflictError("No se puede eliminar una categoría con productos")
        self.db.delete(category)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise AdminConflictError("No se puede eliminar una categoría con productos") from exc

    def deactivate_product(self, product_id: int) -> None:
        product = self.db.get(Producto, product_id)
        if product is None:
            raise AdminNotFoundError
        product.activo = False
        self.db.commit()

    def update_stock(self, product_id: int, data: InventoryStockUpdate, user_id: int) -> AdminProductRead:
        product = self.db.scalar(select(Producto).where(Producto.id == product_id, Producto.activo, Producto.sucursal_id == branch_id(self.db)).with_for_update())
        if product is None:
            raise AdminNotFoundError
        if product.stock_actual != data.stock_anterior:
            raise AdminConflictError("El stock cambió desde que abriste el formulario. Actualiza el inventario e intenta de nuevo")
        if product.stock_actual == data.stock_actual:
            raise AdminConflictError("La nueva cantidad debe ser diferente de la actual")
        self.db.add(AjusteInventario(producto_id=product.id, usuario_id=user_id,
                                    cantidad_anterior=product.stock_actual, cantidad_nueva=data.stock_actual,
                                    motivo=data.motivo))
        delta = data.stock_actual - product.stock_actual
        if delta > 0:
            InventoryService(self.db).increase(product, delta, data.motivo, actor=user_id)
        else:
            InventoryService(self.db).consume(product, -delta, f"ajuste:{product.id}", physical_adjustment=True, reason=data.motivo, actor=user_id)
        self.db.commit()
        self.db.refresh(product)
        return self._product_read(product)

    def get_stock_adjustments(self, product_id: int | None = None) -> list[InventoryAdjustmentRead]:
        statement = select(AjusteInventario, Producto.nombre, Usuario.nombre).join(
            Producto, Producto.id == AjusteInventario.producto_id
        ).join(Usuario, Usuario.id == AjusteInventario.usuario_id)
        if product_id is not None:
            statement = statement.where(AjusteInventario.producto_id == product_id)
        return [InventoryAdjustmentRead(
            id=item.id, producto_id=item.producto_id, producto_nombre=product_name,
            usuario_id=item.usuario_id, usuario_nombre=user_name, cantidad_anterior=item.cantidad_anterior,
            cantidad_nueva=item.cantidad_nueva, motivo=item.motivo, fecha=item.fecha,
        ) for item, product_name, user_name in self.db.execute(statement.order_by(AjusteInventario.id.desc())).all()]

    def get_suppliers(self) -> list[SupplierRead]:
        rows = self.db.execute(select(Proveedor, func.count(Producto.id)).outerjoin(
            Producto, Producto.proveedor_id == Proveedor.id
        ).group_by(Proveedor.id).order_by(Proveedor.razon_social)).all()
        return [SupplierRead(id=item.id, razon_social=item.razon_social, productos=count) for item, count in rows]

    def save_supplier(self, data: SupplierWrite, supplier_id: int | None = None) -> SupplierRead:
        item = self.db.get(Proveedor, supplier_id) if supplier_id is not None else Proveedor()
        if item is None:
            raise AdminNotFoundError
        duplicate = select(Proveedor.id).where(func.lower(Proveedor.razon_social) == data.razon_social.lower())
        if supplier_id is not None:
            duplicate = duplicate.where(Proveedor.id != supplier_id)
        if self.db.scalar(duplicate) is not None:
            raise AdminConflictError("El proveedor ya está registrado")
        item.razon_social = data.razon_social
        self.db.add(item)
        self.db.commit()
        return next(row for row in self.get_suppliers() if row.id == item.id)

    def get_clients(self) -> list[AdminClientRead]:
        rows = self.db.execute(
            select(
                Usuario.id, Usuario.nombre, Usuario.correo,
                Cliente.telefono, Cliente.direccion,
                func.count(distinct(Mascota.id)).label("mascotas"),
                func.count(distinct(Cita.id)).label("citas"),
                func.max(Cita.fecha_hora_programada).label("ultima_cita"),
            )
            .join(Cliente, Cliente.usuario_id == Usuario.id)
            .outerjoin(Mascota, Mascota.cliente_id == Usuario.id)
            .outerjoin(Cita, Cita.mascota_id == Mascota.id)
            .where(Usuario.tipo == TipoUsuario.CLIENTE)
            .group_by(Usuario.id, Cliente.telefono, Cliente.direccion)
            .order_by(Usuario.nombre, Usuario.id)
        ).all()
        return [AdminClientRead.model_validate(row._mapping) for row in rows]

    def get_appointments(
        self, date: datetime.date | None = None, status: str | None = None,
        start_date: datetime.date | None = None, end_date: datetime.date | None = None,
        urgent: bool = False,
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
        if start_date:
            statement = statement.where(Cita.fecha_hora_programada >= datetime.datetime.combine(start_date, datetime.time.min, CLINIC_TIMEZONE).astimezone(datetime.timezone.utc))
        if end_date:
            statement = statement.where(Cita.fecha_hora_programada < datetime.datetime.combine(end_date + datetime.timedelta(days=1), datetime.time.min, CLINIC_TIMEZONE).astimezone(datetime.timezone.utc))
        if urgent:
            statement = statement.where(Cita.es_urgente.is_(True))
        appointments = self.db.scalars(statement.order_by(Cita.es_urgente.desc(), Cita.fecha_hora_programada.desc(), Cita.id.desc())).all()
        return [self._appointment_read(item) for item in appointments]

    def get_appointment_report(self, start_date: datetime.date, end_date: datetime.date) -> AppointmentReportRead:
        appointments = self.get_appointments(start_date=start_date, end_date=end_date)
        counts = {state.value: 0 for state in EstadoCita}
        for item in appointments:
            counts[item.estado] += 1
        return AppointmentReportRead(fecha_inicial=start_date, fecha_final=end_date,
                                     total=len(appointments), urgentes=sum(item.es_urgente for item in appointments), por_estado=counts)

    def get_veterinarians(self) -> list[AdminCatalogOption]:
        return [AdminCatalogOption(id=user.id, nombre=user.nombre) for user in self.db.scalars(
            select(Usuario).join(Usuario.veterinario).where(Usuario.tipo == TipoUsuario.VETERINARIO, Usuario.activo).order_by(Usuario.nombre)
        ).all()]

    def update_appointment(self, appointment_id: int, data: AdminAppointmentUpdate, admin_id: int) -> AdminAppointmentRead:
        service = AppointmentService(self.db)
        appointment = service._get_appointment_with_details(appointment_id, for_update=True)
        if appointment is None:
            raise AdminNotFoundError
        values = data.model_dump(exclude_unset=True)
        if not values:
            return self._appointment_read(appointment)
        if appointment.estado in {EstadoCita.ATENDIDA, EstadoCita.CANCELADA, EstadoCita.NO_ASISTIO}:
            raise AdminConflictError("La cita ya está finalizada y no puede modificarse")
        process = appointment.proceso_atencion
        if process is not None and process.estado != EstadoProcesoAtencion.CANCELADA:
            raise AdminConflictError("La cita tiene una atención clínica; gestiona su cierre desde la ficha veterinaria")
        state = data.estado or appointment.estado
        if state == EstadoCita.ATENDIDA:
            raise ValueError("Registra y cierra la atención clínica para marcar la cita como atendida")
        if state == EstadoCita.CANCELADA and not (data.nota_coordinacion or "").strip():
            raise ValueError("Indica el motivo de la cancelación")
        if state == EstadoCita.NO_ASISTIO:
            scheduled = appointment.fecha_hora_programada
            if scheduled.tzinfo is None:
                scheduled = scheduled.replace(tzinfo=datetime.timezone.utc)
            if appointment.fecha_hora_llegada is not None or scheduled > datetime.datetime.now(datetime.timezone.utc):
                raise ValueError("Solo puedes marcar inasistencia si pasó el horario y no se registró la llegada")
        veterinarian_id = values.get("veterinario_id", appointment.veterinario_id)
        if veterinarian_id is not None and self.db.scalar(select(Veterinario).join(Veterinario.usuario).where(
            Veterinario.usuario_id == veterinarian_id, Usuario.tipo == TipoUsuario.VETERINARIO, Usuario.activo
        )) is None:
            raise ValueError("El veterinario seleccionado no existe")
        if state in {EstadoCita.CONFIRMADA, EstadoCita.REPROGRAMADA} and veterinarian_id is None:
            raise ValueError("Asigna un veterinario para confirmar la cita")
        scheduling = "fecha_hora_programada" in values or "veterinario_id" in values
        if scheduling and appointment.fecha_hora_llegada is not None:
            raise AdminConflictError("No se puede reprogramar una cita cuya llegada ya se registró")
        if state in ACTIVE_BOOKING_STATES and (scheduling or state != appointment.estado):
            scheduled = data.fecha_hora_programada or appointment.fecha_hora_programada
            if scheduled.tzinfo is None:
                scheduled = scheduled.replace(tzinfo=datetime.timezone.utc)
            try:
                if veterinarian_id is not None:
                    service._confirm_without_overlap(appointment, veterinarian_id, scheduled)
                else:
                    service._validate_schedule(scheduled, appointment.servicio.duracion_estimada_min)
            except AppointmentConflictError as exc:
                raise AdminConflictError("El horario se cruza con otra cita del veterinario") from exc
            except InvalidScheduleError as exc:
                raise ValueError(str(exc)) from exc
            values["fecha_hora_fin_programada"] = scheduled + datetime.timedelta(minutes=appointment.servicio.duracion_estimada_min)
        previous_veterinarian = appointment.veterinario_id
        for field, value in values.items():
            setattr(appointment, field, value)
        if scheduling or state in {EstadoCita.CONFIRMADA, EstadoCita.REPROGRAMADA, EstadoCita.CANCELADA}:
            appointment.fecha_hora_propuesta = None
        appointment.estado_actualizado_por = admin_id
        recipients = {appointment.mascota.cliente_id, veterinarian_id, previous_veterinarian} - {None, admin_id}
        for recipient in recipients:
            self.db.add(Notificacion(
                usuario_id=recipient, cita_id=appointment.id, tipo="cambio_cita",
                titulo="Actualización de cita",
                mensaje=f"Administración actualizó la cita de {appointment.mascota.nombre}: {appointment.estado.value}.",
            ))
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise AdminConflictError("El horario de la cita está ocupado") from exc
        self.db.refresh(appointment)
        return self._appointment_read(appointment)

    def get_clinical_records(self) -> list[ProcesoAtencion]:
        return AppointmentService(self.db).get_veterinarian_clinical_records(None)

    def get_notifications(self, user_id: int, unread: bool = False) -> list[AdminNotificationRead]:
        statement = select(Notificacion, Usuario.nombre).join(Usuario, Usuario.id == Notificacion.usuario_id).where(Notificacion.usuario_id == user_id)
        if unread:
            statement = statement.where(Notificacion.leida.is_(False))
        rows = self.db.execute(statement.order_by(Notificacion.fecha_creacion.desc(), Notificacion.id.desc())).all()
        return [AdminNotificationRead(
            id=item.id, usuario_id=item.usuario_id, usuario_nombre=name, tipo=item.tipo,
            titulo=item.titulo, mensaje=item.mensaje, leida=item.leida, fecha_creacion=item.fecha_creacion,
        ) for item, name in rows]

    def create_notification(self, data: AdminNotificationCreate) -> AdminNotificationRead:
        user = self.db.get(Usuario, data.usuario_id)
        if user is None:
            raise AdminNotFoundError
        item = Notificacion(**data.model_dump())
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return AdminNotificationRead.model_validate({**data.model_dump(), "id": item.id, "usuario_nombre": user.nombre, "leida": item.leida, "fecha_creacion": item.fecha_creacion})

    def mark_all_notifications(self, user_id: int) -> None:
        self.db.execute(update(Notificacion).where(Notificacion.usuario_id == user_id, Notificacion.leida.is_(False)).values(leida=True))
        self.db.commit()

    def get_settings(self) -> AdminSettingsRead:
        item = self.db.scalar(select(ConfiguracionClinica).order_by(ConfiguracionClinica.id))
        if item is None:
            item = ConfiguracionClinica(nombre="Clínica Veterinaria", correo="", telefono="", direccion="")
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)
        return AdminSettingsRead.model_validate(item, from_attributes=True)

    def update_settings(self, data: AdminSettingsUpdate) -> AdminSettingsRead:
        item = self.db.scalar(select(ConfiguracionClinica).order_by(ConfiguracionClinica.id))
        if item is None:
            item = ConfiguracionClinica(**data.model_dump())
            self.db.add(item)
        else:
            for field, value in data.model_dump().items():
                setattr(item, field, value)
        self.db.commit()
        self.db.refresh(item)
        return AdminSettingsRead.model_validate(item, from_attributes=True)

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

    def _validate_unit(self, product):
        from app.models.operations import UnidadMedida
        from fastapi import HTTPException
        unit = self.db.get(UnidadMedida, product.unidad_medida)
        if unit is None:
            raise HTTPException(422, "Selecciona una unidad de medida configurada")
        if product.fraccionable and not unit.fraccionable:
            raise HTTPException(422, "Esta unidad no admite fracciones")
        if not product.fraccionable and any(Decimal(str(value)) != Decimal(str(value)).to_integral_value() for value in (product.stock_actual, product.stock_minimo)):
            raise HTTPException(422, "El stock debe ser entero para esta unidad")

    def get_role_permissions(self) -> list[RolePermissionRead]:
        records = {(item.rol, item.modulo): item for item in self.db.scalars(select(PermisoRol)).all()}
        return [
            self._permission_read(records.get((role, module)), role, module)
            for role in TipoUsuario for module in PERMISSION_MODULES
        ]

    def update_role_permission(self, role: TipoUsuario, module: str, data: RolePermissionUpdate) -> RolePermissionRead:
        if module not in PERMISSION_MODULES:
            raise ValueError("Módulo de permiso no válido")
        if role == TipoUsuario.ADMINISTRADOR and module == "usuarios" and not data.puede_editar:
            raise ValueError("El administrador debe conservar permiso para editar usuarios y permisos")
        permission = self.db.scalar(select(PermisoRol).where(PermisoRol.rol == role, PermisoRol.modulo == module))
        if permission is None:
            permission = PermisoRol(rol=role, modulo=module)
            self.db.add(permission)
        for field, value in data.model_dump().items():
            setattr(permission, field, value)
        self.db.commit()
        self.db.refresh(permission)
        return RolePermissionRead.model_validate(permission)

    def apply_recommended_permissions(self, role: TipoUsuario | None = None) -> list[RolePermissionRead]:
        """Reemplaza en una transacción los permisos administrativos seleccionados."""
        roles = (role,) if role is not None else tuple(TipoUsuario)
        existing = {(item.rol, item.modulo): item for item in self.db.scalars(
            select(PermisoRol).where(PermisoRol.rol.in_(roles)).with_for_update()
        ).all()}
        result = []
        for current_role in roles:
            admin = current_role == TipoUsuario.ADMINISTRADOR
            for module in PERMISSION_MODULES:
                permission = existing.get((current_role, module))
                if permission is None:
                    permission = PermisoRol(rol=current_role, modulo=module)
                    self.db.add(permission)
                for action in ("ver", "crear", "editar", "eliminar", "aprobar"):
                    setattr(permission, f"puede_{action}", default_permission(current_role, module, action))
                result.append(permission)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise AdminConflictError("Los permisos cambiaron al mismo tiempo. Intenta de nuevo")
        return [RolePermissionRead.model_validate(item) for item in result]

    @staticmethod
    def _product_read(product: Producto) -> AdminProductRead:
        return AdminProductRead(
            id=product.id, sku=product.sku, nombre=product.nombre,
            precio_venta=product.precio_venta, stock_actual=product.stock_actual,
            stock_minimo=product.stock_minimo, activo=product.activo,
            imagen_url=product.imagen_url, categoria_id=product.categoria_id,
            categoria_nombre=product.categoria.nombre,
            proveedor_id=product.proveedor_id, descripcion=product.descripcion, especies=product.especies,
            unidad_medida=product.unidad_medida, fraccionable=product.fraccionable, costo_unitario=product.costo_unitario, sucursal_id=product.sucursal_id,
        )

    @staticmethod
    def _appointment_read(item: Cita) -> AdminAppointmentRead:
        return AdminAppointmentRead(
            id=item.id, fecha_hora_programada=item.fecha_hora_programada,
            fecha_hora_fin_programada=item.fecha_hora_fin_programada,
            estado=item.estado.value, cliente_nombre=item.mascota.cliente.usuario.nombre,
            mascota_nombre=item.mascota.nombre, servicio_nombre=item.servicio.nombre,
            veterinario_id=item.veterinario_id,
            veterinario_nombre=item.veterinario.usuario.nombre if item.veterinario else None,
            nota_coordinacion=item.nota_coordinacion,
            es_urgente=item.es_urgente,
        )

    @staticmethod
    def _permission_read(permission: PermisoRol | None, role: TipoUsuario, module: str) -> RolePermissionRead:
        if permission is not None:
            return RolePermissionRead.model_validate(permission)
        # The pre-existing administrator role remains fully operational until explicit configuration.
        return RolePermissionRead(
            rol=role, modulo=module, **{f"puede_{action}": default_permission(role, module, action) for action in ("ver", "crear", "editar", "eliminar", "aprobar")},
        )
