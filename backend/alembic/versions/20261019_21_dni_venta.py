"""Guarda el DNI indicado para una venta presencial."""

import sqlalchemy as sa
from alembic import op

revision = "20261019_21"
down_revision = "20261014_20"
branch_labels = None
depends_on = None

SCHEMA = "clinica_veterinaria"


def upgrade() -> None:
    op.add_column("ordenes_cobro", sa.Column("cliente_dni", sa.String(8)), schema=SCHEMA)


def downgrade() -> None:
    op.drop_column("ordenes_cobro", "cliente_dni", schema=SCHEMA)
