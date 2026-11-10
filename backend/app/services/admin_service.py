import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import distinct, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.clinic import CategoriaProducto, Cita, ComprobanteVenta, ConfiguracionClinica, EstadoCita, EstadoPago, EstadoProcesoAtencion, Notificacion, OrdenCobro, Producto, ProcesoAtencion, Proveedor, Mascota
from app.services.appointment_service import ACTIVE_BOOKING_STATES, AppointmentConflictError, AppointmentService, InvalidScheduleError
from app.models.user import Cajero, Cliente, PermisoRol, TipoUsuario, Usuario, Veterinario
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
        if product is None or not product.activo:
            raise AdminNotFoundError
        if data.categoria_id is not None and self.db.get(CategoriaProducto, data.categoria_id) is None:
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

    def update_stock(self, product_id: int, data: InventoryStockUpdate) -> AdminProductRead:
        product = self.db.scalar(select(Producto).where(Producto.id == product_id, Producto.activo).with_for_update())
        if product is None:
            raise AdminNotFoundError
        product.stock_actual = data.stock_actual
        self.db.commit()
        self.db.refresh(product)
        return self._product_read(product)

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
        appointments = self.db.scalars(statement.order_by(Cita.fecha_hora_programada.desc(), Cita.id.desc())).all()
        return [self._appointment_read(item) for item in appointments]

    def get_veterinarians(self) -> list[AdminCatalogOption]:
        return [AdminCatalogOption(id=user.id, nombre=user.nombre) for user in self.db.scalars(
            select(Usuario).join(Usuario.veterinario).where(Usuario.tipo == TipoUsuario.VETERINARIO).order_by(Usuario.nombre)
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
            Veterinario.usuario_id == veterinarian_id, Usuario.tipo == TipoUsuario.VETERINARIO
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
                permission.puede_ver = admin
                permission.puede_crear = admin
                permission.puede_editar = admin
                permission.puede_eliminar = admin
                permission.puede_aprobar = admin
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
