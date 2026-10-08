"""Agrega llegada, cancelacion automatica e idempotencia de WhatsApp."""

from alembic import op
import sqlalchemy as sa

revision = "20261006_17"
down_revision = "20261001_16"
branch_labels = None
depends_on = None
SCHEMA = "clinica_veterinaria"


def upgrade() -> None:
    op.add_column("citas", sa.Column("fecha_hora_llegada", sa.DateTime(timezone=True)), schema=SCHEMA)
    op.add_column("citas", sa.Column("cancelacion_automatica_at", sa.DateTime(timezone=True)), schema=SCHEMA)
    op.create_index("idx_citas_expiracion", "citas", ["estado", "fecha_hora_programada"], schema=SCHEMA)
    op.create_table(
        "whatsapp_mensajes",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("cita_id", sa.BigInteger(), nullable=False),
        sa.Column("evento", sa.String(50), nullable=False),
        sa.Column("telefono", sa.String(30), nullable=False),
        sa.Column("mensaje", sa.Text(), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False),
        sa.Column("proveedor_id", sa.String(150)),
        sa.Column("detalle_error", sa.String(500)),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("fecha_envio", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["cita_id"], [f"{SCHEMA}.citas.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("cita_id", "evento", name="uq_whatsapp_cita_evento"),
        schema=SCHEMA,
    )
    op.create_index("idx_whatsapp_mensajes_estado", "whatsapp_mensajes", ["estado"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_index("idx_whatsapp_mensajes_estado", table_name="whatsapp_mensajes", schema=SCHEMA)
    op.drop_table("whatsapp_mensajes", schema=SCHEMA)
    op.drop_index("idx_citas_expiracion", table_name="citas", schema=SCHEMA)
    op.drop_column("citas", "cancelacion_automatica_at", schema=SCHEMA)
    op.drop_column("citas", "fecha_hora_llegada", schema=SCHEMA)
