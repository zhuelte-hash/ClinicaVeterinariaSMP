"""Catálogo comercial con procedencia y datos desconocidos, sin duplicar tablas."""
from alembic import op
import sqlalchemy as sa

revision = "20261124_27"
down_revision = "20261119_26"
branch_labels = None
depends_on = None
SCHEMA = "clinica_veterinaria"


def upgrade():
    op.alter_column("productos", "precio_venta", existing_type=sa.Numeric(12, 2), nullable=True, schema=SCHEMA)
    op.alter_column("productos", "proveedor_id", existing_type=sa.BigInteger(), nullable=True, schema=SCHEMA)
    for name, kind in [("marca", sa.String(150)), ("presentacion", sa.String(250)), ("subcategoria", sa.String(100)), ("catalogo_origen", sa.JSON())]:
        op.add_column("productos", sa.Column(name, kind, nullable=True), schema=SCHEMA)
    op.add_column("productos", sa.Column("es_demostracion", sa.Boolean(), nullable=False, server_default=sa.text("false")), schema=SCHEMA)


def downgrade():
    # No sustituir información desconocida por precios o proveedores inventados.
    bind = op.get_bind()
    if bind.scalar(sa.text("SELECT count(*) FROM clinica_veterinaria.productos WHERE precio_venta IS NULL OR proveedor_id IS NULL")):
        raise RuntimeError("Completa los precios y proveedores desconocidos antes de revertir esta migración.")
    for name in ("es_demostracion", "catalogo_origen", "subcategoria", "presentacion", "marca"):
        op.drop_column("productos", name, schema=SCHEMA)
    op.alter_column("productos", "proveedor_id", existing_type=sa.BigInteger(), nullable=False, schema=SCHEMA)
    op.alter_column("productos", "precio_venta", existing_type=sa.Numeric(12, 2), nullable=False, schema=SCHEMA)
