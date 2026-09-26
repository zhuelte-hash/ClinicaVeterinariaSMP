import datetime
import enum
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, SCHEMA


class EstadoCita(str, enum.Enum):
    PENDIENTE = "pendiente"
    PENDIENTE_CONTACTO = "pendiente_contacto"
    CONTACTANDO_CLIENTE = "contactando_cliente"
    ESPERANDO_RESPUESTA = "esperando_respuesta"
    REQUIERE_OTRO_HORARIO = "requiere_otro_horario"
    CLIENTE_NO_RESPONDIO = "cliente_no_respondio"
    CONFIRMADA = "confirmada"
    REPROGRAMADA = "reprogramada"
    ATENDIDA = "atendida"
    CANCELADA = "cancelada"
    NO_ASISTIO = "no_asistio"


class TipoAtencionMedica(str, enum.Enum):
    CONSULTA_GENERAL = "consulta_general"
    CIRUGIA = "cirugia"
    VACUNACION = "vacunacion"
    DESPARASITACION = "desparasitacion"
    LABORATORIO_E_IMAGEN = "laboratorio_e_imagen"


class TipoEstetica(str, enum.Enum):
    BANO_SIMPLE = "bano_simple"
    BANO_MEDICADO = "bano_medicado"
    CORTE_Y_ESTILIZADO = "corte_y_estilizado"
    CORTE_DE_UNAS_Y_LIMPIEZA_OIDOS = "corte_de_unas_y_limpieza_oidos"


class TipoProcesoAtencion(str, enum.Enum):
    MEDICA = "medica"
    ESTETICA = "estetica"


class EstadoPago(str, enum.Enum):
    PENDIENTE = "pendiente"
    PAGO_ENVIADO = "pago_enviado"
    VALIDADO_CONFIRMADO = "validado_confirmado"
    ANULADO = "anulado"


def _enum_type(enum_class: type[enum.Enum], name: str) -> Enum:
    return Enum(
        enum_class,
        name=name,
        schema=SCHEMA,
        values_callable=lambda items: [item.value for item in items],
    )


estado_cita_db = _enum_type(EstadoCita, "estado_cita")
tipo_atencion_medica_db = _enum_type(TipoAtencionMedica, "tipo_atencion_medica")
tipo_estetica_db = _enum_type(TipoEstetica, "tipo_estetica")
tipo_proceso_atencion_db = _enum_type(TipoProcesoAtencion, "tipo_proceso_atencion")
estado_pago_db = _enum_type(EstadoPago, "estado_pago")


class Mascota(Base):
    __tablename__ = "mascotas"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.clientes.usuario_id", ondelete="RESTRICT"),
        nullable=False,
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    especie: Mapped[str] = mapped_column(String(80), nullable=False)
    raza: Mapped[str | None] = mapped_column(String(100))
    sexo: Mapped[str | None] = mapped_column(String(20))
    fecha_nacimiento: Mapped[datetime.date | None] = mapped_column(Date)
    peso_actual: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    caracteristicas: Mapped[str | None] = mapped_column(Text)

    cliente: Mapped["Cliente"] = relationship(back_populates="mascotas")
    citas: Mapped[list["Cita"]] = relationship(back_populates="mascota")
    procesos_atencion: Mapped[list["ProcesoAtencion"]] = relationship(
        back_populates="mascota"
    )


