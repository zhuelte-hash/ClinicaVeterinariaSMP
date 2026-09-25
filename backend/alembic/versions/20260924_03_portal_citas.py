"""Agrega agenda de citas y catalogo inicial.

Revision ID: 20260924_03
Revises: 20260924_02
Create Date: 2026-09-24
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260924_03"
down_revision: str | None = "20260924_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "clinica_veterinaria"


def upgrade() -> None:
    op.add_column("citas", sa.Column("motivo", sa.String(500)), schema=SCHEMA)
    op.add_column(
        "citas",
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "uq_citas_horario_activo",
        "citas",
        ["fecha_hora_programada"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("estado NOT IN ('cancelada', 'no_asistio')"),
    )

    op.execute(sa.text(f"""
        INSERT INTO {SCHEMA}.servicios
            (codigo, nombre, descripcion, precio_referencial, duracion_estimada_min)
        VALUES
            ('consultas-veterinarias', 'Consulta veterinaria', 'Evaluacion clinica integral.', 50.00, 30),
            ('vacunacion', 'Vacunacion', 'Aplicacion y control del calendario de vacunas.', 45.00, 30),
            ('desparasitacion', 'Desparasitacion', 'Prevencion de parasitos internos y externos.', 35.00, 30),
            ('cirugia-general', 'Cirugia general', 'Evaluacion y procedimiento quirurgico programado.', 200.00, 90),
            ('laboratorio-clinico', 'Laboratorio clinico', 'Analisis para apoyo diagnostico.', 80.00, 45),
            ('bano-simple', 'Bano estetico', 'Higiene general para la mascota.', 40.00, 60),
            ('bano-medicado', 'Bano medicado', 'Bano con productos dermatologicos indicados.', 55.00, 60),
            ('corte-y-estilizado', 'Corte y estilizado', 'Corte de pelo y arreglo estetico.', 60.00, 90)
        ON CONFLICT (codigo) DO NOTHING
    """))
    op.execute(sa.text(f"""
        INSERT INTO {SCHEMA}.servicios_medicos
            (servicio_id, requiere_receta, incluye_laboratorio, tipo_atencion_medica)
        SELECT id, false, codigo = 'laboratorio-clinico',
            CASE codigo
                WHEN 'vacunacion' THEN 'vacunacion'::{SCHEMA}.tipo_atencion_medica
                WHEN 'desparasitacion' THEN 'desparasitacion'::{SCHEMA}.tipo_atencion_medica
                WHEN 'cirugia-general' THEN 'cirugia'::{SCHEMA}.tipo_atencion_medica
                WHEN 'laboratorio-clinico' THEN 'laboratorio_e_imagen'::{SCHEMA}.tipo_atencion_medica
                ELSE 'consulta_general'::{SCHEMA}.tipo_atencion_medica
            END
        FROM {SCHEMA}.servicios
        WHERE codigo IN (
            'consultas-veterinarias', 'vacunacion', 'desparasitacion',
            'cirugia-general', 'laboratorio-clinico'
        )
        ON CONFLICT (servicio_id) DO NOTHING
    """))
    op.execute(sa.text(f"""
        INSERT INTO {SCHEMA}.servicios_estetica
            (servicio_id, incluye_corte_pelo, incluye_bano_especial, tipo_estetica)
        SELECT id, codigo = 'corte-y-estilizado', codigo = 'bano-medicado',
            CASE codigo
                WHEN 'bano-medicado' THEN 'bano_medicado'::{SCHEMA}.tipo_estetica
                WHEN 'corte-y-estilizado' THEN 'corte_y_estilizado'::{SCHEMA}.tipo_estetica
                ELSE 'bano_simple'::{SCHEMA}.tipo_estetica
            END
        FROM {SCHEMA}.servicios
        WHERE codigo IN ('bano-simple', 'bano-medicado', 'corte-y-estilizado')
        ON CONFLICT (servicio_id) DO NOTHING
    """))


def downgrade() -> None:
    op.drop_index(
        "uq_citas_horario_activo",
        table_name="citas",
        schema=SCHEMA,
    )
    op.drop_column("citas", "fecha_creacion", schema=SCHEMA)
    op.drop_column("citas", "motivo", schema=SCHEMA)
