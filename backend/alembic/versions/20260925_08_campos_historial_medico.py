"""Amplía la ficha clínica con antecedentes estructurados."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260925_08"
down_revision: str | None = "20260925_07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "clinica_veterinaria"


def upgrade() -> None:
    for name in ("vacunas", "desparasitaciones", "medicamentos", "procedimientos", "examenes_resultados"):
        op.add_column("fichas_clinicas", sa.Column(name, sa.Text()), schema=SCHEMA)


def downgrade() -> None:
    for name in ("examenes_resultados", "procedimientos", "medicamentos", "desparasitaciones", "vacunas"):
        op.drop_column("fichas_clinicas", name, schema=SCHEMA)
