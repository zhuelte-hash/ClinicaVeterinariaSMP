"""Persistencia de cuentas, coordinación, mensajería y operaciones de la clínica."""
import datetime as dt
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Identity, Integer, JSON, LargeBinary, Numeric, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, SCHEMA


def identity():
    return mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(always=True), primary_key=True)


def reference(table, nullable=False, **kwargs):
    return mapped_column(BigInteger, ForeignKey(f"{SCHEMA}.{table}", ondelete="RESTRICT"), nullable=nullable, **kwargs)


def created():
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Sucursal(Base):
    __tablename__ = "sucursales"
    __table_args__ = {"schema": SCHEMA}
    id: Mapped[int] = identity()
    nombre: Mapped[str] = mapped_column(String(150), unique=True)
    direccion: Mapped[str] = mapped_column(String(250), default="", server_default="")
    telefono: Mapped[str] = mapped_column(String(30), default="", server_default="")
    activa: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))


class DesafioCuenta(Base):
    __tablename__ = "desafios_cuenta"
    __table_args__ = {"schema": SCHEMA}
    id: Mapped[int] = identity()
    usuario_id: Mapped[int] = reference("usuarios.id")
    proposito: Mapped[str] = mapped_column(String(20))
    secreto_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expira_en: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    usado_en: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    intentos: Mapped[int] = mapped_column(Integer, default=0)
    creado_en: Mapped[dt.datetime] = created()


class PoliticaClinica(Base):
    __tablename__ = "politicas_clinica"
    __table_args__ = {"schema": SCHEMA}
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    horarios: Mapped[list] = mapped_column(JSON, default=list)
    excepciones: Mapped[list] = mapped_column(JSON, default=list)
    galeria: Mapped[list] = mapped_column(JSON, default=list)
    horas_cancelacion: Mapped[int] = mapped_column(Integer, default=4)
    horas_reprogramacion: Mapped[int] = mapped_column(Integer, default=4)
    dias_alerta_vencimiento: Mapped[int] = mapped_column(Integer, default=30)
    dias_recordatorio_vacuna: Mapped[int] = mapped_column(Integer, default=3)


class EventoAuditoria(Base):
    __tablename__ = "eventos_auditoria"
    __table_args__ = {"schema": SCHEMA}
    id: Mapped[int] = identity()
    usuario_id: Mapped[int | None] = reference("usuarios.id", nullable=True)
    sucursal_id: Mapped[int | None] = reference("sucursales.id", nullable=True)
    entidad: Mapped[str] = mapped_column(String(80))
    registro_id: Mapped[str] = mapped_column(String(80))
    accion: Mapped[str] = mapped_column(String(30))
    cambios: Mapped[dict] = mapped_column(JSON, default=dict)
    fecha: Mapped[dt.datetime] = created()


class EventoCita(Base):
    __tablename__ = "eventos_cita"
    __table_args__ = {"schema": SCHEMA}
    id: Mapped[int] = identity()
    cita_id: Mapped[int] = reference("citas.id")
    usuario_id: Mapped[int | None] = reference("usuarios.id", nullable=True)
    accion: Mapped[str] = mapped_column(String(40))
    anterior: Mapped[dict] = mapped_column(JSON, default=dict)
    actual: Mapped[dict] = mapped_column(JSON, default=dict)
    motivo: Mapped[str | None] = mapped_column(String(500))
    fecha: Mapped[dt.datetime] = created()


class SolicitudReprogramacion(Base):
    __tablename__ = "solicitudes_reprogramacion"
    __table_args__ = {"schema": SCHEMA}
    id: Mapped[int] = identity()
    cita_id: Mapped[int] = reference("citas.id")
    cliente_id: Mapped[int] = reference("clientes.usuario_id")
    fecha_propuesta: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    motivo: Mapped[str] = mapped_column(String(500))
    canal: Mapped[str] = mapped_column(String(20), default="web")
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")
    fecha: Mapped[dt.datetime] = created()


class DerivacionClinica(Base):
    __tablename__ = "derivaciones_clinicas"
    __table_args__ = {"schema": SCHEMA}
    id: Mapped[int] = identity()
    proceso_id: Mapped[int] = reference("procesos_atencion.id")
    remitente_id: Mapped[int] = reference("veterinarios.usuario_id")
    receptor_id: Mapped[int] = reference("veterinarios.usuario_id")
    motivo: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")
    respuesta: Mapped[str | None] = mapped_column(Text)
    aceptada_en: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    fecha: Mapped[dt.datetime] = created()


