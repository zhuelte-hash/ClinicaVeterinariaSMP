"""Respaldo lógico con binarios, archivos y verificación en una base aislada."""
import base64
import datetime as dt
import enum
import hashlib
import json
import sqlite3
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, BadZipFile

from fastapi import HTTPException
from sqlalchemy import select, UniqueConstraint

from app.database import Base


def encode(value):
    if isinstance(value, (bytes, memoryview)):
        return {"tipo": "binario", "valor": base64.b64encode(bytes(value)).decode()}
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return {"tipo": type(value).__name__, "valor": value.isoformat()}
    if isinstance(value, Decimal):
        return {"tipo": "decimal", "valor": str(value)}
    if isinstance(value, enum.Enum):
        return value.value
    return value


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def create_backup(db):
    output = BytesIO()
    manifest = {"version": 1, "fecha": dt.datetime.now(dt.timezone.utc).isoformat(), "tablas": {}, "archivos": {}}
    connection = db.connection()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for table in Base.metadata.sorted_tables:
            rows = [{key: encode(value) for key, value in row.items()} for row in connection.execute(select(table)).mappings()]
            data = canonical(rows)
            name = f"datos/{table.name}.json"
            archive.writestr(name, data)
            manifest["tablas"][table.name] = {"archivo": name, "registros": len(rows), "sha256": hashlib.sha256(data).hexdigest()}
        backend = Path(__file__).resolve().parents[2]
        for folder in ("uploads", "clinical_private"):
            directory = backend / folder
            if not directory.exists():
                continue
            for filename in directory.rglob("*"):
                if filename.is_file():
                    name = f"archivos/{folder}/{filename.relative_to(directory).as_posix()}"
                    data = filename.read_bytes()
                    archive.writestr(name, data)
                    manifest["archivos"][name] = hashlib.sha256(data).hexdigest()
        archive.writestr("manifest.json", canonical(manifest))
    return output.getvalue()


def verify_restore(content):
    try:
        archive = ZipFile(BytesIO(content))
        if sum(item.file_size for item in archive.infolist()) > 250 * 1024 * 1024:
            raise ValueError("Respaldo demasiado grande")
        manifest = json.loads(archive.read("manifest.json"))
        if manifest["version"] != 1 or set(manifest["tablas"]) != {table.name for table in Base.metadata.tables.values()}:
            raise ValueError("El esquema del respaldo no coincide con esta versión")
        database = sqlite3.connect(":memory:")
        database.execute("PRAGMA foreign_keys=ON")
        quote = lambda value: '"' + value.replace('"', '""') + '"'
        for table in Base.metadata.sorted_tables:
            columns = [f'{quote(column.name)} TEXT' + (" NOT NULL" if not column.nullable else "") for column in table.columns]
            columns.append("PRIMARY KEY (" + ",".join(quote(column.name) for column in table.primary_key) + ")")
            for constraint in table.constraints:
                if isinstance(constraint, UniqueConstraint):
                    columns.append("UNIQUE (" + ",".join(quote(column.name) for column in constraint.columns) + ")")
            for constraint in table.foreign_key_constraints:
                columns.append("FOREIGN KEY (" + ",".join(quote(column.name) for column in constraint.columns) + ") REFERENCES " + quote(constraint.referred_table.name) + " (" + ",".join(quote(element.column.name) for element in constraint.elements) + ") DEFERRABLE INITIALLY DEFERRED")
            database.execute(f"CREATE TABLE {quote(table.name)} ({','.join(columns)})")
        database.execute("BEGIN")
        restored = 0
        for table in Base.metadata.sorted_tables:
            entry = manifest["tablas"][table.name]
            data = archive.read(entry["archivo"])
            if hashlib.sha256(data).hexdigest() != entry["sha256"]:
                raise ValueError("La integridad del respaldo no coincide")
            rows = json.loads(data)
            if len(rows) != entry["registros"]:
                raise ValueError("El número de registros no coincide")
            names = [column.name for column in table.columns]
            sql = f"INSERT INTO {quote(table.name)} ({','.join(map(quote, names))}) VALUES ({','.join('?' for _ in names)})"
            database.executemany(sql, [[None if row[name] is None else canonical(row[name]).decode() for name in names] for row in rows])
            if database.execute(f"SELECT count(*) FROM {quote(table.name)}").fetchone()[0] != len(rows):
                raise ValueError("No se restauraron todos los registros")
            restored += len(rows)
        database.commit()
        if database.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Se detectaron relaciones inválidas")
        database.close()
        for filename, expected in manifest["archivos"].items():
            if hashlib.sha256(archive.read(filename)).hexdigest() != expected:
                raise ValueError("Hay un archivo corrupto")
        return {"valido": True, "tablas": len(manifest["tablas"]), "registros_restaurados": restored, "archivos": len(manifest["archivos"]), "verificacion": "Restauración lógica en SQLite aislado: claves, relaciones, conteos y SHA-256. La base operativa permanece intacta."}
    except (BadZipFile, KeyError, ValueError, TypeError, sqlite3.DatabaseError, json.JSONDecodeError) as exc:
        raise HTTPException(422, "No se pudo verificar la restauración: " + str(exc)[:300]) from exc
