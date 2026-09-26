"""Completa datos básicos de mascota y fichas sin reserva."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260925_09"
down_revision: str | None = "20260925_08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "clinica_veterinaria"


def upgrade() -> None:
    op.add_column("mascotas", sa.Column("sexo", sa.String(length=20)), schema=SCHEMA)
    op.add_column("mascotas", sa.Column("fecha_nacimiento", sa.Date()), schema=SCHEMA)
    op.add_column("mascotas", sa.Column("peso_actual", sa.Numeric(precision=7, scale=2)), schema=SCHEMA)
    op.add_column("mascotas", sa.Column("caracteristicas", sa.Text()), schema=SCHEMA)
    op.alter_column("procesos_atencion", "cita_id", nullable=True, schema=SCHEMA)
    op.add_column("procesos_atencion", sa.Column("motivo_consulta", sa.Text()), schema=SCHEMA)
    op.add_column("procesos_atencion", sa.Column("anamnesis", sa.Text()), schema=SCHEMA)
    op.add_column("procesos_atencion", sa.Column("proxima_fecha_control", sa.Date()), schema=SCHEMA)


def downgrade() -> None:
    op.drop_column("procesos_atencion", "proxima_fecha_control", schema=SCHEMA)
    op.drop_column("procesos_atencion", "anamnesis", schema=SCHEMA)
    op.drop_column("procesos_atencion", "motivo_consulta", schema=SCHEMA)
    op.alter_column("procesos_atencion", "cita_id", nullable=False, schema=SCHEMA)
    for name in ("caracteristicas", "peso_actual", "fecha_nacimiento", "sexo"):
        op.drop_column("mascotas", name, schema=SCHEMA)
