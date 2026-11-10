"""Pedidos web y comprobantes privados persistentes."""
from alembic import op
import sqlalchemy as sa

revision = "20261109_22"
down_revision = "20261019_21"
branch_labels = None
depends_on = None
SCHEMA = "clinica_veterinaria"


def upgrade():
    op.create_table("pedidos_web",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("codigo_pedido", sa.String(50), nullable=False, unique=True),
        sa.Column("cliente_id", sa.BigInteger(), sa.ForeignKey(f"{SCHEMA}.clientes.usuario_id"), nullable=False),
        sa.Column("fecha_pedido", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("descuento", sa.Numeric(12, 2), nullable=False),
        sa.Column("costo_delivery", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("metodo_pago", sa.String(30), nullable=False),
        sa.Column("estado_pedido", sa.String(20), nullable=False),
        sa.Column("estado_pago", sa.String(20), nullable=False),
        sa.Column("datos_cliente", sa.JSON(), nullable=False),
        sa.Column("numero_operacion", sa.String(100), nullable=False),
        sa.Column("observaciones", sa.String(1000), nullable=False),
        sa.Column("comprobante_pago", sa.String(100), nullable=False),
        sa.Column("comprobante_tipo", sa.String(50), nullable=False),
        sa.Column("comprobante_contenido", sa.LargeBinary(), nullable=False),
        sa.Column("clave_idempotencia", sa.String(80), nullable=False, unique=True),
        sa.Column("solicitud_hash", sa.String(64), nullable=False),
        sa.Column("fecha_revision", sa.DateTime(timezone=True)),
        sa.Column("usuario_revisor_id", sa.BigInteger(), sa.ForeignKey(f"{SCHEMA}.usuarios.id")),
        sa.Column("motivo_rechazo", sa.String(500)),
        sa.Column("venta_id", sa.BigInteger(), sa.ForeignKey(f"{SCHEMA}.ordenes_cobro.id"), unique=True),
        sa.CheckConstraint("estado_pedido IN ('PENDIENTE','APROBADO','RECHAZADO','CANCELADO')", name="estado"),
        sa.CheckConstraint("estado_pago IN ('PAGO_ENVIADO','VALIDADO','RECHAZADO','CANCELADO')", name="pago"),
        sa.CheckConstraint("subtotal >= 0 AND descuento >= 0 AND costo_delivery >= 0 AND total > 0 AND total = subtotal - descuento + costo_delivery", name="importes"),
        sa.CheckConstraint("(estado_pedido = 'APROBADO') = (venta_id IS NOT NULL)", name="venta_aprobada"),
        schema=SCHEMA)
    for column in ("cliente_id", "fecha_pedido", "estado_pedido"):
        op.create_index(f"ix_{SCHEMA}_pedidos_web_{column}", "pedidos_web", [column], schema=SCHEMA)
    op.create_table("detalle_pedido_web",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("pedido_id", sa.BigInteger(), sa.ForeignKey(f"{SCHEMA}.pedidos_web.id", ondelete="CASCADE"), nullable=False),
        sa.Column("producto_id", sa.BigInteger(), sa.ForeignKey(f"{SCHEMA}.productos.id"), nullable=False),
        sa.Column("nombre_producto", sa.String(150), nullable=False),
        sa.Column("imagen_url", sa.String(500), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("precio_unitario", sa.Numeric(12, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.CheckConstraint("cantidad > 0 AND precio_unitario >= 0 AND subtotal = cantidad * precio_unitario", name="importes"),
        schema=SCHEMA)
    op.create_index(f"ix_{SCHEMA}_detalle_pedido_web_pedido_id", "detalle_pedido_web", ["pedido_id"], schema=SCHEMA)
    op.add_column("ordenes_cobro", sa.Column("costo_delivery", sa.Numeric(12, 2), nullable=False, server_default="0"), schema=SCHEMA)


def downgrade():
    op.drop_column("ordenes_cobro", "costo_delivery", schema=SCHEMA)
    op.drop_table("detalle_pedido_web", schema=SCHEMA)
    op.drop_table("pedidos_web", schema=SCHEMA)