class PlantillaMensaje(Base):
    __tablename__ = "plantillas_mensaje"
    __table_args__ = {"schema": SCHEMA}
    id: Mapped[int] = identity()
    evento: Mapped[str] = mapped_column(String(80), unique=True)
    nombre_proveedor: Mapped[str] = mapped_column(String(150), default="")
    idioma: Mapped[str] = mapped_column(String(10), default="es_PE")
    contenido: Mapped[str] = mapped_column(Text)
    variables: Mapped[list] = mapped_column(JSON, default=list)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class MensajeSalida(Base):
    __tablename__ = "mensajes_salida"
    __table_args__ = {"schema": SCHEMA}
    id: Mapped[int] = identity()
    clave: Mapped[str] = mapped_column(String(200), unique=True)
    canal: Mapped[str] = mapped_column(String(20))
    evento: Mapped[str] = mapped_column(String(80))
    destinatario: Mapped[str] = mapped_column(String(254))
    usuario_id: Mapped[int | None] = reference("usuarios.id", nullable=True)
    entidad_id: Mapped[int | None] = mapped_column(BigInteger)
    asunto: Mapped[str | None] = mapped_column(String(200))
    contenido: Mapped[str] = mapped_column(Text)
    parametros: Mapped[list] = mapped_column(JSON, default=list)
    documento: Mapped[bytes | None] = mapped_column(LargeBinary)
    documento_nombre: Mapped[str | None] = mapped_column(String(150))
    estado: Mapped[str] = mapped_column(String(30), default="pendiente")
    intentos: Mapped[int] = mapped_column(Integer, default=0)
    proximo_intento: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    proveedor_id: Mapped[str | None] = mapped_column(String(150), index=True)
    error: Mapped[str | None] = mapped_column(String(500))
    fecha: Mapped[dt.datetime] = created()
    enviado_en: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    entregado_en: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class MensajeEntrante(Base):
    __tablename__ = "mensajes_entrantes"
    __table_args__ = {"schema": SCHEMA}
    id: Mapped[int] = identity()
    proveedor_id: Mapped[str] = mapped_column(String(150), unique=True)
    telefono: Mapped[str] = mapped_column(String(30))
    contenido: Mapped[str] = mapped_column(Text)
    resultado: Mapped[str] = mapped_column(String(500), default="recibido")
    fecha: Mapped[dt.datetime] = created()


class EncuestaConsulta(Base):
    __tablename__ = "encuestas_consulta"
    __table_args__ = (CheckConstraint("valoracion IS NULL OR valoracion BETWEEN 1 AND 5", name="valoracion"), {"schema": SCHEMA})
    id: Mapped[int] = identity()
    proceso_id: Mapped[int] = reference("procesos_atencion.id", unique=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expira_en: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    valoracion: Mapped[int | None] = mapped_column(Integer)
    comentario: Mapped[str | None] = mapped_column(String(2000))
    respondida_en: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    fecha: Mapped[dt.datetime] = created()


class UnidadMedida(Base):
    __tablename__ = "unidades_medida"
    __table_args__ = {"schema": SCHEMA}
    codigo: Mapped[str] = mapped_column(String(15), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80))
    dimension: Mapped[str] = mapped_column(String(20))
    factor_base: Mapped[Decimal] = mapped_column(Numeric(14, 6), default=1)
    fraccionable: Mapped[bool] = mapped_column(Boolean, default=False)


class LoteInventario(Base):
    __tablename__ = "lotes_inventario"
    __table_args__ = (CheckConstraint("cantidad >= 0 AND costo_unitario >= 0", name="cantidades"), UniqueConstraint("producto_id", "codigo", name="uq_lote_producto_codigo"), {"schema": SCHEMA})
    id: Mapped[int] = identity()
    producto_id: Mapped[int] = reference("productos.id")
    codigo: Mapped[str] = mapped_column(String(100))
    vencimiento: Mapped[dt.date | None] = mapped_column(Date)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    fecha: Mapped[dt.datetime] = created()


class CompraProveedor(Base):
    __tablename__ = "compras_proveedor"
    __table_args__ = (UniqueConstraint("proveedor_id", "documento", name="uq_compra_proveedor_documento"), {"schema": SCHEMA})
    id: Mapped[int] = identity()
    proveedor_id: Mapped[int] = reference("proveedores.id")
    usuario_id: Mapped[int] = reference("usuarios.id")
    sucursal_id: Mapped[int] = reference("sucursales.id")
    documento: Mapped[str] = mapped_column(String(100))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    detalles: Mapped[list] = mapped_column(JSON)
    fecha: Mapped[dt.datetime] = created()


