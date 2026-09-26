"""Refuerza la integridad de agenda y la relación cita-mascota."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260926_10"
down_revision: str | None = "20260925_09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "clinica_veterinaria"


def upgrade() -> None:
    op.drop_index("uq_citas_horario_activo", table_name="citas", schema=SCHEMA)
    op.create_index(
        "uq_citas_horario_activo",
        "citas",
        ["veterinario_id", "fecha_hora_programada"],
        unique=True,
        postgresql_where=sa.text(
            "veterinario_id IS NOT NULL AND estado NOT IN ('cancelada', 'no_asistio')"
        ),
        schema=SCHEMA,
    )

    op.create_unique_constraint(
        "uq_citas_id_mascota", "citas", ["id", "mascota_id"], schema=SCHEMA
    )
    op.drop_constraint(
        "fk_procesos_atencion_cita_id_citas",
        "procesos_atencion",
        schema=SCHEMA,
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_procesos_atencion_cita_mascota_citas",
        "procesos_atencion",
        "citas",
        ["cita_id", "mascota_id"],
        ["id", "mascota_id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
        ondelete="RESTRICT",
    )
    op.execute(
        sa.text(
            f"""
            DELETE FROM {SCHEMA}.horarios_veterinarios duplicate
            USING {SCHEMA}.horarios_veterinarios keeper
            WHERE duplicate.id > keeper.id
              AND duplicate.veterinario_id = keeper.veterinario_id
              AND duplicate.dia_semana = keeper.dia_semana
              AND duplicate.hora_inicio = keeper.hora_inicio
              AND duplicate.hora_fin = keeper.hora_fin
            """
        )
    )
    op.create_unique_constraint(
        "uq_horario_veterinario_rango",
        "horarios_veterinarios",
        ["veterinario_id", "dia_semana", "hora_inicio", "hora_fin"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_horario_veterinario_rango", "horarios_veterinarios", schema=SCHEMA
    )
    op.drop_constraint(
        "fk_procesos_atencion_cita_mascota_citas",
        "procesos_atencion",
        schema=SCHEMA,
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_procesos_atencion_cita_id_citas",
        "procesos_atencion",
        "citas",
        ["cita_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
        ondelete="RESTRICT",
    )
    op.drop_constraint("uq_citas_id_mascota", "citas", schema=SCHEMA)
    op.drop_index("uq_citas_horario_activo", table_name="citas", schema=SCHEMA)
    op.create_index(
        "uq_citas_horario_activo",
        "citas",
        ["veterinario_id", "fecha_hora_programada"],
        unique=True,
        postgresql_where=sa.text(
            "veterinario_id IS NOT NULL AND estado IN ('confirmada', 'reprogramada', 'atendida')"
        ),
        schema=SCHEMA,
    )
