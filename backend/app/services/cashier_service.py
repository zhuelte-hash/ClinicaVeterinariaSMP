import datetime
from decimal import Decimal, ROUND_HALF_UP
import secrets

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.clinic import (
    Caja,
    CategoriaProducto,
    ComprobanteVenta,
    DetalleOrdenCobro,
    EstadoPago,
    OrdenCobro,
    Producto,
    Servicio,
)
from app.models.user import Cajero, Cliente, TipoUsuario, Usuario
from app.schemas.cashier import (
    BoletaDetalleRead,
    BoletaRead,
    CajaAbrir,
    CajaResumen,
    ClienteCajaRead,
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

    def get_summary(self, cashier_id: int) -> CajaResumen:
        pending = self.db.scalar(
            select(func.count(OrdenCobro.id)).where(
                OrdenCobro.cajero_id == cashier_id,
                OrdenCobro.estado_pago == EstadoPago.PAGO_ENVIADO,
            )
        ) or 0
        validated = self.db.scalar(
            select(func.count(OrdenCobro.id)).where(
                OrdenCobro.cajero_id == cashier_id,
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
        return CajaResumen(
            caja=self.get_open_register(cashier_id),
            ordenes_pendientes=pending,
            ordenes_validadas=validated,
            ordenes_recientes=recent,
        )

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

    def close_register(self, cashier_id: int) -> Caja:
        register = self.get_open_register(cashier_id)
        if register is None:
            raise CajaNoAbiertaError
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

        code = (
            f"VTA-{datetime.datetime.now(datetime.timezone.utc):%Y%m%d%H%M%S}-"
            f"{secrets.token_hex(2).upper()}"
        )
        order = OrdenCobro(
            codigo_orden=code,
            cajero_id=cashier.id,
            cliente_id=client.usuario_id if client else None,
            caja_id=register.id,
            monto_total=total,
            subtotal=(total / Decimal("1.18")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            impuesto=total - (total / Decimal("1.18")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            descuento=Decimal("0.00"),
            clave_idempotencia=data.clave_idempotencia,
            estado_pago=EstadoPago.VALIDADO_CONFIRMADO,
            medio_pago=data.medio_pago,
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
                or order.estado_pago != EstadoPago.VALIDADO_CONFIRMADO):
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
