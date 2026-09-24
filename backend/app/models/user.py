import datetime
import enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, SCHEMA


class TipoUsuario(str, enum.Enum):
    CLIENTE = "cliente"
    VETERINARIO = "veterinario"
    CAJERO = "cajero"
    ADMINISTRADOR = "administrador"


tipo_usuario_db = Enum(
    TipoUsuario,
    name="tipo_usuario",
    schema=SCHEMA,
    values_callable=lambda enum_class: [item.value for item in enum_class],
)


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        Index("uq_usuarios_correo_lower", text("lower(correo)"), unique=True),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    correo: Mapped[str] = mapped_column(String(254), nullable=False, unique=True)
    contrasena: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[TipoUsuario] = mapped_column(tipo_usuario_db, nullable=False)

    cliente: Mapped["Cliente | None"] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", uselist=False
    )
    veterinario: Mapped["Veterinario | None"] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", uselist=False
    )
    cajero: Mapped["Cajero | None"] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", uselist=False
    )
    administrador: Mapped["Administrador | None"] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", uselist=False
    )


class Cliente(Base):
    __tablename__ = "clientes"
    __table_args__ = {"schema": SCHEMA}

    usuario_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.usuarios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    telefono: Mapped[str | None] = mapped_column(String(30))
    direccion: Mapped[str | None] = mapped_column(String(255))

    usuario: Mapped[Usuario] = relationship(back_populates="cliente")
    mascotas: Mapped[list["Mascota"]] = relationship(back_populates="cliente")
    ordenes_cobro: Mapped[list["OrdenCobro"]] = relationship(back_populates="cliente")


class Veterinario(Base):
    __tablename__ = "veterinarios"
    __table_args__ = {"schema": SCHEMA}

    usuario_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.usuarios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    colegiatura: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    especialidad: Mapped[str | None] = mapped_column(String(100))

    usuario: Mapped[Usuario] = relationship(back_populates="veterinario")
    procesos_medicos: Mapped[list["ProcesoAtencionMedica"]] = relationship(
        back_populates="veterinario"
    )


class Cajero(Base):
    __tablename__ = "cajeros"
    __table_args__ = {"schema": SCHEMA}

    usuario_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.usuarios.id", ondelete="CASCADE"),
        primary_key=True,
    )

    usuario: Mapped[Usuario] = relationship(back_populates="cajero")
    cajas: Mapped[list["Caja"]] = relationship(back_populates="cajero")
    ordenes_cobro: Mapped[list["OrdenCobro"]] = relationship(back_populates="cajero")


class Administrador(Base):
    __tablename__ = "administradores"
    __table_args__ = {"schema": SCHEMA}

    usuario_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.usuarios.id", ondelete="CASCADE"),
        primary_key=True,
    )

    usuario: Mapped[Usuario] = relationship(back_populates="administrador")
    permisos: Mapped[list["Permiso"]] = relationship(
        back_populates="administrador", cascade="all, delete-orphan"
    )
    auditorias: Mapped[list["AuditoriaAccion"]] = relationship(
        back_populates="administrador"
    )


class Permiso(Base):
    __tablename__ = "permisos"
    __table_args__ = (
        UniqueConstraint(
            "administrador_id",
            "modulo",
            name="uq_permisos_administrador_modulo",
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    administrador_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.administradores.usuario_id", ondelete="RESTRICT"),
        nullable=False,
    )
    modulo: Mapped[str] = mapped_column(String(100), nullable=False)
    puede_ver: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    puede_editar: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    administrador: Mapped[Administrador] = relationship(back_populates="permisos")


class AuditoriaAccion(Base):
    __tablename__ = "auditoria_acciones"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    administrador_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA}.administradores.usuario_id", ondelete="RESTRICT"),
        nullable=False,
    )
    accion_critica: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha_hora: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    administrador: Mapped[Administrador] = relationship(back_populates="auditorias")