class Servicio(Base):
    __tablename__ = "servicios"
    __table_args__ = (
        CheckConstraint("precio_referencial >= 0", name="precio"),
        CheckConstraint("duracion_estimada_min > 0", name="duracion"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    precio_referencial: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    duracion_estimada_min: Mapped[int] = mapped_column(Integer, nullable=False)

    medico: Mapped["ServicioMedico | None"] = relationship(
        back_populates="servicio", cascade="all, delete-orphan", uselist=False
    )
    estetica: Mapped["ServicioEstetica | None"] = relationship(
        back_populates="servicio", cascade="all, delete-orphan", uselist=False
    )
    citas: Mapped[list["Cita"]] = relationship(back_populates="servicio")
    detalles_venta: Mapped[list["DetalleOrdenCobro"]] = relationship(
        back_populates="servicio"
    )


class ServicioMedico(Base):
    __tablename__ = "servicios_medicos"
    __table_args__ = {"schema": SCHEMA}

    servicio_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.servicios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    requiere_receta: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    incluye_laboratorio: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    tipo_atencion_medica: Mapped[TipoAtencionMedica] = mapped_column(
        tipo_atencion_medica_db, nullable=False
    )

    servicio: Mapped[Servicio] = relationship(back_populates="medico")


class ServicioEstetica(Base):
    __tablename__ = "servicios_estetica"
    __table_args__ = {"schema": SCHEMA}

    servicio_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.servicios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    incluye_corte_pelo: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    incluye_bano_especial: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    tipo_estetica: Mapped[TipoEstetica] = mapped_column(tipo_estetica_db, nullable=False)

    servicio: Mapped[Servicio] = relationship(back_populates="estetica")


class Cita(Base):
    __tablename__ = "citas"
    __table_args__ = (
        Index("idx_citas_mascota", "mascota_id"),
        Index("idx_citas_servicio", "servicio_id"),
        Index("idx_citas_fecha", "fecha_hora_programada"),
        Index("idx_citas_veterinario_estado", "veterinario_id", "estado"),
        UniqueConstraint("id", "mascota_id", name="uq_citas_id_mascota"),
        Index(
            "uq_citas_horario_activo",
            "veterinario_id",
            "fecha_hora_programada",
            unique=True,
            postgresql_where=text(
                "veterinario_id IS NOT NULL AND estado NOT IN "
                "('cancelada', 'no_asistio')"
            ),
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    mascota_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.mascotas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    servicio_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.servicios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    fecha_hora_programada: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    fecha_hora_fin_programada: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    estado: Mapped[EstadoCita] = mapped_column(
        estado_cita_db, server_default=text("'pendiente'"), nullable=False
    )
    es_urgente: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    motivo: Mapped[str | None] = mapped_column(String(500))
    fecha_creacion: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    veterinario_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey(f"{SCHEMA}.veterinarios.usuario_id", ondelete="RESTRICT")
    )
    fecha_hora_propuesta: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    telefono_contacto: Mapped[str | None] = mapped_column(String(30))
    preferencia_contacto: Mapped[str | None] = mapped_column(String(20))
    nota_coordinacion: Mapped[str | None] = mapped_column(String(500))
    estado_actualizado_por: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey(f"{SCHEMA}.usuarios.id", ondelete="SET NULL")
    )
    fecha_actualizacion: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    mascota: Mapped[Mascota] = relationship(back_populates="citas")
    servicio: Mapped[Servicio] = relationship(back_populates="citas")
    veterinario: Mapped["Veterinario | None"] = relationship(back_populates="citas")
    estado_actualizado_por_usuario: Mapped["Usuario | None"] = relationship(
        foreign_keys=[estado_actualizado_por]
    )
    proceso_atencion: Mapped["ProcesoAtencion | None"] = relationship(
        back_populates="cita", uselist=False, overlaps="procesos_atencion,mascota"
    )


class HorarioVeterinario(Base):
    __tablename__ = "horarios_veterinarios"
    __table_args__ = (
        CheckConstraint("dia_semana BETWEEN 0 AND 6", name="dia_semana"),
        CheckConstraint("hora_fin > hora_inicio", name="horas"),
        UniqueConstraint(
            "veterinario_id", "dia_semana", "hora_inicio", "hora_fin",
            name="uq_horario_veterinario_rango",
        ),
        Index("idx_horarios_veterinario", "veterinario_id", "dia_semana"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    veterinario_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.veterinarios.usuario_id", ondelete="CASCADE"),
        nullable=False,
    )
    dia_semana: Mapped[int] = mapped_column(Integer, nullable=False)
    hora_inicio: Mapped[datetime.time] = mapped_column(Time, nullable=False)
    hora_fin: Mapped[datetime.time] = mapped_column(Time, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)

    veterinario: Mapped["Veterinario"] = relationship(back_populates="horarios")


class BloqueoHorario(Base):
    __tablename__ = "bloqueos_horario"
    __table_args__ = (
        CheckConstraint("fecha_hora_fin > fecha_hora_inicio", name="horas"),
        Index("idx_bloqueos_veterinario_fecha", "veterinario_id", "fecha_hora_inicio"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    veterinario_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.veterinarios.usuario_id", ondelete="CASCADE"),
        nullable=False,
    )
    fecha_hora_inicio: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    fecha_hora_fin: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    motivo: Mapped[str] = mapped_column(String(255), nullable=False)

    veterinario: Mapped["Veterinario"] = relationship(back_populates="bloqueos")


class ProcesoAtencion(Base):
    __tablename__ = "procesos_atencion"
    __table_args__ = (
        ForeignKeyConstraint(
            ["cita_id", "mascota_id"],
            [f"{SCHEMA}.citas.id", f"{SCHEMA}.citas.mascota_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "fecha_fin IS NULL OR fecha_fin >= fecha_inicio", name="fechas"
        ),
        Index("idx_procesos_mascota", "mascota_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    cita_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=True,
    )
    mascota_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.mascotas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tipo: Mapped[TipoProcesoAtencion] = mapped_column(
        tipo_proceso_atencion_db, nullable=False
    )
    fecha_inicio: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    fecha_fin: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    observaciones: Mapped[str | None] = mapped_column(Text)
    motivo_consulta: Mapped[str | None] = mapped_column(Text)
    anamnesis: Mapped[str | None] = mapped_column(Text)
    proxima_fecha_control: Mapped[datetime.date | None] = mapped_column(Date)

    cita: Mapped[Cita] = relationship(
        back_populates="proceso_atencion", overlaps="procesos_atencion,mascota"
    )
    mascota: Mapped[Mascota] = relationship(
        back_populates="procesos_atencion", overlaps="cita,proceso_atencion"
    )
    proceso_medico: Mapped["ProcesoAtencionMedica | None"] = relationship(
        back_populates="proceso", cascade="all, delete-orphan", uselist=False
    )
    proceso_estetica: Mapped["ProcesoAtencionEstetica | None"] = relationship(
        back_populates="proceso", cascade="all, delete-orphan", uselist=False
    )
    ordenes_cobro: Mapped[list["OrdenCobro"]] = relationship(
        back_populates="proceso_atencion", passive_deletes=True
    )


class ProcesoAtencionMedica(Base):
    __tablename__ = "procesos_atencion_medica"
    __table_args__ = {"schema": SCHEMA}

    proceso_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.procesos_atencion.id", ondelete="CASCADE"),
        primary_key=True,
    )
    veterinario_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.veterinarios.usuario_id", ondelete="RESTRICT"),
        nullable=False,
    )
    diagnostico: Mapped[str | None] = mapped_column(Text)
    tratamiento: Mapped[str | None] = mapped_column(Text)

    proceso: Mapped[ProcesoAtencion] = relationship(back_populates="proceso_medico")
    veterinario: Mapped["Veterinario"] = relationship(back_populates="procesos_medicos")
    ficha_clinica: Mapped["FichaClinica | None"] = relationship(
        back_populates="proceso_medico", cascade="all, delete-orphan", uselist=False
    )


class ProcesoAtencionEstetica(Base):
    __tablename__ = "procesos_atencion_estetica"
    __table_args__ = {"schema": SCHEMA}

    proceso_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.procesos_atencion.id", ondelete="CASCADE"),
        primary_key=True,
    )
    notas_especiales_estilista: Mapped[str | None] = mapped_column(Text)
    productos_utilizados: Mapped[str | None] = mapped_column(Text)

    proceso: Mapped[ProcesoAtencion] = relationship(back_populates="proceso_estetica")


class FichaClinica(Base):
    __tablename__ = "fichas_clinicas"
    __table_args__ = (
        CheckConstraint("peso IS NULL OR peso >= 0", name="peso"),
        CheckConstraint("temperatura IS NULL OR temperatura > 0", name="temperatura"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    proceso_medico_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{SCHEMA}.procesos_atencion_medica.proceso_id", ondelete="CASCADE"
        ),
        unique=True,
        nullable=False,
    )
    peso: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    temperatura: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    historial_alergias: Mapped[str | None] = mapped_column(Text)
    vacunas: Mapped[str | None] = mapped_column(Text)
    desparasitaciones: Mapped[str | None] = mapped_column(Text)
    medicamentos: Mapped[str | None] = mapped_column(Text)
    procedimientos: Mapped[str | None] = mapped_column(Text)
    examenes_resultados: Mapped[str | None] = mapped_column(Text)

    proceso_medico: Mapped[ProcesoAtencionMedica] = relationship(
        back_populates="ficha_clinica"
    )
    examenes: Mapped[list["ExamenMedicoAdjunto"]] = relationship(
        back_populates="ficha_clinica", cascade="all, delete-orphan"
    )


class Notificacion(Base):
    __tablename__ = "notificaciones"
    __table_args__ = (
        Index("idx_notificaciones_usuario_leida", "usuario_id", "leida"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.usuarios.id", ondelete="CASCADE"),
        nullable=False,
    )
    cita_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey(f"{SCHEMA}.citas.id", ondelete="SET NULL")
    )
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    mensaje: Mapped[str] = mapped_column(String(500), nullable=False)
    leida: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    fecha_creacion: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    usuario: Mapped["Usuario"] = relationship(back_populates="notificaciones")
    cita: Mapped["Cita | None"] = relationship()


class ExamenMedicoAdjunto(Base):
    __tablename__ = "examenes_medicos_adjuntos"
    __table_args__ = (
        Index("idx_examenes_ficha", "ficha_clinica_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    ficha_clinica_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.fichas_clinicas.id", ondelete="CASCADE"),
        nullable=False,
    )
    tipo_examen: Mapped[str] = mapped_column(String(100), nullable=False)
    archivo_ruta: Mapped[str] = mapped_column(String(500), nullable=False)

    ficha_clinica: Mapped[FichaClinica] = relationship(back_populates="examenes")


class CategoriaProducto(Base):
    __tablename__ = "categorias_producto"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    productos: Mapped[list["Producto"]] = relationship(back_populates="categoria")


class Proveedor(Base):
    __tablename__ = "proveedores"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    razon_social: Mapped[str] = mapped_column(String(180), nullable=False)

    productos: Mapped[list["Producto"]] = relationship(back_populates="proveedor")


class Producto(Base):
    __tablename__ = "productos"
    __table_args__ = (
        CheckConstraint("precio_venta >= 0", name="precio"),
        CheckConstraint("stock_actual >= 0", name="stock_actual"),
        CheckConstraint("stock_minimo >= 0", name="stock_minimo"),
        Index("idx_productos_categoria", "categoria_id"),
        Index("idx_productos_proveedor", "proveedor_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    categoria_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.categorias_producto.id", ondelete="RESTRICT"),
        nullable=False,
    )
    proveedor_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.proveedores.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    precio_venta: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    stock_actual: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False
    )
    stock_minimo: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False
    )

    categoria: Mapped[CategoriaProducto] = relationship(back_populates="productos")
    proveedor: Mapped[Proveedor] = relationship(back_populates="productos")
    detalles_venta: Mapped[list["DetalleOrdenCobro"]] = relationship(
        back_populates="producto"
    )


class Caja(Base):
    __tablename__ = "cajas"
    __table_args__ = (
        CheckConstraint("fondo_inicial >= 0", name="fondo"),
        CheckConstraint("total_ingresos_validados >= 0", name="ingresos"),
        CheckConstraint("estado_caja IN ('abierta', 'cerrada')", name="estado"),
        Index("idx_cajas_cajero", "cajero_id"),
        Index(
            "uq_cajas_cajero_abierta",
            "cajero_id",
            unique=True,
            postgresql_where=text("estado_caja = 'abierta'"),
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    cajero_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.cajeros.usuario_id", ondelete="RESTRICT"),
        nullable=False,
    )
    fondo_inicial: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_ingresos_validados: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), server_default=text("0"), nullable=False
    )
    estado_caja: Mapped[str] = mapped_column(String(20), nullable=False)

    cajero: Mapped["Cajero"] = relationship(back_populates="cajas")
    ordenes_cobro: Mapped[list["OrdenCobro"]] = relationship(back_populates="caja")


