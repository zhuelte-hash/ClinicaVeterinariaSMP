"""Acceso completo del modo manual: mismo origen, permisos, enlaces y bienvenida."""
import datetime as dt
from pathlib import Path
import re

import pytest
from dotenv import dotenv_values
from sqlalchemy import select

from test_admin_clinical_flows import clinic
from test_priority_stories import operations
from test_manual_whatsapp import manual
from test_next_five_stories import start_attention
from app.config import get_settings
from app.main import app
from app.models.clinic import ProcesoAtencion, ProcesoAtencionMedica
from app.models.operations import EncuestaConsulta, MensajeSalida
from app.models.user import PermisoRol, TipoUsuario, Usuario
from app.services.access_service import digest, now
from app.services.automation_service import run_automations
from scripts import configure_email


@pytest.mark.parametrize("path", ["/", "/inicio", "/mis-mascotas", "/encuesta/prueba", "/admin/comunicaciones", "/caja/comunicaciones", "/veterinario/comunicaciones"])
def test_frontend_documents_boot_same_origin_api_without_exposing_private_data(operations, path):
    http, *_ = operations
    result = http.get(path, headers={"Accept": "text/html"})
    assert result.status_code == 200
    assert "globalThis.__CLINIC_API_URL__=\"/api\"" in result.text
    assert result.headers["content-type"].startswith("text/html")
    assert result.headers["cache-control"] == "no-store"
    assert "owner@example.com" not in result.text


def test_prefixed_api_keeps_authentication_permissions_and_client_ownership(operations, manual):
    http, db, headers, *_ = operations
    assert http.get("/api/health").json() == {"status": "ok"}
    assert http.get("/api/admin/citas").status_code == 401
    response = http.get("/api/portal/mascotas", headers=headers[1])
    assert response.status_code == 200 and response.json()[0]["nombre"] == "Luna"
    db.add(PermisoRol(rol=TipoUsuario.CLIENTE, modulo="mascotas", puede_ver=False)); db.commit()
    assert http.get("/api/portal/mascotas", headers=headers[1]).status_code == 403
    assert http.get("/api/admin/citas", headers=headers[1]).status_code == 403
    assert http.get("/api/operaciones/comunicaciones/manuales", headers=headers[1]).status_code == 403


def test_json_api_is_not_replaced_with_a_frontend_document(operations):
    http, *_ = operations
    assert http.get("/admin/citas", headers={"Accept": "application/json"}).status_code == 401
    result = http.get("/api/health", headers={"Accept": "text/html"})
    assert result.headers["content-type"].startswith("application/json")
    assert http.get("/backend/.env", headers={"Accept": "text/html"}).status_code == 404


def test_prefixed_uploads_do_not_publish_clinical_files(operations, monkeypatch, tmp_path):
    http, *_ = operations
    (tmp_path / "clinical").mkdir()
    (tmp_path / "clinical/secret.pdf").write_bytes(b"private-clinical-content")
    (tmp_path / "public.jpg").write_bytes(b"public-photo")
    uploads = next(route.app for route in app.routes if getattr(route, "path", "") == "/uploads")
    monkeypatch.setattr(uploads, "all_directories", [str(tmp_path)])
    assert http.get("/api/uploads/public.jpg").content == b"public-photo"
    assert http.get("/api/uploads/clinical/secret.pdf").status_code == 404
    assert http.get("/uploads/clinical/secret.pdf").status_code == 404


def test_staff_registration_prepares_one_manual_welcome_without_smtp(operations, manual, monkeypatch):
    http, db, headers, *_ = operations
    monkeypatch.setattr(get_settings(), "smtp_host", "")
    monkeypatch.setattr(get_settings(), "mail_from", "")
    payload = {"nombre": "Cliente de alta presencial", "correo": "presencial@example.com", "contrasena": "Inicial123", "tipo": "cliente", "telefono": "938304590"}
    created = http.post("/usuarios", headers=headers[4], json=payload)
    assert created.status_code == 201, created.text
    owner = db.get(Usuario, created.json()["id"])
    assert owner.correo_verificado
    welcome, = db.scalars(select(MensajeSalida).where(MensajeSalida.evento == "bienvenida", MensajeSalida.usuario_id == owner.id)).all()
    assert welcome.estado == "pendiente_manual" and welcome.destinatario == "51938304590"
    assert http.post("/usuarios", headers=headers[4], json=payload).status_code == 409
    assert len(db.scalars(select(MensajeSalida).where(MensajeSalida.evento == "bienvenida", MensajeSalida.usuario_id == owner.id)).all()) == 1
    prepared = http.post(f"/api/operaciones/comunicaciones/manuales/{welcome.id}/preparar", headers=headers[4], json={})
    assert prepared.status_code == 200 and "alta presencial" in prepared.json()["contenido"]
    public = http.post("/auth/register", json={"nombre": "Registro público", "correo": "publico@example.com", "password": "Inicial123", "telefono": "938304590"})
    assert public.status_code == 503
    assert db.scalar(select(Usuario).where(Usuario.correo == "publico@example.com")) is None


