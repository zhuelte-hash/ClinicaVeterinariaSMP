"""Agrega imágenes de catálogo y productos de muestra."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260926_13"
down_revision: str | None = "20260926_12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "clinica_veterinaria"

IMAGES = {
    "ALI-001": "https://images.unsplash.com/photo-1589924691995-400dc9ecc119?auto=format&fit=crop&w=300&q=80",
    "ALI-002": "https://images.unsplash.com/photo-1606214174585-fe31582dc6ee?auto=format&fit=crop&w=300&q=80",
    "HIG-001": "https://images.unsplash.com/photo-1583337130417-3346a1be7dee?auto=format&fit=crop&w=300&q=80",
    "HIG-002": "https://images.unsplash.com/photo-1601758228041-f3b2795255f1?auto=format&fit=crop&w=300&q=80",
    "ACC-001": "https://images.unsplash.com/photo-1558788353-f76d92427f16?auto=format&fit=crop&w=300&q=80",
    "ACC-002": "https://images.unsplash.com/photo-1548199973-03cce0bbc87b?auto=format&fit=crop&w=300&q=80",
    "FAR-001": "https://images.unsplash.com/photo-1587300003388-59208cc962cb?auto=format&fit=crop&w=300&q=80",
    "FAR-002": "https://images.unsplash.com/photo-1581888227599-779811939961?auto=format&fit=crop&w=300&q=80",
}


def upgrade() -> None:
    op.add_column(
        "productos",
        sa.Column("imagen_url", sa.String(length=500), nullable=False, server_default="/logo.png"),
        schema=SCHEMA,
    )
    for sku, image in IMAGES.items():
        op.execute(sa.text(f"UPDATE {SCHEMA}.productos SET imagen_url = :image WHERE sku = :sku").bindparams(image=image, sku=sku))
    op.execute(sa.text(f"""
        INSERT INTO {SCHEMA}.productos (categoria_id, proveedor_id, sku, nombre, precio_venta, stock_actual, stock_minimo, activo, imagen_url)
        SELECT categoria.id, proveedor.id, sample.sku, sample.nombre, sample.precio, sample.stock, sample.minimo, true, sample.imagen
        FROM (VALUES
          ('ALI-003', 'Snack dental canino', 19.90, 18, 5, 'Alimentos', 'https://images.unsplash.com/photo-1587300003388-59208cc962cb?auto=format&fit=crop&w=300&q=80'),
          ('HIG-003', 'Toallitas húmedas para mascotas', 14.50, 24, 6, 'Higiene', 'https://images.unsplash.com/photo-1517849845537-4d257902454a?auto=format&fit=crop&w=300&q=80'),
          ('ACC-003', 'Juguete mordedor resistente', 22.00, 12, 4, 'Accesorios', 'https://images.unsplash.com/photo-1558788353-f76d92427f16?auto=format&fit=crop&w=300&q=80'),
          ('FAR-003', 'Spray cicatrizante veterinario', 28.00, 8, 3, 'Farmacia', 'https://images.unsplash.com/photo-1583337130417-3346a1be7dee?auto=format&fit=crop&w=300&q=80')
        ) AS sample(sku, nombre, precio, stock, minimo, categoria_nombre, imagen)
        JOIN {SCHEMA}.categorias_producto categoria ON categoria.nombre = sample.categoria_nombre
        CROSS JOIN (SELECT id FROM {SCHEMA}.proveedores ORDER BY id LIMIT 1) proveedor
        ON CONFLICT (sku) DO NOTHING
    """))


def downgrade() -> None:
    op.execute(sa.text(f"DELETE FROM {SCHEMA}.productos WHERE sku IN ('ALI-003', 'HIG-003', 'ACC-003', 'FAR-003')"))
    op.drop_column("productos", "imagen_url", schema=SCHEMA)
