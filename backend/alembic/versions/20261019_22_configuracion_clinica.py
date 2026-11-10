"""Agrega configuración persistente de la clínica para el panel administrativo."""

import sqlalchemy as sa
from alembic import op

revision = "20261019_22"
down_revision = "20261019_21"
branch_labels = None
depends_on = None

SCHEMA = "clinica_veterinaria"


def upgrade() -> None:
    op.create_table(
        "configuracion_clinica",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("correo", sa.String(254), nullable=False),
        sa.Column("telefono", sa.String(50), nullable=False, server_default=""),
        sa.Column("direccion", sa.String(250), nullable=False, server_default=""),
        sa.Column("umbral_stock_bajo", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("recordatorios_citas", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("alertas_stock", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("configuracion_clinica", schema=SCHEMA)