def test_laboratory_link_uses_current_application_origin_when_prepared(operations, manual, monkeypatch):
    http, db, headers, *_ = operations
    monkeypatch.setattr(get_settings(), "frontend_url", "http://localhost:4200")
    process = start_attention(http, db, headers)
    assert http.patch(f"/portal/veterinario/atenciones/{process}/resultados", headers=headers[2], json={"examenes_resultados": "Resultado privado"}).status_code == 200
    message = db.scalar(select(MensajeSalida).where(MensajeSalida.evento == "laboratorio"))
    monkeypatch.setattr(get_settings(), "frontend_url", "https://clinica.example.test")
    prepared = http.post(f"/api/operaciones/comunicaciones/manuales/{message.id}/preparar", headers=headers[2], json={})
    assert prepared.status_code == 200, prepared.text
    assert "https://clinica.example.test/mis-mascotas" in prepared.json()["contenido"]
    assert "localhost" not in prepared.json()["contenido"] and "Resultado privado" not in prepared.json()["contenido"]


@pytest.mark.parametrize("corrupted", [False, True])
def test_survey_origin_can_change_but_its_private_token_cannot(operations, manual, monkeypatch, corrupted):
    http, db, headers, *_ = operations
    monkeypatch.setattr(get_settings(), "frontend_url", "http://localhost:4200")
    process = ProcesoAtencion(mascota_id=1, tipo="medica", estado="cerrada", fecha_cierre=now() - dt.timedelta(hours=25))
    db.add(process); db.flush(); db.add(ProcesoAtencionMedica(proceso_id=process.id, veterinario_id=2)); db.commit()
    run_automations(db)
    message = db.scalar(select(MensajeSalida).where(MensajeSalida.evento == "encuesta"))
    token = re.search(r"/encuesta/([A-Za-z0-9_-]+)", message.contenido)[1]
    survey = db.scalar(select(EncuestaConsulta).where(EncuestaConsulta.proceso_id == process.id))
    if corrupted:
        survey.token_hash = digest("otro-token"); db.commit()
    monkeypatch.setattr(get_settings(), "frontend_url", "https://clinica.example.test")
    result = http.post(f"/api/operaciones/comunicaciones/manuales/{message.id}/preparar", headers=headers[2], json={})
    if corrupted:
        assert result.status_code == 409 and message.estado == "cancelado"
    else:
        assert result.status_code == 200 and f"https://clinica.example.test/encuesta/{token}" in result.json()["contenido"]
        assert survey.token_hash == digest(token)


def test_email_configuration_preserves_other_local_settings_and_normalizes_app_password(tmp_path):
    path = tmp_path / ".env"
    path.write_text("DATABASE_URL='postgresql://existing/database'\nSECRET_KEY='preserve-secret'\nWHATSAPP_PROVIDER=manual\n", encoding="utf-8")
    values = configure_email.smtp_values("clinic@gmail.com", "abcd efgh ijkl mnop")
    configure_email.save(path, values)
    saved = dotenv_values(path)
    assert saved["DATABASE_URL"] == "postgresql://existing/database" and saved["SECRET_KEY"] == "preserve-secret"
    assert saved["WHATSAPP_PROVIDER"] == "manual" and saved["SMTP_PASSWORD"] == "abcdefghijklmnop"
    assert saved["MAIL_FROM"] == saved["SMTP_USERNAME"] == "clinic@gmail.com"


def test_smtp_configuration_check_connects_and_authenticates_without_sending(monkeypatch):
    events = []
    class SMTP:
        def __init__(self, host, port, **kwargs): events.append(("connect", host, port))
        def __enter__(self): return self
        def __exit__(self, *_args): return None
        def starttls(self, **kwargs): events.append(("tls",))
        def login(self, user, password): events.append(("login", user, password))
        def send_message(self, *_args): pytest.fail("El diagnóstico no debe enviar mensajes")
    monkeypatch.setattr(configure_email.smtplib, "SMTP", SMTP)
    configure_email.check_connection(configure_email.smtp_values("clinic@gmail.com", "app-password"))
    assert [event[0] for event in events] == ["connect", "tls", "login"]
