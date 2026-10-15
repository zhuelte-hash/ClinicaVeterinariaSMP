import datetime
from decimal import Decimal, ROUND_HALF_UP
import secrets

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.clinic import (
    Caja,
    Cita,
    CategoriaProducto,
    ComprobanteVenta,
    DetalleOrdenCobro,
    EstadoPago,
    OrdenCobro,
    Producto,
    ProcesoAtencion,
    Servicio,
    Mascota,
)
from app.models.user import Cajero, Cliente, TipoUsuario, Usuario
from app.schemas.cashier import (
    BoletaDetalleRead,
    BoletaRead,
    CajaAbrir,
    CajaResumen,
    ClienteCajaRead,
    PagoCreate,
    VentaCreate,
)


class CajaYaAbiertaError(Exception):
    pass


class CajaNoAbiertaError(Exception):
    pass


class ClienteNoEncontradoError(Exception):
    pass


class ProductoNoDisponibleError(Exception):
    pass


class StockInsuficienteError(Exception):
    pass


class VentaNoEncontradaError(Exception):
    pass


class VentaDuplicadaError(Exception):
    pass


class VentaInvalidaError(Exception):
    pass


class CashierService:
    def __init__(self, db: Session):
        self.db = db

    def get_open_register(self, cashier_id: int) -> Caja | None:
        statement = (
            select(Caja)
            .where(Caja.cajero_id == cashier_id, Caja.estado_caja == "abierta")
            .order_by(Caja.id.desc())
        )
        return self.db.scalar(statement)

    def get_closed_registers(self, cashier_id: int) -> list[Caja]:
        return list(self.db.scalars(select(Caja).where(
            Caja.cajero_id == cashier_id, Caja.estado_caja == "cerrada"
        ).order_by(Caja.id.desc()).limit(20)).all())

    def get_summary(self, cashier_id: int) -> CajaResumen:
        register = self.get_open_register(cashier_id)
        pending = self.db.scalar(
            select(func.count(OrdenCobro.id)).where(
                OrdenCobro.caja_id == register.id if register else False,
                OrdenCobro.estado_pago == EstadoPago.PAGO_ENVIADO,
            )
        ) or 0
        validated = self.db.scalar(
            select(func.count(OrdenCobro.id)).where(
                OrdenCobro.caja_id == register.id if register else False,
                OrdenCobro.estado_pago == EstadoPago.VALIDADO_CONFIRMADO,
            )
        ) or 0
        recent = list(
            self.db.scalars(
                select(OrdenCobro)
                .where(OrdenCobro.cajero_id == cashier_id)
                .order_by(OrdenCobro.id.desc())
                .limit(8)
            ).all()
        )
        cash, digital = self._payment_totals(register.id) if register else (Decimal("0.00"), Decimal("0.00"))
        return CajaResumen(
            caja=register,
            ordenes_pendientes=pending,
            ordenes_validadas=validated,
            ordenes_recientes=recent,
            ingresos_efectivo=cash,
            ingresos_digitales=digital,
            efectivo_esperado=(register.fondo_inicial + cash) if register else Decimal("0.00"),
        )

    def _payment_totals(self, register_id: int) -> tuple[Decimal, Decimal]:
        orders = self.db.scalars(select(OrdenCobro).where(
            OrdenCobro.caja_id == register_id,
            OrdenCobro.estado_pago == EstadoPago.VALIDADO_CONFIRMADO,
        )).all()
        cash = Decimal("0.00")
        digital = Decimal("0.00")
        for order in orders:
            payments = order.pagos or [{"medio": order.medio_pago, "monto": str(order.monto_total)}]
            for payment in payments:
                amount = Decimal(str(payment["monto"]))
                if payment["medio"] == "efectivo":
                    cash += amount
                else:
                    digital += amount
        return cash, digital

    def open_register(self, cashier: Usuario, data: CajaAbrir) -> Caja:
        if self.get_open_register(cashier.id) is not None:
            raise CajaYaAbiertaError
        register = Caja(
            cajero_id=cashier.id,
            fondo_inicial=data.fondo_inicial,
            total_ingresos_validados=0,
            estado_caja="abierta",
        )
        self.db.add(register)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise CajaYaAbiertaError from exc
        self.db.refresh(register)
        return register

    def close_register(self, cashier_id: int, counted: Decimal) -> Caja:
        register = self.db.scalar(select(Caja).where(
            Caja.cajero_id == cashier_id, Caja.estado_caja == "abierta"
        ).with_for_update())
        if register is None:
            raise CajaNoAbiertaError
        if self.db.scalar(select(OrdenCobro.id).where(
            OrdenCobro.caja_id == register.id,
            OrdenCobro.estado_pago == EstadoPago.PAGO_ENVIADO,
        ).limit(1)) is not None:
            raise VentaInvalidaError("Revisa los pagos pendientes antes de cerrar la caja")
        cash, _ = self._payment_totals(register.id)
        register.efectivo_contado = counted
        register.diferencia = counted - register.fondo_inicial - cash
        register.fecha_cierre = datetime.datetime.now(datetime.timezone.utc)
        register.estado_caja = "cerrada"
        self.db.commit()
        self.db.refresh(register)
        return register

    def get_categories(self) -> list[CategoriaProducto]:
        return list(
            self.db.scalars(
                select(CategoriaProducto).order_by(CategoriaProducto.nombre)
            ).all()
        )

    def get_products(
        self, query: str | None = None, category_id: int | None = None
    ) -> list[Producto]:
        statement = select(Producto).options(selectinload(Producto.categoria)).where(Producto.activo)
        if query:
            pattern = f"%{query.strip()}%"
            statement = statement.where(
                or_(Producto.nombre.ilike(pattern), Producto.sku.ilike(pattern))
            )
        if category_id is not None:
            statement = statement.where(Producto.categoria_id == category_id)
        return list(self.db.scalars(statement.order_by(Producto.nombre)).all())

    def get_clients(self, query: str | None = None) -> list[ClienteCajaRead]:
        statement = select(Cliente, Usuario).join(Cliente.usuario)
        if query:
            pattern = f"%{query.strip()}%"
            statement = statement.where(
                or_(Usuario.nombre.ilike(pattern), Usuario.correo.ilike(pattern))
            )
        rows = self.db.execute(statement.order_by(Usuario.nombre).limit(50)).all()
        return [
            ClienteCajaRead(
                id=user.id,
                nombre=user.nombre,
                correo=user.correo,
                telefono=client.telefono,
            )
            for client, user in rows
        ]

    def get_services(self, query: str | None = None) -> list[Servicio]:
        statement = select(Servicio)
        if query:
            pattern = f"%{query.strip()}%"
            statement = statement.where(
                or_(Servicio.nombre.ilike(pattern), Servicio.codigo.ilike(pattern))
            )
        return list(self.db.scalars(statement.order_by(Servicio.nombre)).all())

    def get_attentions(self, client_id: int) -> list[dict]:
        rows = self.db.execute(select(ProcesoAtencion, Mascota, Servicio)
            .join(Mascota, ProcesoAtencion.mascota_id == Mascota.id)
            .join(Cita, ProcesoAtencion.cita_id == Cita.id)
            .join(Servicio, Cita.servicio_id == Servicio.id)
            .where(Mascota.cliente_id == client_id)
            .order_by(ProcesoAtencion.id.desc()).limit(50)).all()
        return [{"id": process.id, "mascota_nombre": pet.nombre,
                 "servicio_nombre": service.nombre, "cliente_id": pet.cliente_id}
                for process, pet, service in rows]

    def get_sales(self, cashier_id: int, limit: int = 30) -> list[dict]:
        orders = self.db.scalars(select(OrdenCobro).where(OrdenCobro.cajero_id == cashier_id)
            .order_by(OrdenCobro.id.desc()).limit(limit)).all()
        return [{"id": order.id, "codigo_orden": order.codigo_orden,
                 "monto_total": order.monto_total, "estado_pago": order.estado_pago,
                 "medio_pago": order.medio_pago} for order in orders]

    def get_pending(self, cashier_id: int) -> list[dict]:
        register = self.get_open_register(cashier_id)
        if register is None:
            return []
        orders = self.db.scalars(select(OrdenCobro).where(
            OrdenCobro.caja_id == register.id, OrdenCobro.estado_pago == EstadoPago.PAGO_ENVIADO
        ).options(selectinload(OrdenCobro.comprobante_pago_whatsapp)).order_by(OrdenCobro.id.desc())).all()
        return [{"id": order.id, "codigo_orden": order.codigo_orden,
                 "monto_total": order.monto_total, "estado_pago": order.estado_pago,
                 "medio_pago": order.medio_pago,
                 "captura_imagen": order.comprobante_pago_whatsapp.captura_imagen if order.comprobante_pago_whatsapp else None,
                 "codigo_operacion": order.comprobante_pago_whatsapp.codigo_operacion if order.comprobante_pago_whatsapp else None}
                for order in orders]

    def validate_pending(self, cashier_id: int, order_id: int) -> None:
        register = self.db.scalar(select(Caja).where(
            Caja.cajero_id == cashier_id, Caja.estado_caja == "abierta"
        ).with_for_update())
        if register is None:
            raise CajaNoAbiertaError
        order = self.db.scalar(select(OrdenCobro).where(
            OrdenCobro.id == order_id, OrdenCobro.cajero_id == cashier_id,
            OrdenCobro.caja_id == register.id,
        ).with_for_update())
        if order is None or order.estado_pago != EstadoPago.PAGO_ENVIADO:
            raise VentaInvalidaError("La orden no tiene un pago por validar")
        if order.comprobante_pago_whatsapp is None:
            raise VentaInvalidaError("Esta orden no tiene comprobante para revisar")
        if order.comprobante_venta is None:
            self.db.add(ComprobanteVenta(orden_cobro_id=order.id,
                        serie_correlativo=f"B001-{order.id:08d}", total_pagar=order.monto_total))
        order.estado_pago = EstadoPago.VALIDADO_CONFIRMADO
        register.total_ingresos_validados += order.monto_total
        self.db.commit()

    def reject_pending(self, cashier_id: int, order_id: int, reason: str) -> None:
        register = self.db.scalar(select(Caja).where(
            Caja.cajero_id == cashier_id, Caja.estado_caja == "abierta"
        ).with_for_update())
        if register is None:
            raise CajaNoAbiertaError
        order = self.db.scalar(select(OrdenCobro).where(
            OrdenCobro.id == order_id, OrdenCobro.cajero_id == cashier_id,
            OrdenCobro.caja_id == register.id,
        ).with_for_update())
        if order is None or order.estado_pago != EstadoPago.PAGO_ENVIADO:
            raise VentaInvalidaError("La orden no tiene un pago por rechazar")
        order.estado_pago = EstadoPago.ANULADO
        order.motivo_rechazo = reason.strip()
        self.db.commit()

    def create_sale(self, cashier: Usuario, data: VentaCreate) -> BoletaRead:
        try:
            return self._create_sale(cashier, data)
        except Exception:
            self.db.rollback()
            raise

    def _create_sale(self, cashier: Usuario, data: VentaCreate) -> BoletaRead:
        if data.clave_idempotencia:
            previous = self.db.scalar(select(OrdenCobro).where(OrdenCobro.clave_idempotencia == data.clave_idempotencia))
            if previous is not None:
                return self._existing_sale(previous, cashier, data)
        register = self.get_open_register(cashier.id)
        if register is None and cashier.tipo == TipoUsuario.ADMINISTRADOR:
            if self.db.get(Cajero, cashier.id) is None:
                self.db.add(Cajero(usuario_id=cashier.id))
                self.db.flush()
            register = Caja(cajero_id=cashier.id, fondo_inicial=Decimal("0.00"),
                            total_ingresos_validados=Decimal("0.00"), estado_caja="abierta")
            self.db.add(register)
            self.db.flush()
        if register is None:
            raise CajaNoAbiertaError
        register = self.db.scalar(select(Caja).where(Caja.id == register.id, Caja.estado_caja == "abierta").with_for_update())
        if register is None:
            raise CajaNoAbiertaError
        client = self.db.get(Cliente, data.cliente_id) if data.cliente_id is not None else None
        if data.cliente_id is not None and client is None:
            raise ClienteNoEncontradoError
        if data.proceso_atencion_id is not None:
            process = self.db.get(ProcesoAtencion, data.proceso_atencion_id)
            if (client is None or process is None or process.mascota.cliente_id != client.usuario_id):
                raise VentaInvalidaError("La atención no pertenece al cliente seleccionado")
            if self.db.scalar(select(OrdenCobro.id).where(
                OrdenCobro.proceso_atencion_id == process.id,
                OrdenCobro.estado_pago == EstadoPago.VALIDADO_CONFIRMADO,
            ).limit(1)) is not None:
                raise VentaInvalidaError("Esta atención ya tiene una venta pagada")

        quantities: dict[int, int] = {}
        service_quantities: dict[int, int] = {}
        for item in data.items:
            if item.producto_id is not None:
                quantities[item.producto_id] = quantities.get(item.producto_id, 0) + item.cantidad
            if item.servicio_id is not None:
                service_quantities[item.servicio_id] = (
                    service_quantities.get(item.servicio_id, 0) + item.cantidad
                )
        products = list(
            self.db.scalars(
                select(Producto)
                .where(Producto.id.in_(quantities), Producto.activo)
                .order_by(Producto.id)
                .with_for_update()
            ).all()
        )
        if len(products) != len(quantities):
            raise ProductoNoDisponibleError
        services = list(
            self.db.scalars(
                select(Servicio).where(Servicio.id.in_(service_quantities))
            ).all()
        )
        if len(services) != len(service_quantities):
            raise ProductoNoDisponibleError

        product_by_id = {product.id: product for product in products}
        total = Decimal("0.00")
        details: list[DetalleOrdenCobro] = []
        for product_id, quantity in quantities.items():
            product = product_by_id[product_id]
            if product.stock_actual < quantity:
                raise StockInsuficienteError
            subtotal = (product.precio_venta * quantity).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            total += subtotal
            product.stock_actual -= quantity
            details.append(
                DetalleOrdenCobro(
                    producto_id=product.id,
                    cantidad=quantity,
                    precio_unitario=product.precio_venta,
                    subtotal=subtotal,
                )
            )
        service_by_id = {service.id: service for service in services}
        for service_id, quantity in service_quantities.items():
            service = service_by_id[service_id]
            subtotal = (service.precio_referencial * quantity).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            total += subtotal
            details.append(
                DetalleOrdenCobro(
                    servicio_id=service.id,
                    cantidad=quantity,
                    precio_unitario=service.precio_referencial,
                    subtotal=subtotal,
                )
            )

        if data.descuento > total:
            raise VentaInvalidaError("El descuento supera el importe de la venta")
        total = (total - data.descuento).quantize(Decimal("0.01"))
        if total <= 0:
            raise VentaInvalidaError("El total de la venta debe ser mayor que cero")
        payments = data.pagos or [PagoCreate(medio=data.medio_pago, monto=total)]
        if sum((payment.monto for payment in payments), Decimal("0.00")) != total:
            raise VentaInvalidaError("La suma de los pagos debe coincidir con el total")
        cash_amount = sum((payment.monto for payment in payments if payment.medio == "efectivo"), Decimal("0.00"))
        if data.efectivo_recibido is not None and cash_amount == 0:
            raise VentaInvalidaError("El efectivo recibido requiere un pago en efectivo")
        if data.efectivo_recibido is not None and data.efectivo_recibido < cash_amount:
            raise VentaInvalidaError("El efectivo recibido no alcanza para el cobro")
        change = (data.efectivo_recibido - cash_amount) if data.efectivo_recibido is not None else Decimal("0.00")
        code = (
            f"VTA-{datetime.datetime.now(datetime.timezone.utc):%Y%m%d%H%M%S}-"
            f"{secrets.token_hex(2).upper()}"
        )
        order = OrdenCobro(
            codigo_orden=code,
            cajero_id=cashier.id,
            cliente_id=client.usuario_id if client else None,
            proceso_atencion_id=data.proceso_atencion_id,
            caja_id=register.id,
            monto_total=total,
            subtotal=(total / Decimal("1.18")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            impuesto=total - (total / Decimal("1.18")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            descuento=data.descuento,
            clave_idempotencia=data.clave_idempotencia,
            estado_pago=EstadoPago.VALIDADO_CONFIRMADO,
            medio_pago=data.medio_pago,
            pagos=[{"medio": payment.medio, "monto": str(payment.monto)} for payment in payments],
            efectivo_recibido=data.efectivo_recibido,
            vuelto=change,
            detalles=details,
        )
        self.db.add(order)
        self.db.flush()
        receipt = ComprobanteVenta(
            orden_cobro_id=order.id,
            serie_correlativo=f"B001-{order.id:08d}",
            total_pagar=total,
        )
        self.db.add(receipt)
        register.total_ingresos_validados += total
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            if data.clave_idempotencia:
                previous = self.db.scalar(select(OrdenCobro).where(OrdenCobro.clave_idempotencia == data.clave_idempotencia))
                if previous is not None:
                    return self._existing_sale(previous, cashier, data)
            raise VentaDuplicadaError from exc
        return self.get_receipt(cashier.id, order.id)

    def _existing_sale(self, order: OrdenCobro, cashier: Usuario, data: VentaCreate) -> BoletaRead:
        requested = {}
        for item in data.items:
            key = (item.producto_id, item.servicio_id)
            requested[key] = requested.get(key, 0) + item.cantidad
        existing = {(item.producto_id, item.servicio_id): item.cantidad for item in order.detalles}
        if (order.cajero_id != cashier.id or order.cliente_id != data.cliente_id
                or order.medio_pago != data.medio_pago or existing != requested
                or order.estado_pago != EstadoPago.VALIDADO_CONFIRMADO
                or order.descuento != data.descuento
                or order.proceso_atencion_id != data.proceso_atencion_id
                or order.efectivo_recibido != data.efectivo_recibido
                or (data.pagos is not None and order.pagos != [
                    {"medio": p.medio, "monto": str(p.monto)} for p in data.pagos])):
            raise VentaDuplicadaError
        return self.get_receipt(cashier.id, order.id)

    def get_receipt(self, cashier_id: int, order_id: int) -> BoletaRead:
        statement = (
            select(OrdenCobro)
            .where(OrdenCobro.id == order_id, OrdenCobro.cajero_id == cashier_id)
            .options(
                selectinload(OrdenCobro.detalles).selectinload(
                    DetalleOrdenCobro.producto
                ),
                selectinload(OrdenCobro.detalles).selectinload(
                    DetalleOrdenCobro.servicio
                ),
                selectinload(OrdenCobro.comprobante_venta),
                selectinload(OrdenCobro.cliente).selectinload(Cliente.usuario),
                selectinload(OrdenCobro.cajero),
            )
        )
        order = self.db.scalar(statement)
        if order is None or order.comprobante_venta is None:
            raise VentaNoEncontradaError
        return BoletaRead(
            orden_id=order.id,
            codigo_orden=order.codigo_orden,
            serie_correlativo=order.comprobante_venta.serie_correlativo,
            fecha_emision=order.comprobante_venta.fecha_emision,
            cliente_nombre=order.cliente.usuario.nombre if order.cliente else None,
            cliente_correo=order.cliente.usuario.correo if order.cliente else None,
            cajero_nombre=order.cajero.usuario.nombre,
            medio_pago=order.medio_pago or "no_especificado",
            subtotal=order.subtotal,
            igv=order.impuesto,
            descuento=order.descuento,
            estado="ANULADA" if order.estado_pago == EstadoPago.ANULADO else "PAGADA",
            total=order.monto_total,
            pagos=order.pagos or [{"medio": order.medio_pago, "monto": order.monto_total}],
            efectivo_recibido=order.efectivo_recibido,
            vuelto=order.vuelto,
            proceso_atencion_id=order.proceso_atencion_id,
            detalles=[
                BoletaDetalleRead(
                    producto_id=detail.producto_id,
                    servicio_id=detail.servicio_id,
                    codigo=(
                        detail.producto.sku
                        if detail.producto is not None
                        else detail.servicio.codigo
                    ),
                    tipo="producto" if detail.producto is not None else "servicio",
                    nombre=(
                        detail.producto.nombre
                        if detail.producto is not None
                        else detail.servicio.nombre
                    ),
                    cantidad=detail.cantidad,
                    precio_unitario=detail.precio_unitario,
                    subtotal=detail.subtotal,
                )
                for detail in order.detalles
            ],
        )
