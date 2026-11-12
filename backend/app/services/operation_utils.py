import datetime as dt
import enum
from decimal import Decimal

from sqlalchemy import inspect


def branch_id(db):
    return getattr(db, "info", {}).get("sucursal_id", 1)


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
