"""Registra arqueos y formas de pago combinadas."""

import sqlalchemy as sa
from alembic import op

revision = "20261014_19"
down_revision = "20261012_18"
branch_labels = None
depends_on = None

SCHEMA = "clinica_veterinaria"


def upgrade() -> None:
    op.add_column("cajas", sa.Column("fecha_apertura", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), schema=SCHEMA)
    op.add_column("cajas", sa.Column("fecha_cierre", sa.DateTime(timezone=True)), schema=SCHEMA)
    op.add_column("cajas", sa.Column("efectivo_contado", sa.Numeric(12, 2)), schema=SCHEMA)
    op.add_column("cajas", sa.Column("diferencia", sa.Numeric(12, 2)), schema=SCHEMA)
    op.add_column("ordenes_cobro", sa.Column("pagos", sa.JSON()), schema=SCHEMA)
    op.add_column("ordenes_cobro", sa.Column("efectivo_recibido", sa.Numeric(12, 2)), schema=SCHEMA)
    op.add_column("ordenes_cobro", sa.Column("vuelto", sa.Numeric(12, 2), server_default="0", nullable=False), schema=SCHEMA)


def downgrade() -> None:
    for column in ("vuelto", "efectivo_recibido", "pagos"):
        op.drop_column("ordenes_cobro", column, schema=SCHEMA)
    for column in ("diferencia", "efectivo_contado", "fecha_cierre", "fecha_apertura"):
        op.drop_column("cajas", column, schema=SCHEMA)
