"""Completa catálogo, ficha de pacientes, transferencias y ajustes auditados."""

from alembic import op
import sqlalchemy as sa

revision = "20261110_24"
down_revision = "20261110_23"
branch_labels = None
depends_on = None
SCHEMA = "clinica_veterinaria"


def upgrade() -> None:
    op.add_column("productos", sa.Column("descripcion", sa.Text()), schema=SCHEMA)
    op.add_column("productos", sa.Column("especies", sa.JSON(), server_default=sa.text("'[]'"), nullable=False), schema=SCHEMA)
    for field in ("alergias", "condiciones_especiales"):
        op.add_column("mascotas", sa.Column(field, sa.Text()), schema=SCHEMA)
    op.add_column("mascotas", sa.Column("foto_url", sa.String(500)), schema=SCHEMA)
    op.execute(f"""UPDATE {SCHEMA}.mascotas m SET alergias = (
        SELECT string_agg(DISTINCT trim(f.historial_alergias), E'\n') FROM {SCHEMA}.fichas_clinicas f
        JOIN {SCHEMA}.procesos_atencion p ON p.id = f.proceso_medico_id
        WHERE p.mascota_id = m.id AND trim(coalesce(f.historial_alergias, '')) <> '')""")
    op.create_table(
        "ajustes_inventario",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("producto_id", sa.BigInteger(), sa.ForeignKey(f"{SCHEMA}.productos.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), sa.ForeignKey(f"{SCHEMA}.usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("cantidad_anterior", sa.Integer(), nullable=False),
        sa.Column("cantidad_nueva", sa.Integer(), nullable=False),
        sa.Column("motivo", sa.String(500), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("cantidad_anterior >= 0 AND cantidad_nueva >= 0", name="cantidades"),
        schema=SCHEMA,
    )
    # Versiones anteriores aplicaron dos veces la convención de nombres.
    for name in ("ck_ordenes_cobro_medio_pago", "ck_ordenes_cobro_ck_ordenes_cobro_medio_pago"):
        op.execute(f"ALTER TABLE {SCHEMA}.ordenes_cobro DROP CONSTRAINT IF EXISTS {name}")
    op.create_check_constraint("medio_pago", "ordenes_cobro", "medio_pago IS NULL OR medio_pago IN ('efectivo', 'yape', 'plin', 'tarjeta', 'transferencia')", schema=SCHEMA)


def downgrade() -> None:
    op.execute(f"UPDATE {SCHEMA}.ordenes_cobro SET medio_pago = NULL WHERE medio_pago = 'transferencia'")
    op.drop_constraint(op.f("ck_ordenes_cobro_medio_pago"), "ordenes_cobro", schema=SCHEMA, type_="check")
    op.create_check_constraint("medio_pago", "ordenes_cobro", "medio_pago IS NULL OR medio_pago IN ('efectivo', 'yape', 'plin', 'tarjeta')", schema=SCHEMA)
    op.drop_table("ajustes_inventario", schema=SCHEMA)
    for field in ("foto_url", "condiciones_especiales", "alergias"):
        op.drop_column("mascotas", field, schema=SCHEMA)
    op.drop_column("productos", "especies", schema=SCHEMA)
    op.drop_column("productos", "descripcion", schema=SCHEMA)
