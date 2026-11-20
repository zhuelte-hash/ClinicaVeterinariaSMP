import datetime as dt
import enum
from decimal import Decimal

from sqlalchemy import inspect, select


def branch_id(db):
    return getattr(db, "info", {}).get("sucursal_id", 1)


def process_in_branch(db):
    from app.models.clinic import Cita, Mascota, ProcesoAtencion
    from app.models.user import Cliente, Usuario
    return ProcesoAtencion.cita_id.in_(select(Cita.id).where(Cita.sucursal_id == branch_id(db))) | (
        ProcesoAtencion.cita_id.is_(None) & ProcesoAtencion.mascota.has(
            Mascota.cliente.has(Cliente.usuario.has(Usuario.sucursal_id == branch_id(db)))))


def row_data(item, exclude=()):
    return {column.key: getattr(item, column.key) for column in inspect(type(item)).columns if column.key not in exclude and column.key not in {"contrasena", "secreto_hash", "token_hash", "documento", "comprobante"}}


def json_value(value):
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value if isinstance(value, (str, int, float, bool, type(None))) else None
