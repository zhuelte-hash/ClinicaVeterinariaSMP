"""Conserva el motivo de rechazo de un pago presentado en caja."""

import sqlalchemy as sa
from alembic import op

revision = "20261014_20"
down_revision = "20261014_19"
branch_labels = None
depends_on = None

SCHEMA = "clinica_veterinaria"


def upgrade() -> None:
    op.add_column("ordenes_cobro", sa.Column("motivo_rechazo", sa.String(500)), schema=SCHEMA)


def downgrade() -> None:
    op.drop_column("ordenes_cobro", "motivo_rechazo", schema=SCHEMA)