class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"
    __table_args__ = {"schema": SCHEMA}
    id: Mapped[int] = identity()
    producto_id: Mapped[int] = reference("productos.id")
    lote_id: Mapped[int | None] = reference("lotes_inventario.id", nullable=True)
    usuario_id: Mapped[int | None] = reference("usuarios.id", nullable=True)
    tipo: Mapped[str] = mapped_column(String(30))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    saldo_anterior: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    saldo_nuevo: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    motivo: Mapped[str] = mapped_column(String(500))
    referencia: Mapped[str | None] = mapped_column(String(100))
    fecha: Mapped[dt.datetime] = created()


class Egreso(Base):
    __tablename__ = "egresos"
    __table_args__ = (CheckConstraint("monto > 0", name="monto"), {"schema": SCHEMA})
    id: Mapped[int] = identity()
    usuario_id: Mapped[int] = reference("usuarios.id")
    sucursal_id: Mapped[int] = reference("sucursales.id")
    categoria: Mapped[str] = mapped_column(String(80))
    concepto: Mapped[str] = mapped_column(String(500))
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    fecha: Mapped[dt.date] = mapped_column(Date)
    compra_id: Mapped[int | None] = reference("compras_proveedor.id", nullable=True, unique=True)


class AutorizacionDescuento(Base):
    __tablename__ = "autorizaciones_descuento"
    __table_args__ = (CheckConstraint("monto > 0", name="monto"), {"schema": SCHEMA})
    id: Mapped[int] = identity()
    solicitante_id: Mapped[int] = reference("usuarios.id")
    aprobador_id: Mapped[int | None] = reference("usuarios.id", nullable=True)
    cliente_id: Mapped[int | None] = reference("clientes.usuario_id", nullable=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    motivo: Mapped[str] = mapped_column(String(500))
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")
    usada: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha: Mapped[dt.datetime] = created()


class OrdenPendiente(Base):
    __tablename__ = "ordenes_pendientes"
    __table_args__ = (CheckConstraint("total > 0 AND descuento >= 0", name="importes"), {"schema": SCHEMA})
    id: Mapped[int] = identity()
    codigo: Mapped[str] = mapped_column(String(50), unique=True)
    cliente_id: Mapped[int] = reference("clientes.usuario_id")
    creador_id: Mapped[int] = reference("usuarios.id")
    sucursal_id: Mapped[int] = reference("sucursales.id")
    proceso_id: Mapped[int | None] = reference("procesos_atencion.id", nullable=True, unique=True)
    detalles: Mapped[list] = mapped_column(JSON)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    descuento: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    autorizacion_id: Mapped[int | None] = reference("autorizaciones_descuento.id", nullable=True, unique=True)
    estado: Mapped[str] = mapped_column(String(30), default="pendiente")
    motivo_anulacion: Mapped[str | None] = mapped_column(String(500))
    clave_idempotencia: Mapped[str] = mapped_column(String(80), unique=True)
    fecha: Mapped[dt.datetime] = created()


class AbonoOrden(Base):
    __tablename__ = "abonos_orden"
    __table_args__ = (CheckConstraint("monto > 0", name="monto"), {"schema": SCHEMA})
    id: Mapped[int] = identity()
    orden_id: Mapped[int] = reference("ordenes_pendientes.id")
    registrado_por: Mapped[int] = reference("usuarios.id")
    validado_por: Mapped[int | None] = reference("usuarios.id", nullable=True)
    caja_id: Mapped[int | None] = reference("cajas.id", nullable=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    medio: Mapped[str] = mapped_column(String(30))
    canal: Mapped[str] = mapped_column(String(20))
    codigo_operacion: Mapped[str | None] = mapped_column(String(100))
    comprobante: Mapped[bytes | None] = mapped_column(LargeBinary)
    comprobante_tipo: Mapped[str | None] = mapped_column(String(80))
    estado: Mapped[str] = mapped_column(String(20), default="enviado")
    motivo: Mapped[str | None] = mapped_column(String(500))
    clave_idempotencia: Mapped[str] = mapped_column(String(150), unique=True)
    fecha: Mapped[dt.datetime] = created()


class MovimientoCaja(Base):
    __tablename__ = "movimientos_caja"
    __table_args__ = {"schema": SCHEMA}
    id: Mapped[int] = identity()
    caja_id: Mapped[int] = reference("cajas.id")
    abono_id: Mapped[int] = reference("abonos_orden.id")
    usuario_id: Mapped[int] = reference("usuarios.id")
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    medio: Mapped[str] = mapped_column(String(30))
    motivo: Mapped[str] = mapped_column(String(500))
    fecha: Mapped[dt.datetime] = created()
