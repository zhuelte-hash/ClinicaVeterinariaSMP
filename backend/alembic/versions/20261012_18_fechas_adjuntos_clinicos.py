"""Agrega fecha a estudios clínicos adjuntos."""

from alembic import op
import sqlalchemy as sa

revision = "20261012_18"
down_revision = "20261006_17"
branch_labels = None
depends_on = None

SCHEMA = "clinica_veterinaria"


def upgrade() -> None:
    op.add_column(
        "examenes_medicos_adjuntos",
        sa.Column("fecha_estudio", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=False),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("examenes_medicos_adjuntos", "fecha_estudio", schema=SCHEMA)
