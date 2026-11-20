"""Sede operativa persistida para pedidos y reportes multisedes (HU-094)."""
from alembic import op
import sqlalchemy as sa

revision = "20261119_26"
down_revision = "20261112_25"
branch_labels = None
depends_on = None


def upgrade():
    schema = "clinica_veterinaria"
    op.add_column("pedidos_web", sa.Column("sucursal_id", sa.BigInteger(), nullable=False, server_default="1"), schema=schema)
    # Conservar la sede de la venta o de los productos de pedidos anteriores.
    op.execute("""UPDATE clinica_veterinaria.pedidos_web p SET sucursal_id = COALESCE(
        (SELECT o.sucursal_id FROM clinica_veterinaria.ordenes_cobro o WHERE o.id = p.venta_id),
        (SELECT pr.sucursal_id FROM clinica_veterinaria.detalle_pedido_web d JOIN clinica_veterinaria.productos pr ON pr.id = d.producto_id WHERE d.pedido_id = p.id ORDER BY d.id LIMIT 1), 1)""")
    op.create_foreign_key("fk_pedidos_web_sucursal_id_sucursales", "pedidos_web", "sucursales", ["sucursal_id"], ["id"], source_schema=schema, referent_schema=schema)
    op.create_index("ix_pedidos_web_sucursal_id", "pedidos_web", ["sucursal_id"], schema=schema)


def downgrade():
    op.drop_index("ix_pedidos_web_sucursal_id", table_name="pedidos_web", schema="clinica_veterinaria")
    op.drop_constraint("fk_pedidos_web_sucursal_id_sucursales", "pedidos_web", schema="clinica_veterinaria", type_="foreignkey")
    op.drop_column("pedidos_web", "sucursal_id", schema="clinica_veterinaria")
