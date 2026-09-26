"""Agrega bloqueos de agenda y notificaciones internas."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260925_07"
down_revision: str | None = "20260925_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "clinica_veterinaria"


def upgrade() -> None:
    op.create_table(
        "bloqueos_horario",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("veterinario_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha_hora_inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_hora_fin", sa.DateTime(timezone=True), nullable=False),
        sa.Column("motivo", sa.String(length=255), nullable=False),
        sa.CheckConstraint("fecha_hora_fin > fecha_hora_inicio", name="ck_bloqueos_horario_horas"),
        sa.ForeignKeyConstraint(
            ["veterinario_id"],
            [f"{SCHEMA}.veterinarios.usuario_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_bloqueos_veterinario_fecha",
        "bloqueos_horario",
        ["veterinario_id", "fecha_hora_inicio"],
        schema=SCHEMA,
    )
    op.create_table(
        "notificaciones",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("cita_id", sa.BigInteger(), nullable=True),
        sa.Column("tipo", sa.String(length=50), nullable=False),
        sa.Column("titulo", sa.String(length=150), nullable=False),
        sa.Column("mensaje", sa.String(length=500), nullable=False),
        sa.Column("leida", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], [f"{SCHEMA}.usuarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cita_id"], [f"{SCHEMA}.citas.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_notificaciones_usuario_leida",
        "notificaciones",
        ["usuario_id", "leida"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("idx_notificaciones_usuario_leida", table_name="notificaciones", schema=SCHEMA)
    op.drop_table("notificaciones", schema=SCHEMA)
    op.drop_index("idx_bloqueos_veterinario_fecha", table_name="bloqueos_horario", schema=SCHEMA)
    op.drop_table("bloqueos_horario", schema=SCHEMA)
