"""Pedidos previos a la venta; el comprobante privado vive en PostgreSQL/Neon."""
import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Identity, Integer, JSON, LargeBinary, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, deferred

from app.database import Base, SCHEMA


class PedidoWeb(Base):
    __tablename__ = "pedidos_web"
    __table_args__ = (
        CheckConstraint("estado_pedido IN ('PENDIENTE','APROBADO','RECHAZADO','CANCELADO')", name="estado"),
        CheckConstraint("estado_pago IN ('PAGO_ENVIADO','VALIDADO','RECHAZADO','CANCELADO')", name="pago"),
        CheckConstraint("subtotal >= 0 AND descuento >= 0 AND costo_delivery >= 0 AND total > 0 AND total = subtotal - descuento + costo_delivery", name="importes"),
        CheckConstraint("(estado_pedido = 'APROBADO') = (venta_id IS NOT NULL)", name="venta_aprobada"),
        {"schema": SCHEMA},
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo_pedido: Mapped[str] = mapped_column(String(50), unique=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.clientes.usuario_id"), index=True)
    fecha_pedido: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    descuento: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    costo_delivery: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    metodo_pago: Mapped[str] = mapped_column(String(30))
    estado_pedido: Mapped[str] = mapped_column(String(20), default="PENDIENTE", index=True)
    estado_pago: Mapped[str] = mapped_column(String(20), default="PAGO_ENVIADO")
    datos_cliente: Mapped[dict] = mapped_column(JSON)
    numero_operacion: Mapped[str] = mapped_column(String(100))
    observaciones: Mapped[str] = mapped_column(String(1000), default="")
    comprobante_pago: Mapped[str] = mapped_column(String(100))
    comprobante_tipo: Mapped[str] = mapped_column(String(50))
    comprobante_contenido: Mapped[bytes] = deferred(mapped_column(LargeBinary))
    clave_idempotencia: Mapped[str] = mapped_column(String(80), unique=True)
    solicitud_hash: Mapped[str] = mapped_column(String(64))
    fecha_revision: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    usuario_revisor_id: Mapped[int | None] = mapped_column(ForeignKey(f"{SCHEMA}.usuarios.id"))
    motivo_rechazo: Mapped[str | None] = mapped_column(String(500))
    venta_id: Mapped[int | None] = mapped_column(ForeignKey(f"{SCHEMA}.ordenes_cobro.id"), unique=True)
    detalles: Mapped[list["DetallePedidoWeb"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class DetallePedidoWeb(Base):
    __tablename__ = "detalle_pedido_web"
    __table_args__ = (
        CheckConstraint("cantidad > 0 AND precio_unitario >= 0 AND subtotal = cantidad * precio_unitario", name="importes"),
        {"schema": SCHEMA},
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.pedidos_web.id", ondelete="CASCADE"), index=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.productos.id"))
    nombre_producto: Mapped[str] = mapped_column(String(150))
    imagen_url: Mapped[str] = mapped_column(String(500))
    cantidad: Mapped[int] = mapped_column(Integer)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
