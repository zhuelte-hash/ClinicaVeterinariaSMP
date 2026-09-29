"""Permite ventas presenciales sin cliente identificado."""
from alembic import op
import sqlalchemy as sa

revision = "20260929_15"
down_revision = "20260929_14"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("ordenes_cobro", "cliente_id", existing_type=sa.BigInteger(), nullable=True, schema="clinica_veterinaria")


def downgrade() -> None:
    op.alter_column("ordenes_cobro", "cliente_id", existing_type=sa.BigInteger(), nullable=False, schema="clinica_veterinaria")
