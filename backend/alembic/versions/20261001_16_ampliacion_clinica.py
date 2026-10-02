"""Amplia el expediente clinico sin afectar inventario ni caja."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261001_16"
down_revision = "20260929_15"
branch_labels = None
depends_on = None

SCHEMA = "clinica_veterinaria"


def _enum(name, values, *, create_type=True):
    return postgresql.ENUM(*values, name=name, schema=SCHEMA, create_type=create_type)


def upgrade() -> None:
    bind = op.get_bind()
    _enum("estado_proceso_atencion", ["borrador", "en_atencion", "cerrada", "cancelada"]).create(bind, checkfirst=True)
    _enum("prioridad_examen", ["rutina", "urgente", "emergencia"]).create(bind, checkfirst=True)
    _enum("estado_orden_examen", ["solicitado", "en_proceso", "resultado_disponible", "revisado", "cancelado"]).create(bind, checkfirst=True)
    _enum("tipo_aplicacion_preventiva", ["vacuna", "desparasitacion"]).create(bind, checkfirst=True)

    op.add_column("procesos_atencion", sa.Column("estado", _enum("estado_proceso_atencion", ["borrador", "en_atencion", "cerrada", "cancelada"], create_type=False), server_default="borrador", nullable=False), schema=SCHEMA)
    op.add_column("procesos_atencion", sa.Column("fecha_cierre", sa.DateTime(timezone=True), nullable=True), schema=SCHEMA)
    op.execute(sa.text(f"UPDATE {SCHEMA}.procesos_atencion SET estado = 'cerrada', fecha_cierre = fecha_fin WHERE fecha_fin IS NOT NULL"))

    op.create_index("idx_procesos_estado", "procesos_atencion", ["estado"], schema=SCHEMA)
    op.create_table(
        "diagnosticos_atencion",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("proceso_id", sa.BigInteger(), sa.ForeignKey(f"{SCHEMA}.procesos_atencion.id", ondelete="CASCADE"), nullable=False),
        sa.Column("codigo", sa.String(50)), sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("es_principal", sa.Boolean(), server_default=sa.text("false"), nullable=False), sa.Column("observaciones", sa.Text()), schema=SCHEMA,
    )
    op.create_table(
        "ordenes_examen",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("proceso_id", sa.BigInteger(), sa.ForeignKey(f"{SCHEMA}.procesos_atencion.id", ondelete="CASCADE"), nullable=False),
        sa.Column("veterinario_id", sa.BigInteger(), sa.ForeignKey(f"{SCHEMA}.veterinarios.usuario_id", ondelete="RESTRICT"), nullable=False),
         sa.Column("tipo", sa.String(100), nullable=False), sa.Column("prioridad", _enum("prioridad_examen", ["rutina", "urgente", "emergencia"], create_type=False), server_default="rutina", nullable=False),
         sa.Column("estado", _enum("estado_orden_examen", ["solicitado", "en_proceso", "resultado_disponible", "revisado", "cancelado"], create_type=False), server_default="solicitado", nullable=False),
        sa.Column("resultado", sa.Text()), sa.Column("interpretacion", sa.Text()),
        sa.Column("revisado_por", sa.BigInteger(), sa.ForeignKey(f"{SCHEMA}.veterinarios.usuario_id", ondelete="RESTRICT")), sa.Column("revisado_en", sa.DateTime(timezone=True)), sa.Column("fecha_solicitud", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), schema=SCHEMA,
    )
    op.create_index("idx_ordenes_examen_proceso", "ordenes_examen", ["proceso_id"], schema=SCHEMA)
    op.create_table(
        "recetas",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True), sa.Column("proceso_id", sa.BigInteger(), sa.ForeignKey(f"{SCHEMA}.procesos_atencion.id", ondelete="CASCADE"), unique=True, nullable=False), sa.Column("veterinario_id", sa.BigInteger(), sa.ForeignKey(f"{SCHEMA}.veterinarios.usuario_id", ondelete="RESTRICT"), nullable=False), sa.Column("indicaciones_generales", sa.Text()), sa.Column("fecha_emision", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), schema=SCHEMA,
    )
    op.create_table(
        "detalles_receta",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True), sa.Column("receta_id", sa.BigInteger(), sa.ForeignKey(f"{SCHEMA}.recetas.id", ondelete="CASCADE"), nullable=False), sa.Column("medicamento", sa.String(150), nullable=False), sa.Column("presentacion", sa.String(150)), sa.Column("dosis", sa.String(100), nullable=False), sa.Column("unidad", sa.String(50), nullable=False), sa.Column("via", sa.String(80), nullable=False), sa.Column("frecuencia", sa.String(100), nullable=False), sa.Column("duracion", sa.String(100), nullable=False), sa.Column("cantidad", sa.String(50)), sa.Column("indicaciones", sa.Text()), schema=SCHEMA,
    )
    op.create_table(
        "procedimientos_realizados",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True), sa.Column("proceso_id", sa.BigInteger(), sa.ForeignKey(f"{SCHEMA}.procesos_atencion.id", ondelete="CASCADE"), nullable=False), sa.Column("veterinario_id", sa.BigInteger(), sa.ForeignKey(f"{SCHEMA}.veterinarios.usuario_id", ondelete="RESTRICT"), nullable=False), sa.Column("nombre", sa.String(150), nullable=False), sa.Column("fecha_realizacion", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("medicamentos_materiales", sa.JSON()), sa.Column("observaciones", sa.Text()), schema=SCHEMA,
    )
    op.create_table(
        "aplicaciones_preventivas",
         sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True), sa.Column("proceso_id", sa.BigInteger(), sa.ForeignKey(f"{SCHEMA}.procesos_atencion.id", ondelete="CASCADE"), nullable=False), sa.Column("veterinario_id", sa.BigInteger(), sa.ForeignKey(f"{SCHEMA}.veterinarios.usuario_id", ondelete="RESTRICT"), nullable=False), sa.Column("tipo", _enum("tipo_aplicacion_preventiva", ["vacuna", "desparasitacion"], create_type=False), nullable=False), sa.Column("producto", sa.String(150), nullable=False), sa.Column("lote", sa.String(100)), sa.Column("fecha_vencimiento", sa.Date()), sa.Column("fecha_aplicacion", sa.Date(), server_default=sa.func.current_date(), nullable=False), sa.Column("proxima_fecha", sa.Date()), sa.Column("observaciones", sa.Text()), schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("idx_ordenes_examen_proceso", table_name="ordenes_examen", schema=SCHEMA)
    for table in ("aplicaciones_preventivas", "procedimientos_realizados", "detalles_receta", "recetas", "ordenes_examen", "diagnosticos_atencion"):
        op.drop_table(table, schema=SCHEMA)
    op.drop_index("idx_procesos_estado", table_name="procesos_atencion", schema=SCHEMA)
    op.drop_column("procesos_atencion", "fecha_cierre", schema=SCHEMA)
    op.drop_column("procesos_atencion", "estado", schema=SCHEMA)
    bind = op.get_bind()
    for name in ("tipo_aplicacion_preventiva", "estado_orden_examen", "prioridad_examen", "estado_proceso_atencion"):
        postgresql.ENUM(name=name, schema=SCHEMA).drop(bind, checkfirst=True)
