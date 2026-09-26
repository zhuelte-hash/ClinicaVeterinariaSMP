"""Extiende citas para solicitudes y agenda veterinaria.

Revision ID: 20260925_06
Revises: 20260924_05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260925_06"
down_revision: str | None = "20260924_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "clinica_veterinaria"


def upgrade() -> None:
    for value in (
        "pendiente_contacto",
        "contactando_cliente",
        "esperando_respuesta",
        "requiere_otro_horario",
        "cliente_no_respondio",
    ):
        op.execute(
            sa.text(
                "ALTER TYPE clinica_veterinaria.estado_cita "
                f"ADD VALUE IF NOT EXISTS '{value}'"
            )
        )

    op.drop_index("uq_citas_horario_activo", table_name="citas", schema=SCHEMA)
    op.add_column("citas", sa.Column("veterinario_id", sa.BigInteger()), schema=SCHEMA)
    op.add_column(
        "citas", sa.Column("fecha_hora_propuesta", sa.DateTime(timezone=True)), schema=SCHEMA
    )
    op.add_column("citas", sa.Column("telefono_contacto", sa.String(30)), schema=SCHEMA)
    op.add_column("citas", sa.Column("preferencia_contacto", sa.String(20)), schema=SCHEMA)
    op.add_column("citas", sa.Column("nota_coordinacion", sa.String(500)), schema=SCHEMA)
    op.add_column("citas", sa.Column("estado_actualizado_por", sa.BigInteger()), schema=SCHEMA)
    op.add_column(
        "citas",
        sa.Column(
            "fecha_actualizacion",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema=SCHEMA,
    )
    op.create_foreign_key(
        "fk_citas_veterinario_id_veterinarios",
        "citas",
        "veterinarios",
        ["veterinario_id"],
        ["usuario_id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_citas_estado_actualizado_por_usuarios",
        "citas",
        "usuarios",
        ["estado_actualizado_por"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
        ondelete="SET NULL",
    )
    op.create_index(
        "uq_citas_horario_activo",
        "citas",
        ["veterinario_id", "fecha_hora_programada"],
        unique=True,
        postgresql_where=sa.text(
            "veterinario_id IS NOT NULL AND estado IN "
            "('confirmada', 'reprogramada', 'atendida')"
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_citas_veterinario_estado",
        "citas",
        ["veterinario_id", "estado"],
        schema=SCHEMA,
    )
    op.create_table(
        "horarios_veterinarios",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("veterinario_id", sa.BigInteger(), nullable=False),
        sa.Column("dia_semana", sa.Integer(), nullable=False),
        sa.Column("hora_inicio", sa.Time(), nullable=False),
        sa.Column("hora_fin", sa.Time(), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.CheckConstraint("dia_semana BETWEEN 0 AND 6", name="ck_horarios_veterinarios_dia_semana"),
        sa.CheckConstraint("hora_fin > hora_inicio", name="ck_horarios_veterinarios_horas"),
        sa.ForeignKeyConstraint(
            ["veterinario_id"],
            [f"{SCHEMA}.veterinarios.usuario_id"],
            ondelete="CASCADE",
            name="fk_horarios_veterinarios_veterinario_id_veterinarios",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_horarios_veterinario",
        "horarios_veterinarios",
        ["veterinario_id", "dia_semana"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("uq_citas_horario_activo", table_name="citas", schema=SCHEMA)
    op.create_index(
        "uq_citas_horario_activo",
        "citas",
        ["fecha_hora_programada"],
        unique=True,
        postgresql_where=sa.text("estado NOT IN ('cancelada', 'no_asistio')"),
        schema=SCHEMA,
    )
    op.drop_index("idx_horarios_veterinario", table_name="horarios_veterinarios", schema=SCHEMA)
    op.drop_table("horarios_veterinarios", schema=SCHEMA)
    op.drop_index("idx_citas_veterinario_estado", table_name="citas", schema=SCHEMA)
    op.drop_constraint("fk_citas_estado_actualizado_por_usuarios", "citas", schema=SCHEMA, type_="foreignkey")
    op.drop_constraint("fk_citas_veterinario_id_veterinarios", "citas", schema=SCHEMA, type_="foreignkey")
    for column in (
        "fecha_actualizacion",
        "estado_actualizado_por",
        "nota_coordinacion",
        "preferencia_contacto",
        "telefono_contacto",
        "fecha_hora_propuesta",
        "veterinario_id",
    ):
        op.drop_column("citas", column, schema=SCHEMA)
