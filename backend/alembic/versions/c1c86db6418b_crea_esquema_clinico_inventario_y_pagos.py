"""Crea los modulos clinico, inventario y pagos.

Revision ID: c1c86db6418b
Revises: 20260915_01
Create Date: 2026-09-24 08:46:46.669364
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c1c86db6418b"
down_revision: str | None = "20260915_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "clinica_veterinaria"

estado_cita = postgresql.ENUM(
    "pendiente",
    "confirmada",
    "reprogramada",
    "atendida",
    "cancelada",
    "no_asistio",
    name="estado_cita",
    schema=SCHEMA,
    create_type=False,
)
tipo_atencion_medica = postgresql.ENUM(
    "consulta_general",
    "cirugia",
    "vacunacion",
    "desparasitacion",
    "laboratorio_e_imagen",
    name="tipo_atencion_medica",
    schema=SCHEMA,
    create_type=False,
)
tipo_estetica = postgresql.ENUM(
    "bano_simple",
    "bano_medicado",
    "corte_y_estilizado",
    "corte_de_unas_y_limpieza_oidos",
    name="tipo_estetica",
    schema=SCHEMA,
    create_type=False,
)
tipo_proceso_atencion = postgresql.ENUM(
    "medica",
    "estetica",
    name="tipo_proceso_atencion",
    schema=SCHEMA,
    create_type=False,
)
estado_pago = postgresql.ENUM(
    "pendiente",
    "pago_enviado",
    "validado_confirmado",
    "anulado",
    name="estado_pago",
    schema=SCHEMA,
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (
        estado_cita,
        tipo_atencion_medica,
        tipo_estetica,
        tipo_proceso_atencion,
        estado_pago,
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table('categorias_producto',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('nombre', sa.String(length=100), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_categorias_producto')),
    sa.UniqueConstraint('nombre', name=op.f('uq_categorias_producto_nombre')),
    schema='clinica_veterinaria'
    )
    op.create_table('proveedores',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('razon_social', sa.String(length=180), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_proveedores')),
    schema='clinica_veterinaria'
    )
    op.create_table('servicios',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('codigo', sa.String(length=50), nullable=False),
    sa.Column('nombre', sa.String(length=150), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=True),
    sa.Column('precio_referencial', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('duracion_estimada_min', sa.Integer(), nullable=False),
    sa.CheckConstraint('duracion_estimada_min > 0', name=op.f('ck_servicios_duracion')),
    sa.CheckConstraint('precio_referencial >= 0', name=op.f('ck_servicios_precio')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_servicios')),
    sa.UniqueConstraint('codigo', name=op.f('uq_servicios_codigo')),
    schema='clinica_veterinaria'
    )
    op.create_table('productos',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('categoria_id', sa.BigInteger(), nullable=False),
    sa.Column('proveedor_id', sa.BigInteger(), nullable=False),
    sa.Column('sku', sa.String(length=50), nullable=False),
    sa.Column('nombre', sa.String(length=150), nullable=False),
    sa.Column('precio_venta', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('stock_actual', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('stock_minimo', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.CheckConstraint('precio_venta >= 0', name=op.f('ck_productos_precio')),
    sa.CheckConstraint('stock_actual >= 0', name=op.f('ck_productos_stock_actual')),
    sa.CheckConstraint('stock_minimo >= 0', name=op.f('ck_productos_stock_minimo')),
    sa.ForeignKeyConstraint(['categoria_id'], ['clinica_veterinaria.categorias_producto.id'], name=op.f('fk_productos_categoria_id_categorias_producto'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['proveedor_id'], ['clinica_veterinaria.proveedores.id'], name=op.f('fk_productos_proveedor_id_proveedores'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_productos')),
    sa.UniqueConstraint('sku', name=op.f('uq_productos_sku')),
    schema='clinica_veterinaria'
    )
    op.create_index('idx_productos_categoria', 'productos', ['categoria_id'], unique=False, schema='clinica_veterinaria')
    op.create_index('idx_productos_proveedor', 'productos', ['proveedor_id'], unique=False, schema='clinica_veterinaria')
    op.create_table('servicios_estetica',
    sa.Column('servicio_id', sa.BigInteger(), nullable=False),
    sa.Column('incluye_corte_pelo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('incluye_bano_especial', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('tipo_estetica', tipo_estetica, nullable=False),
    sa.ForeignKeyConstraint(['servicio_id'], ['clinica_veterinaria.servicios.id'], name=op.f('fk_servicios_estetica_servicio_id_servicios'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('servicio_id', name=op.f('pk_servicios_estetica')),
    schema='clinica_veterinaria'
    )
    op.create_table('servicios_medicos',
    sa.Column('servicio_id', sa.BigInteger(), nullable=False),
    sa.Column('requiere_receta', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('incluye_laboratorio', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('tipo_atencion_medica', tipo_atencion_medica, nullable=False),
    sa.ForeignKeyConstraint(['servicio_id'], ['clinica_veterinaria.servicios.id'], name=op.f('fk_servicios_medicos_servicio_id_servicios'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('servicio_id', name=op.f('pk_servicios_medicos')),
    schema='clinica_veterinaria'
    )
    op.create_table('cajas',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('cajero_id', sa.BigInteger(), nullable=False),
    sa.Column('fondo_inicial', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('total_ingresos_validados', sa.Numeric(precision=12, scale=2), server_default=sa.text('0'), nullable=False),
    sa.Column('estado_caja', sa.String(length=20), nullable=False),
    sa.CheckConstraint("estado_caja IN ('abierta', 'cerrada')", name=op.f('ck_cajas_estado')),
    sa.CheckConstraint('fondo_inicial >= 0', name=op.f('ck_cajas_fondo')),
    sa.CheckConstraint('total_ingresos_validados >= 0', name=op.f('ck_cajas_ingresos')),
    sa.ForeignKeyConstraint(['cajero_id'], ['clinica_veterinaria.cajeros.usuario_id'], name=op.f('fk_cajas_cajero_id_cajeros'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_cajas')),
    schema='clinica_veterinaria'
    )
    op.create_index('idx_cajas_cajero', 'cajas', ['cajero_id'], unique=False, schema='clinica_veterinaria')
    op.create_table('mascotas',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('cliente_id', sa.BigInteger(), nullable=False),
    sa.Column('nombre', sa.String(length=100), nullable=False),
    sa.Column('especie', sa.String(length=80), nullable=False),
    sa.Column('raza', sa.String(length=100), nullable=True),
    sa.ForeignKeyConstraint(['cliente_id'], ['clinica_veterinaria.clientes.usuario_id'], name=op.f('fk_mascotas_cliente_id_clientes'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_mascotas')),
    schema='clinica_veterinaria'
    )
    op.create_table('citas',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('mascota_id', sa.BigInteger(), nullable=False),
    sa.Column('servicio_id', sa.BigInteger(), nullable=False),
    sa.Column('fecha_hora_programada', sa.DateTime(timezone=True), nullable=False),
    sa.Column('estado', estado_cita, server_default=sa.text("'pendiente'"), nullable=False),
    sa.Column('es_urgente', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.ForeignKeyConstraint(['mascota_id'], ['clinica_veterinaria.mascotas.id'], name=op.f('fk_citas_mascota_id_mascotas'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['servicio_id'], ['clinica_veterinaria.servicios.id'], name=op.f('fk_citas_servicio_id_servicios'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_citas')),
    schema='clinica_veterinaria'
    )
    op.create_index('idx_citas_fecha', 'citas', ['fecha_hora_programada'], unique=False, schema='clinica_veterinaria')
    op.create_index('idx_citas_mascota', 'citas', ['mascota_id'], unique=False, schema='clinica_veterinaria')
    op.create_index('idx_citas_servicio', 'citas', ['servicio_id'], unique=False, schema='clinica_veterinaria')
    op.create_table('procesos_atencion',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('cita_id', sa.BigInteger(), nullable=False),
    sa.Column('mascota_id', sa.BigInteger(), nullable=False),
    sa.Column('tipo', tipo_proceso_atencion, nullable=False),
    sa.Column('fecha_inicio', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('fecha_fin', sa.DateTime(timezone=True), nullable=True),
    sa.Column('observaciones', sa.Text(), nullable=True),
    sa.CheckConstraint('fecha_fin IS NULL OR fecha_fin >= fecha_inicio', name=op.f('ck_procesos_atencion_fechas')),
    sa.ForeignKeyConstraint(['cita_id'], ['clinica_veterinaria.citas.id'], name=op.f('fk_procesos_atencion_cita_id_citas'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['mascota_id'], ['clinica_veterinaria.mascotas.id'], name=op.f('fk_procesos_atencion_mascota_id_mascotas'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_procesos_atencion')),
    sa.UniqueConstraint('cita_id', name=op.f('uq_procesos_atencion_cita_id')),
    schema='clinica_veterinaria'
    )
    op.create_index('idx_procesos_mascota', 'procesos_atencion', ['mascota_id'], unique=False, schema='clinica_veterinaria')
    op.create_table('ordenes_cobro',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('codigo_orden', sa.String(length=50), nullable=False),
    sa.Column('cajero_id', sa.BigInteger(), nullable=False),
    sa.Column('cliente_id', sa.BigInteger(), nullable=False),
    sa.Column('caja_id', sa.BigInteger(), nullable=False),
    sa.Column('proceso_atencion_id', sa.BigInteger(), nullable=True),
    sa.Column('monto_total', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('estado_pago', estado_pago, server_default=sa.text("'pendiente'"), nullable=False),
    sa.CheckConstraint('monto_total >= 0', name=op.f('ck_ordenes_cobro_monto')),
    sa.ForeignKeyConstraint(['caja_id'], ['clinica_veterinaria.cajas.id'], name=op.f('fk_ordenes_cobro_caja_id_cajas'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['cajero_id'], ['clinica_veterinaria.cajeros.usuario_id'], name=op.f('fk_ordenes_cobro_cajero_id_cajeros'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['cliente_id'], ['clinica_veterinaria.clientes.usuario_id'], name=op.f('fk_ordenes_cobro_cliente_id_clientes'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['proceso_atencion_id'], ['clinica_veterinaria.procesos_atencion.id'], name=op.f('fk_ordenes_cobro_proceso_atencion_id_procesos_atencion'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ordenes_cobro')),
    sa.UniqueConstraint('codigo_orden', name=op.f('uq_ordenes_cobro_codigo_orden')),
    schema='clinica_veterinaria'
    )
    op.create_index('idx_ordenes_caja', 'ordenes_cobro', ['caja_id'], unique=False, schema='clinica_veterinaria')
    op.create_index('idx_ordenes_cajero', 'ordenes_cobro', ['cajero_id'], unique=False, schema='clinica_veterinaria')
    op.create_index('idx_ordenes_cliente', 'ordenes_cobro', ['cliente_id'], unique=False, schema='clinica_veterinaria')
    op.create_table('procesos_atencion_estetica',
    sa.Column('proceso_id', sa.BigInteger(), nullable=False),
    sa.Column('notas_especiales_estilista', sa.Text(), nullable=True),
    sa.Column('productos_utilizados', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['proceso_id'], ['clinica_veterinaria.procesos_atencion.id'], name=op.f('fk_procesos_atencion_estetica_proceso_id_procesos_atencion'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('proceso_id', name=op.f('pk_procesos_atencion_estetica')),
    schema='clinica_veterinaria'
    )
    op.create_table('procesos_atencion_medica',
    sa.Column('proceso_id', sa.BigInteger(), nullable=False),
    sa.Column('veterinario_id', sa.BigInteger(), nullable=False),
    sa.Column('diagnostico', sa.Text(), nullable=True),
    sa.Column('tratamiento', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['proceso_id'], ['clinica_veterinaria.procesos_atencion.id'], name=op.f('fk_procesos_atencion_medica_proceso_id_procesos_atencion'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['veterinario_id'], ['clinica_veterinaria.veterinarios.usuario_id'], name=op.f('fk_procesos_atencion_medica_veterinario_id_veterinarios'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('proceso_id', name=op.f('pk_procesos_atencion_medica')),
    schema='clinica_veterinaria'
    )
    op.create_table('comprobantes_pago_whatsapp',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('orden_cobro_id', sa.BigInteger(), nullable=False),
    sa.Column('medio_pago', sa.String(length=80), nullable=False),
    sa.Column('codigo_operacion', sa.String(length=100), nullable=False),
    sa.Column('captura_imagen', sa.String(length=500), nullable=False),
    sa.ForeignKeyConstraint(['orden_cobro_id'], ['clinica_veterinaria.ordenes_cobro.id'], name=op.f('fk_comprobantes_pago_whatsapp_orden_cobro_id_ordenes_cobro'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_comprobantes_pago_whatsapp')),
    sa.UniqueConstraint('orden_cobro_id', name=op.f('uq_comprobantes_pago_whatsapp_orden_cobro_id')),
    schema='clinica_veterinaria'
    )
    op.create_table('comprobantes_venta',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('orden_cobro_id', sa.BigInteger(), nullable=False),
    sa.Column('serie_correlativo', sa.String(length=50), nullable=False),
    sa.Column('total_pagar', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.CheckConstraint('total_pagar >= 0', name=op.f('ck_comprobantes_venta_total')),
    sa.ForeignKeyConstraint(['orden_cobro_id'], ['clinica_veterinaria.ordenes_cobro.id'], name=op.f('fk_comprobantes_venta_orden_cobro_id_ordenes_cobro'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_comprobantes_venta')),
    sa.UniqueConstraint('orden_cobro_id', name=op.f('uq_comprobantes_venta_orden_cobro_id')),
    sa.UniqueConstraint('serie_correlativo', name=op.f('uq_comprobantes_venta_serie_correlativo')),
    schema='clinica_veterinaria'
    )
    op.create_table('fichas_clinicas',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('proceso_medico_id', sa.BigInteger(), nullable=False),
    sa.Column('peso', sa.Numeric(precision=7, scale=2), nullable=True),
    sa.Column('temperatura', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('historial_alergias', sa.Text(), nullable=True),
    sa.CheckConstraint('peso IS NULL OR peso >= 0', name=op.f('ck_fichas_clinicas_peso')),
    sa.CheckConstraint('temperatura IS NULL OR temperatura > 0', name=op.f('ck_fichas_clinicas_temperatura')),
    sa.ForeignKeyConstraint(['proceso_medico_id'], ['clinica_veterinaria.procesos_atencion_medica.proceso_id'], name=op.f('fk_fichas_clinicas_proceso_medico_id_procesos_atencion_medica'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_fichas_clinicas')),
    sa.UniqueConstraint('proceso_medico_id', name=op.f('uq_fichas_clinicas_proceso_medico_id')),
    schema='clinica_veterinaria'
    )
    op.create_table('examenes_medicos_adjuntos',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('ficha_clinica_id', sa.BigInteger(), nullable=False),
    sa.Column('tipo_examen', sa.String(length=100), nullable=False),
    sa.Column('archivo_ruta', sa.String(length=500), nullable=False),
    sa.ForeignKeyConstraint(['ficha_clinica_id'], ['clinica_veterinaria.fichas_clinicas.id'], name=op.f('fk_examenes_medicos_adjuntos_ficha_clinica_id_fichas_clinicas'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_examenes_medicos_adjuntos')),
    schema='clinica_veterinaria'
    )
    op.create_index('idx_examenes_ficha', 'examenes_medicos_adjuntos', ['ficha_clinica_id'], unique=False, schema='clinica_veterinaria')


def downgrade() -> None:
    op.drop_index('idx_examenes_ficha', table_name='examenes_medicos_adjuntos', schema='clinica_veterinaria')
    op.drop_table('examenes_medicos_adjuntos', schema='clinica_veterinaria')
    op.drop_table('fichas_clinicas', schema='clinica_veterinaria')
    op.drop_table('comprobantes_venta', schema='clinica_veterinaria')
    op.drop_table('comprobantes_pago_whatsapp', schema='clinica_veterinaria')
    op.drop_table('procesos_atencion_medica', schema='clinica_veterinaria')
    op.drop_table('procesos_atencion_estetica', schema='clinica_veterinaria')
    op.drop_index('idx_ordenes_cliente', table_name='ordenes_cobro', schema='clinica_veterinaria')
    op.drop_index('idx_ordenes_cajero', table_name='ordenes_cobro', schema='clinica_veterinaria')
    op.drop_index('idx_ordenes_caja', table_name='ordenes_cobro', schema='clinica_veterinaria')
    op.drop_table('ordenes_cobro', schema='clinica_veterinaria')
    op.drop_index('idx_procesos_mascota', table_name='procesos_atencion', schema='clinica_veterinaria')
    op.drop_table('procesos_atencion', schema='clinica_veterinaria')
    op.drop_index('idx_citas_servicio', table_name='citas', schema='clinica_veterinaria')
    op.drop_index('idx_citas_mascota', table_name='citas', schema='clinica_veterinaria')
    op.drop_index('idx_citas_fecha', table_name='citas', schema='clinica_veterinaria')
    op.drop_table('citas', schema='clinica_veterinaria')
    op.drop_table('mascotas', schema='clinica_veterinaria')
    op.drop_index('idx_cajas_cajero', table_name='cajas', schema='clinica_veterinaria')
    op.drop_table('cajas', schema='clinica_veterinaria')
    op.drop_table('servicios_medicos', schema='clinica_veterinaria')
    op.drop_table('servicios_estetica', schema='clinica_veterinaria')
    op.drop_index('idx_productos_proveedor', table_name='productos', schema='clinica_veterinaria')
    op.drop_index('idx_productos_categoria', table_name='productos', schema='clinica_veterinaria')
    op.drop_table('productos', schema='clinica_veterinaria')
    op.drop_table('servicios', schema='clinica_veterinaria')
    op.drop_table('proveedores', schema='clinica_veterinaria')
    op.drop_table('categorias_producto', schema='clinica_veterinaria')
    bind = op.get_bind()
    for enum_type in (
        estado_pago,
        tipo_proceso_atencion,
        tipo_estetica,
        tipo_atencion_medica,
        estado_cita,
    ):
        enum_type.drop(bind, checkfirst=True)
