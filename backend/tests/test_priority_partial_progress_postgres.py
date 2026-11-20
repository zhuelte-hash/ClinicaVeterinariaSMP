"""E32: concurrencia de correos y confirmación versionada en PostgreSQL migrado."""
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import os
from threading import Barrier
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import HTTPException
import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from test_independent_stories_postgres import native
from test_priority_partial_progress import signed_command
from app.database import engine
from app.models.clinic import ConfiguracionClinica
from app.models.operations import DesafioCuenta, MensajeSalida
from app.models.user import Cliente, PermisoRol, TipoUsuario, Usuario
from app.schemas.auth import ClientRegisterRequest
from app.services.access_service import AccessService, digest, now
from app.services.policy_service import ZONE
from app.services.user_service import UserService


@pytest.fixture
def committed_account():
    url = os.getenv("TEST_DATABASE_URL")
    if not url or os.getenv("DATABASE_URL") != url:
        pytest.skip("Requiere PostgreSQL aislado local de pruebas")
    parsed = urlparse(url)
    assert parsed.hostname in {"localhost", "127.0.0.1"} and "test" in parsed.path
    with Session(engine) as db:
        owner = UserService(db).create_client(ClientRegisterRequest(nombre="Concurrencia", correo=f"{uuid4().hex}@example.com", password="PruebaClave123", telefono="999888777"))
        identifier = owner.id
    try:
        yield identifier
    finally:
        with Session(engine) as db:
            db.execute(delete(MensajeSalida).where(MensajeSalida.usuario_id == identifier))
            db.execute(delete(DesafioCuenta).where(DesafioCuenta.usuario_id == identifier))
            db.execute(delete(Cliente).where(Cliente.usuario_id == identifier))
            db.execute(delete(Usuario).where(Usuario.id == identifier))
            db.commit()


@pytest.mark.parametrize("purpose", ["verificar", "recuperar"])
def test_native_simultaneous_account_requests_issue_only_one_live_challenge(committed_account, purpose):
    identifier = committed_account
    barrier = Barrier(2)

    def issue():
        with Session(engine) as db:
            owner = db.get(Usuario, identifier)
            barrier.wait(timeout=10)
            try:
                return "issued", AccessService(db).issue(owner, purpose)
            except HTTPException as exc:
                return "rejected", exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: issue(), range(2)))
    assert [result[0] for result in results].count("issued") == 1
    assert ("rejected", 429) in results
    with Session(engine) as db:
        assert len(db.scalars(select(DesafioCuenta).where(DesafioCuenta.usuario_id == identifier, DesafioCuenta.usado_en.is_(None))).all()) == 1
        assert len(db.scalars(select(MensajeSalida).where(MensajeSalida.usuario_id == identifier, MensajeSalida.canal == "correo")).all()) == 1


def test_native_verification_and_resend_do_not_deadlock_or_accept_replaced_code(committed_account, monkeypatch):
    monkeypatch.setattr("app.services.access_service.secrets.randbelow", lambda _maximum: 654321)
    identifier = committed_account
    with Session(engine) as db:
        db.add(DesafioCuenta(usuario_id=identifier, proposito="verificar", secreto_hash=digest(f"{identifier}:verificar:123456"), creado_en=now() - dt.timedelta(minutes=2), expira_en=now() + dt.timedelta(minutes=10)))
        db.commit()
    barrier = Barrier(2)

    def act(action):
        with Session(engine) as db:
            owner = db.get(Usuario, identifier)
            barrier.wait(timeout=10)
            try:
                if action == "verify":
                    AccessService(db).verify(owner.correo, "123456")
                else:
                    AccessService(db).issue(owner, "verificar")
                return action, 200
            except HTTPException as exc:
                return action, exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(act, ("verify", "resend")))
    assert sorted(status for _, status in results) == [200, 400]
    with Session(engine) as db:
        verified = db.get(Usuario, identifier).correo_verificado
        assert verified == (("verify", 200) in results)


def test_native_attendance_code_tracks_schedule_and_accepts_only_current_version(native, monkeypatch):
    http, db, headers, appointment, pet, *_ = native
    owner = db.get(Usuario, pet.cliente_id); owner.cliente.telefono = "999888777"
    config = db.scalar(select(ConfiguracionClinica))
    if config is None:
        config = ConfiguracionClinica(nombre="Prueba", correo="clinic@example.test"); db.add(config)
    config.telefono = "999111222"
    permission = db.scalar(select(PermisoRol).where(PermisoRol.rol == TipoUsuario.CLIENTE, PermisoRol.modulo == "citas"))
    if permission is None:
        permission = PermisoRol(rol=TipoUsuario.CLIENTE, modulo="citas"); db.add(permission)
    permission.puede_ver = permission.puede_editar = True
    tomorrow = now().astimezone(ZONE).date() + dt.timedelta(days=1)
    appointment.fecha_hora_programada = dt.datetime.combine(tomorrow, dt.time(10), ZONE)
    appointment.fecha_hora_fin_programada = appointment.fecha_hora_programada + dt.timedelta(minutes=30)
    db.commit()
    url = f"/portal/citas/{appointment.id}/asistencia-whatsapp"
    response = http.get(url, headers=headers["cliente"])
    assert response.status_code == 200, response.text
    old = response.json()["comando"]
    appointment.fecha_hora_programada += dt.timedelta(hours=1); appointment.fecha_hora_fin_programada += dt.timedelta(hours=1); db.commit()
    assert signed_command(http, monkeypatch, old, "native-old").status_code == 200
    db.refresh(appointment)
    assert appointment.asistencia_confirmada_en is None
    current = http.get(url, headers=headers["cliente"]).json()["comando"]
    assert current != old
    assert signed_command(http, monkeypatch, current, "native-current").status_code == 200
    db.refresh(appointment)
    assert appointment.asistencia_confirmada_en is not None
