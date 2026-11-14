"""Control de vencimiento obligatorio para medicamentos y perecibles."""
from alembic import op
import sqlalchemy as sa

revision = '20261112_25'
down_revision = '37ebf391ec82'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('productos', sa.Column('requiere_vencimiento', sa.Boolean(), nullable=False, server_default=sa.text('false')), schema='clinica_veterinaria')


def downgrade():
    op.drop_column('productos', 'requiere_vencimiento', schema='clinica_veterinaria')