class OrdenCobro(Base):
    __tablename__ = "ordenes_cobro"
    __table_args__ = (
        CheckConstraint("monto_total >= 0", name="monto"),
        CheckConstraint(
            "medio_pago IS NULL OR medio_pago IN ('efectivo', 'yape', 'plin', 'tarjeta')",
            name="medio_pago",
        ),
        Index("idx_ordenes_cajero", "cajero_id"),
        Index("idx_ordenes_cliente", "cliente_id"),
        Index("idx_ordenes_caja", "caja_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo_orden: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    cajero_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.cajeros.usuario_id", ondelete="RESTRICT"),
        nullable=False,
    )
    cliente_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.clientes.usuario_id", ondelete="RESTRICT"),
        nullable=False,
    )
    caja_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.cajas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    proceso_atencion_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.procesos_atencion.id", ondelete="SET NULL"),
    )
    monto_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    estado_pago: Mapped[EstadoPago] = mapped_column(
        estado_pago_db, server_default=text("'pendiente'"), nullable=False
    )
    medio_pago: Mapped[str | None] = mapped_column(String(30))

    cajero: Mapped["Cajero"] = relationship(back_populates="ordenes_cobro")
    cliente: Mapped["Cliente"] = relationship(back_populates="ordenes_cobro")
    caja: Mapped[Caja] = relationship(back_populates="ordenes_cobro")
    proceso_atencion: Mapped[ProcesoAtencion | None] = relationship(
        back_populates="ordenes_cobro"
    )
    comprobante_pago_whatsapp: Mapped["ComprobantePagoWhatsApp | None"] = relationship(
        back_populates="orden_cobro", cascade="all, delete-orphan", uselist=False
    )
    comprobante_venta: Mapped["ComprobanteVenta | None"] = relationship(
        back_populates="orden_cobro", uselist=False
    )
    detalles: Mapped[list["DetalleOrdenCobro"]] = relationship(
        back_populates="orden_cobro", cascade="all, delete-orphan"
    )


