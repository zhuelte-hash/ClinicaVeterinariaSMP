"""Snapshot real de respaldo PostgreSQL; solo base local explícita de pruebas."""
from contextlib import contextmanager
from io import BytesIO
import json
import os
import base64
import datetime as dt
from decimal import Decimal
from urllib.parse import urlparse
from uuid import uuid4
from zipfile import ZipFile

import pytest

from sqlalchemy import bindparam, select, text
from sqlalchemy.types import JSON
from app.database import Base, SessionLocal
from app.models.user import TipoUsuario, Usuario
from app.services import backup_service


@pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL") != os.environ.get("TEST_DATABASE_URL"),
    reason="Se requiere una base PostgreSQL local aislada indicada explícitamente",
)
def test_backup_uses_one_postgres_snapshot_and_verifies_its_logical_restore(monkeypatch, tmp_path):
    database = urlparse(os.environ["TEST_DATABASE_URL"])
    assert database.hostname in {"localhost", "127.0.0.1"} and "test" in database.path
    marker = f"backup-{uuid4().hex}@example.test"
    monkeypatch.setattr(backup_service, "__file__", str(tmp_path / "backend" / "app" / "services" / "backup_service.py"))
    original = backup_service.backup_connection

    class ConcurrentWrite:
        def __init__(self, connection):
            self.connection, self.inserted = connection, False

        def execute(self, statement):
            result = self.connection.execute(statement)
            if not self.inserted:
                self.inserted = True
                with SessionLocal() as writer:
                    writer.add(Usuario(nombre="Snapshot concurrente", correo=marker, contrasena="test-hash", tipo=TipoUsuario.CLIENTE))
                    writer.commit()
            return result

    @contextmanager
    def interleaved(db):
        with original(db) as connection:
            yield ConcurrentWrite(connection)

    monkeypatch.setattr(backup_service, "backup_connection", interleaved)
    with SessionLocal() as db:
        content = backup_service.create_backup(db)
    with ZipFile(BytesIO(content)) as archive:
        users = json.loads(archive.read("datos/usuarios.json"))
        assert not any(user["correo"] == marker for user in users)
    assert backup_service.verify_restore(content)["valido"]
    monkeypatch.setattr(backup_service, "backup_connection", original)
    with SessionLocal() as db:
        next_content = backup_service.create_backup(db)
    with ZipFile(BytesIO(next_content)) as archive:
        users = json.loads(archive.read("datos/usuarios.json"))
        assert any(user["correo"] == marker for user in users)
    verify_native_restore(next_content)


def verify_native_restore(content):
    """Recupera tipos, binarios, relaciones y secuencias en un esquema PG efímero.

    La transacción se revierte al salir: ninguna tabla operativa es reemplazada.
    """
    schema = "restore_test_" + uuid4().hex
    with SessionLocal() as db:
        engine = db.get_bind()
    with ZipFile(BytesIO(content)) as archive, engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            connection = connection.execution_options(schema_translate_map={"clinica_veterinaria": schema})
            Base.metadata.create_all(connection)
            for table in Base.metadata.sorted_tables:
                rows = json.loads(archive.read(f"datos/{table.name}.json"))
                if not rows:
                    continue
                columns = list(table.columns)
                names = ",".join(f'"{column.name}"' for column in columns)
                parameters = ",".join(f":c{index}" for index in range(len(columns)))
                statement = text(f'INSERT INTO "{schema}"."{table.name}" ({names}) OVERRIDING SYSTEM VALUE VALUES ({parameters})')
                statement = statement.bindparams(*(bindparam(f"c{index}", type_=column.type) for index, column in enumerate(columns)))
                def decode(value, column):
                    if value is None or not isinstance(value, dict) or isinstance(column.type, JSON):
                        return value
                    kind, raw = value["tipo"], value["valor"]
                    return {"binario": lambda: base64.b64decode(raw, validate=True), "decimal": lambda: Decimal(raw),
                            "datetime": lambda: dt.datetime.fromisoformat(raw), "date": lambda: dt.date.fromisoformat(raw),
                            "time": lambda: dt.time.fromisoformat(raw)}[kind]()
                connection.execute(statement, [{f"c{index}": decode(row[column.name], column) for index, column in enumerate(columns)} for row in rows])
                restored = [{key: backup_service.encode(value) for key, value in row.items()} for row in connection.execute(select(table)).mappings()]
                assert sorted(map(backup_service.canonical, restored)) == sorted(map(backup_service.canonical, rows)), table.name
                for column in columns:
                    if column.identity:
                        maximum = max(int(row[column.name]) for row in rows)
                        connection.execute(text("SELECT setval(pg_get_serial_sequence(:table, :column), :value, true)"), {"table": f'{schema}.{table.name}', "column": column.name, "value": maximum})
            user_table = Usuario.__table__
            expected = max(row[0] for row in connection.execute(select(user_table.c.id))) + 1
            generated = connection.execute(user_table.insert().values(nombre="Después de restaurar", correo=f"restore-{uuid4().hex}@example.test", contrasena="test-hash", tipo=TipoUsuario.CLIENTE).returning(user_table.c.id)).scalar_one()
            assert generated == expected
        finally:
            transaction.rollback()
