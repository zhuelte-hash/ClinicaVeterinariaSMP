"""Impide solapamientos de citas directamente en PostgreSQL."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260926_11"
down_revision: str | None = "20260926_10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "clinica_veterinaria"


def upgrade() -> None:
    op.add_column(
        "citas",
        sa.Column("fecha_hora_fin_programada", sa.DateTime(timezone=True)),
        schema=SCHEMA,
    )
    op.execute(
        sa.text(
            f"""
            UPDATE {SCHEMA}.citas cita
            SET fecha_hora_fin_programada = cita.fecha_hora_programada
                + (servicio.duracion_estimada_min * interval '1 minute')
            FROM {SCHEMA}.servicios servicio
            WHERE servicio.id = cita.servicio_id
            """
        )
    )
    op.alter_column(
        "citas", "fecha_hora_fin_programada", nullable=False, schema=SCHEMA
    )
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
    op.execute(
        sa.text(
            f"""
            ALTER TABLE {SCHEMA}.citas
            ADD CONSTRAINT ex_citas_veterinario_solapamiento
            EXCLUDE USING gist (
                veterinario_id WITH =,
                tstzrange(fecha_hora_programada, fecha_hora_fin_programada, '[)') WITH &&
            )
            WHERE (
                veterinario_id IS NOT NULL
                AND estado NOT IN ('cancelada', 'no_asistio')
            )
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"ALTER TABLE {SCHEMA}.citas DROP CONSTRAINT ex_citas_veterinario_solapamiento"
        )
    )
    op.drop_column("citas", "fecha_hora_fin_programada", schema=SCHEMA)
