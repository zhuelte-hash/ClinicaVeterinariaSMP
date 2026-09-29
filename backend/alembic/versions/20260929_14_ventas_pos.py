"""Totales e idempotencia para las órdenes de caja existentes."""

from alembic import op
import sqlalchemy as sa

revision = "20260929_14"
down_revision = "20260926_13"
branch_labels = None
depends_on = None
SCHEMA = "clinica_veterinaria"


def upgrade() -> None:
    for name in ("subtotal", "descuento", "impuesto"):
        op.add_column("ordenes_cobro", sa.Column(name, sa.Numeric(12, 2), nullable=False, server_default="0"), schema=SCHEMA)
    op.add_column("ordenes_cobro", sa.Column("clave_idempotencia", sa.String(80), nullable=True), schema=SCHEMA)
    op.create_unique_constraint("uq_ordenes_cobro_clave_idempotencia", "ordenes_cobro", ["clave_idempotencia"], schema=SCHEMA)
    op.execute(sa.text(f"""UPDATE {SCHEMA}.ordenes_cobro AS o SET
        subtotal = round(o.monto_total / 1.18, 2),
        impuesto = o.monto_total - round(o.monto_total / 1.18, 2)
        WHERE EXISTS (SELECT 1 FROM {SCHEMA}.comprobantes_venta c WHERE c.orden_cobro_id = o.id)"""))


def downgrade() -> None:
    op.drop_constraint("uq_ordenes_cobro_clave_idempotencia", "ordenes_cobro", schema=SCHEMA)
    for name in ("clave_idempotencia", "impuesto", "descuento", "subtotal"):
        op.drop_column("ordenes_cobro", name, schema=SCHEMA)