class DetalleOrdenCobro(Base):
    __tablename__ = "detalles_orden_cobro"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="cantidad"),
        CheckConstraint("precio_unitario >= 0", name="precio"),
        CheckConstraint("subtotal >= 0", name="subtotal"),
        CheckConstraint(
            "(producto_id IS NOT NULL) <> (servicio_id IS NOT NULL)", name="item"
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    orden_cobro_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.ordenes_cobro.id", ondelete="CASCADE"),
        nullable=False,
    )
    producto_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.productos.id", ondelete="RESTRICT"),
    )
    servicio_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.servicios.id", ondelete="RESTRICT"),
    )
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    orden_cobro: Mapped[OrdenCobro] = relationship(back_populates="detalles")
    producto: Mapped[Producto | None] = relationship(back_populates="detalles_venta")
    servicio: Mapped[Servicio | None] = relationship(back_populates="detalles_venta")


class ComprobantePagoWhatsApp(Base):
    __tablename__ = "comprobantes_pago_whatsapp"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    orden_cobro_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.ordenes_cobro.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    medio_pago: Mapped[str] = mapped_column(String(80), nullable=False)
    codigo_operacion: Mapped[str] = mapped_column(String(100), nullable=False)
    captura_imagen: Mapped[str] = mapped_column(String(500), nullable=False)

    orden_cobro: Mapped[OrdenCobro] = relationship(
        back_populates="comprobante_pago_whatsapp"
    )


class ComprobanteVenta(Base):
    __tablename__ = "comprobantes_venta"
    __table_args__ = (
        CheckConstraint("total_pagar >= 0", name="total"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    orden_cobro_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.ordenes_cobro.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    serie_correlativo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    total_pagar: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fecha_emision: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    orden_cobro: Mapped[OrdenCobro] = relationship(back_populates="comprobante_venta")
