"""Agrega punto de venta y boletas.

Revision ID: 20260924_04
Revises: 20260924_03
Create Date: 2026-09-24
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260924_04"
down_revision: str | None = "20260924_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "clinica_veterinaria"


def upgrade() -> None:
    op.add_column(
        "ordenes_cobro",
        sa.Column("medio_pago", sa.String(30)),
        schema=SCHEMA,
    )
    op.create_check_constraint(
        "ck_ordenes_cobro_medio_pago",
        "ordenes_cobro",
        "medio_pago IS NULL OR medio_pago IN ('efectivo', 'yape', 'plin', 'tarjeta')",
        schema=SCHEMA,
    )
    op.add_column(
        "comprobantes_venta",
        sa.Column(
            "fecha_emision",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema=SCHEMA,
    )
    op.create_table(
        "detalles_orden_cobro",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("orden_cobro_id", sa.BigInteger(), nullable=False),
        sa.Column("producto_id", sa.BigInteger(), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("precio_unitario", sa.Numeric(12, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.CheckConstraint("cantidad > 0", name="ck_detalles_orden_cobro_cantidad"),
        sa.CheckConstraint("precio_unitario >= 0", name="ck_detalles_orden_cobro_precio"),
        sa.CheckConstraint("subtotal >= 0", name="ck_detalles_orden_cobro_subtotal"),
        sa.ForeignKeyConstraint(
            ["orden_cobro_id"],
            [f"{SCHEMA}.ordenes_cobro.id"],
            name="fk_detalles_orden_cobro_orden_cobro_id_ordenes_cobro",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["producto_id"],
            [f"{SCHEMA}.productos.id"],
            name="fk_detalles_orden_cobro_producto_id_productos",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_detalles_orden_cobro"),
        schema=SCHEMA,
    )

    op.execute(sa.text(f"""
        INSERT INTO {SCHEMA}.categorias_producto (nombre)
        VALUES ('Alimentos'), ('Higiene'), ('Accesorios'), ('Farmacia')
        ON CONFLICT (nombre) DO NOTHING
    """))
    op.execute(sa.text(f"""
        INSERT INTO {SCHEMA}.proveedores (razon_social)
        SELECT 'Distribuidora Clinica SMP'
        WHERE NOT EXISTS (
            SELECT 1 FROM {SCHEMA}.proveedores
            WHERE razon_social = 'Distribuidora Clinica SMP'
        )
    """))
    op.execute(sa.text(f"""
        INSERT INTO {SCHEMA}.productos
            (categoria_id, proveedor_id, sku, nombre, precio_venta, stock_actual, stock_minimo)
        SELECT c.id, p.id, v.sku, v.nombre, v.precio, v.stock, 5
        FROM (VALUES
            ('ALI-001', 'Alimento premium perro 3 kg', 69.90, 30, 'Alimentos'),
            ('ALI-002', 'Alimento premium gato 1 kg', 39.90, 25, 'Alimentos'),
            ('HIG-001', 'Shampoo veterinario 500 ml', 32.50, 20, 'Higiene'),
            ('HIG-002', 'Pasta dental para mascotas', 24.90, 18, 'Higiene'),
            ('ACC-001', 'Correa ajustable', 29.90, 15, 'Accesorios'),
            ('ACC-002', 'Plato antideslizante', 18.50, 22, 'Accesorios'),
            ('FAR-001', 'Antipulgas pipeta', 45.00, 16, 'Farmacia'),
            ('FAR-002', 'Suplemento multivitaminico', 38.00, 14, 'Farmacia')
        ) AS v(sku, nombre, precio, stock, categoria)
        JOIN {SCHEMA}.categorias_producto c ON c.nombre = v.categoria
        CROSS JOIN LATERAL (
            SELECT id FROM {SCHEMA}.proveedores
            WHERE razon_social = 'Distribuidora Clinica SMP'
            ORDER BY id LIMIT 1
        ) p
        ON CONFLICT (sku) DO NOTHING
    """))


def downgrade() -> None:
    op.drop_table("detalles_orden_cobro", schema=SCHEMA)
    op.drop_column("comprobantes_venta", "fecha_emision", schema=SCHEMA)
    op.drop_constraint(
        "ck_ordenes_cobro_medio_pago",
        "ordenes_cobro",
        type_="check",
        schema=SCHEMA,
    )
    op.drop_column("ordenes_cobro", "medio_pago", schema=SCHEMA)
