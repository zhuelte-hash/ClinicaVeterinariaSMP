"""Crea el modulo inicial de usuarios.

Revision ID: 20260915_01
Revises:
Create Date: 2026-09-15
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260915_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "clinica_veterinaria"

tipo_usuario = postgresql.ENUM(
    "cliente",
    "veterinario",
    "cajero",
    "administrador",
    name="tipo_usuario",
    schema=SCHEMA,
    create_type=False,
)


def upgrade() -> None:
    op.execute(sa.text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
    tipo_usuario.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "usuarios",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("correo", sa.String(254), nullable=False),
        sa.Column("contrasena", sa.String(255), nullable=False),
        sa.Column("tipo", tipo_usuario, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_usuarios"),
        sa.UniqueConstraint("correo", name="uq_usuarios_correo"),
        schema=SCHEMA,
    )
    op.create_index(
        "uq_usuarios_correo_lower",
        "usuarios",
        [sa.text("lower(correo)")],
        unique=True,
        schema=SCHEMA,
    )

    for table_name in ("clientes", "cajeros", "administradores"):
        extra_columns: list[sa.Column] = []
        if table_name == "clientes":
            extra_columns = [
                sa.Column("telefono", sa.String(30)),
                sa.Column("direccion", sa.String(255)),
            ]
        op.create_table(
            table_name,
            sa.Column("usuario_id", sa.BigInteger(), nullable=False),
            *extra_columns,
            sa.ForeignKeyConstraint(
                ["usuario_id"],
                [f"{SCHEMA}.usuarios.id"],
                name=f"fk_{table_name}_usuario_id_usuarios",
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("usuario_id", name=f"pk_{table_name}"),
            schema=SCHEMA,
        )

    op.create_table(
        "veterinarios",
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("colegiatura", sa.String(50), nullable=False),
        sa.Column("especialidad", sa.String(100)),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            [f"{SCHEMA}.usuarios.id"],
            name="fk_veterinarios_usuario_id_usuarios",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("usuario_id", name="pk_veterinarios"),
        sa.UniqueConstraint("colegiatura", name="uq_veterinarios_colegiatura"),
        schema=SCHEMA,
    )

    op.create_table(
        "permisos",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("administrador_id", sa.BigInteger(), nullable=False),
        sa.Column("modulo", sa.String(100), nullable=False),
        sa.Column("puede_ver", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("puede_editar", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.ForeignKeyConstraint(
            ["administrador_id"],
            [f"{SCHEMA}.administradores.usuario_id"],
            name="fk_permisos_administrador_id_administradores",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_permisos"),
        sa.UniqueConstraint(
            "administrador_id",
            "modulo",
            name="uq_permisos_administrador_modulo",
        ),
        schema=SCHEMA,
    )

    op.create_table(
        "auditoria_acciones",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("administrador_id", sa.BigInteger(), nullable=False),
        sa.Column("accion_critica", sa.String(255), nullable=False),
        sa.Column(
            "fecha_hora",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["administrador_id"],
            [f"{SCHEMA}.administradores.usuario_id"],
            name="fk_auditoria_acciones_administrador_id_administradores",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_auditoria_acciones"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    for table_name in (
        "auditoria_acciones",
        "permisos",
        "veterinarios",
        "administradores",
        "cajeros",
        "clientes",
    ):
        op.drop_table(table_name, schema=SCHEMA)
    op.drop_index("uq_usuarios_correo_lower", table_name="usuarios", schema=SCHEMA)
    op.drop_table("usuarios", schema=SCHEMA)
    tipo_usuario.drop(op.get_bind(), checkfirst=True)
    op.execute(sa.text(f"DROP SCHEMA IF EXISTS {SCHEMA}"))
