"""Permite incluir servicios en las boletas.

Revision ID: 20260924_05
Revises: 20260924_04
Create Date: 2026-09-24
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260924_05"
down_revision: str | None = "20260924_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "clinica_veterinaria"


def upgrade() -> None:
    op.alter_column(
        "detalles_orden_cobro",
        "producto_id",
        existing_type=sa.BigInteger(),
        nullable=True,
        schema=SCHEMA,
    )
    op.add_column(
        "detalles_orden_cobro",
        sa.Column("servicio_id", sa.BigInteger()),
        schema=SCHEMA,
    )
    op.create_foreign_key(
        "fk_detalles_orden_cobro_servicio_id_servicios",
        "detalles_orden_cobro",
        "servicios",
        ["servicio_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_detalles_orden_cobro_item",
        "detalles_orden_cobro",
        "(producto_id IS NOT NULL) <> (servicio_id IS NOT NULL)",
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_detalles_orden_cobro_item",
        "detalles_orden_cobro",
        type_="check",
        schema=SCHEMA,
    )
    op.drop_constraint(
        "fk_detalles_orden_cobro_servicio_id_servicios",
        "detalles_orden_cobro",
        type_="foreignkey",
        schema=SCHEMA,
    )
    op.drop_column("detalles_orden_cobro", "servicio_id", schema=SCHEMA)
    op.alter_column(
        "detalles_orden_cobro",
        "producto_id",
        existing_type=sa.BigInteger(),
        nullable=False,
        schema=SCHEMA,
    )
