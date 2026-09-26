"""Agrega desactivacion de productos y permisos configurables por rol."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260926_12"
down_revision: str | None = "20260926_11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "clinica_veterinaria"


def upgrade() -> None:
    op.add_column(
        "productos",
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_productos_activos", "productos", ["activo"], schema=SCHEMA
    )
    op.create_table(
        "permisos_rol",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("rol", postgresql.ENUM("cliente", "veterinario", "cajero", "administrador", name="tipo_usuario", schema=SCHEMA, create_type=False), nullable=False),
        sa.Column("modulo", sa.String(length=100), nullable=False),
        sa.Column("puede_ver", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("puede_crear", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("puede_editar", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("puede_eliminar", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("puede_aprobar", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint("rol", "modulo", name="uq_permisos_rol_modulo"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("permisos_rol", schema=SCHEMA)
    op.drop_index("idx_productos_activos", table_name="productos", schema=SCHEMA)
    op.drop_column("productos", "activo", schema=SCHEMA)
