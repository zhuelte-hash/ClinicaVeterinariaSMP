"""Impide multiples cajas abiertas por cajero.

Revision ID: 20260924_02
Revises: c1c86db6418b
Create Date: 2026-09-24
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260924_02"
down_revision: str | None = "c1c86db6418b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "clinica_veterinaria"


def upgrade() -> None:
    op.create_index(
        "uq_cajas_cajero_abierta",
        "cajas",
        ["cajero_id"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("estado_caja = 'abierta'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_cajas_cajero_abierta",
        table_name="cajas",
        schema=SCHEMA,
    )
