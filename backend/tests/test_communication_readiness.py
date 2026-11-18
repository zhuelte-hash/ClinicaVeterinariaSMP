"""Preparación y seguimiento de HU-002/004/036/039/050 con HTTP/JWT aislado."""
import datetime as dt

import pytest

from test_admin_clinical_flows import clinic
from test_priority_stories import operations
from app.config import get_settings
from app.models.clinic import ConfiguracionClinica
from app.models.operations import DesafioCuenta, MensajeSalida
from app.models.user import PermisoRol, TipoUsuario
from app.services.access_service import now


def test_readiness_lists_missing_configuration_without_secrets_or_network(operations, monkeypatch):
    http, db, headers, *_ = operations
    settings = get_settings()
    for name in ("smtp_host", "mail_from", "smtp_username", "smtp_password", "whatsapp_phone_number_id", "whatsapp_access_token", "whatsapp_app_secret", "whatsapp_verify_token"):
        monkeypatch.setattr(settings, name, "")
    monkeypatch.setattr(settings, "smtp_ssl", False)
    db.add(ConfiguracionClinica(nombre="SMP", correo="clinic@example.com", telefono="965939522")); db.commit()
    response = http.get("/admin/operaciones/comunicaciones/estado", headers=headers[4])
    assert response.status_code == 200, response.text
    data = response.json()
    assert response.headers["cache-control"] == "private, no-store"
    assert data["correo"] == {"configurado": False, "faltantes": ["SMTP_HOST", "MAIL_FROM"]}
    assert not data["whatsapp"]["configurado"] and not data["webhook"]["configurado"]
    assert data["telefono_clinica_valido"]
    assert {"receta", "cita_cancelada", "cita_confirmada", "cita_reprogramada", "veterinario_reprogramacion", "veterinario_cancelacion"} <= {row["evento"] for row in data["plantillas"]}
    assert "No acredita recepción externa" in data["alcance"]


def test_readiness_reports_present_variables_but_does_not_claim_external_delivery(operations, monkeypatch):
    http, _db, headers, *_ = operations
    settings = get_settings()
    for name in ("smtp_host", "mail_from", "whatsapp_phone_number_id", "whatsapp_access_token", "whatsapp_app_secret", "whatsapp_verify_token"):
        monkeypatch.setattr(settings, name, "private-value-" + name)
    monkeypatch.setattr(settings, "smtp_username", "")
    monkeypatch.setattr(settings, "smtp_password", "")
    monkeypatch.setattr(settings, "smtp_ssl", False)
    response = http.get("/admin/operaciones/comunicaciones/estado", headers=headers[4])
    assert all(response.json()[channel]["configurado"] for channel in ("correo", "whatsapp", "webhook"))
    assert "private-value-" not in response.text


def test_readiness_detects_incompatible_smtp_options(operations, monkeypatch):
    http, _db, headers, *_ = operations
    settings = get_settings()
    for key, value in {"smtp_host": "smtp.example.com", "mail_from": "clinic@example.com", "smtp_ssl": True, "smtp_starttls": True, "smtp_username": "user", "smtp_password": ""}.items():
        monkeypatch.setattr(settings, key, value)
    result = http.get("/admin/operaciones/comunicaciones/estado", headers=headers[4]).json()["correo"]
    assert not result["configurado"] and len(result["faltantes"]) == 2


def test_readiness_and_message_log_require_users_permission(operations):
    http, db, headers, *_ = operations
    for path in ("/admin/operaciones/comunicaciones/estado", "/admin/operaciones/mensajes"):
        assert http.get(path).status_code == 401
        assert http.get(path, headers=headers[1]).status_code == 403
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="usuarios", puede_ver=False)); db.commit()
    assert http.get("/admin/operaciones/comunicaciones/estado", headers=headers[4]).status_code == 403


def test_filtered_log_omits_account_secrets_and_binary_documents(operations):
    http, db, headers, *_ = operations
    db.add_all([
        MensajeSalida(clave="readiness-email", canal="correo", evento="recuperar", destinatario="test@example.com", contenido="private-reset-token", parametros=["private-code"], estado="error"),
        MensajeSalida(clave="readiness-pdf", canal="whatsapp", evento="receta", destinatario="51999888777", contenido="Receta", documento=b"private-pdf", estado="enviado"),
    ]); db.commit()
    response = http.get("/admin/operaciones/mensajes", headers=headers[4], params={"evento": "recuperar", "estado": "error"})
    assert len(response.json()) == 1 and response.json()[0]["evento"] == "recuperar"
    assert "private-" not in response.text
    assert "contenido" not in response.json()[0] and "parametros" not in response.json()[0]
    assert "documento" not in http.get("/admin/operaciones/mensajes", headers=headers[4], params={"evento": "receta"}).json()[0]
    summary = http.get("/admin/operaciones/comunicaciones/estado", headers=headers[4]).json()["resumen"]
    assert {"evento": "recuperar", "estado": "error", "cantidad": 1} in summary


@pytest.mark.parametrize("condition", ["expired", "used", "cancelled", "sent"])
def test_retry_rejects_obsolete_account_mail(operations, condition):
    http, db, headers, *_ = operations
    challenge = DesafioCuenta(usuario_id=1, proposito="recuperar", secreto_hash="test-hash", expira_en=now() + dt.timedelta(minutes=-1 if condition == "expired" else 15), usado_en=now() if condition == "used" else None)
    db.add(challenge); db.flush()
    message = MensajeSalida(clave="obsolete-email", canal="correo", evento="recuperar", destinatario="test@example.com", contenido="old-token", entidad_id=challenge.id, estado={"cancelled": "cancelado", "sent": "enviado"}.get(condition, "error"))
    db.add(message); db.commit()
    state = message.estado
    assert http.post(f"/admin/operaciones/mensajes/{message.id}/reintentar", headers=headers[4]).status_code == 409
    assert db.get(MensajeSalida, message.id).estado == state


def test_retry_preserves_valid_mail_and_requires_edit_permission(operations):
    http, db, headers, *_ = operations
    challenge = DesafioCuenta(usuario_id=1, proposito="verificar", secreto_hash="test-hash", expira_en=now() + dt.timedelta(minutes=15))
    db.add(challenge); db.flush()
    item = MensajeSalida(clave="valid-email", canal="correo", evento="verificar", destinatario="test@example.com", contenido="code", entidad_id=challenge.id, estado="error", intentos=3, proximo_intento=now() + dt.timedelta(minutes=30))
    db.add(item); db.commit()
    url = f"/admin/operaciones/mensajes/{item.id}/reintentar"
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="usuarios", puede_ver=True, puede_editar=False)); db.commit()
    assert http.post(url, headers=headers[4]).status_code == 403
    assert item.estado == "error"
    db.query(PermisoRol).delete(); db.commit()
    assert http.post(url, headers=headers[4]).status_code == 200
    assert item.estado == "pendiente" and item.intentos == 0 and item.proximo_intento is None


@pytest.mark.parametrize("content,variables", [
    ("Hola {nombre}, {mascota}, {codigo:invalid}", ["nombre", "mascota", "codigo"]),
    ("Hola {nombre!r}, {mascota}, {codigo}", ["nombre", "mascota", "codigo"]),
    ("Hola {nombre}, {mascota}, {codigo}", ["nombre", "mascota", "codigo", "codigo"]),
])
def test_template_rejects_formats_that_break_recipe_or_duplicate_provider_parameters(operations, content, variables):
    http, _db, headers, *_ = operations
    response = http.put("/admin/operaciones/plantillas/receta", headers=headers[4], json={"nombre_proveedor": "receta_pdf", "contenido": content, "variables": variables, "idioma": "es_PE", "activa": True})
    assert response.status_code == 422, response.text


def test_template_persists_provider_order_and_is_readable_without_edit_access(operations):
    http, db, headers, *_ = operations
    payload = {"nombre_proveedor": "receta_pdf", "contenido": "Hola {nombre}, receta de {mascota}: {codigo}", "variables": ["codigo", "nombre", "mascota"], "idioma": "es_PE", "activa": True}
    assert http.put("/admin/operaciones/plantillas/receta", headers=headers[4], json=payload).status_code == 200
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="usuarios", puede_ver=True, puede_editar=False)); db.commit()
    data = http.get("/admin/operaciones/comunicaciones/estado", headers=headers[4]).json()
    template = next(row for row in data["plantillas"] if row["evento"] == "receta")
    assert template["variables"] == payload["variables"]
    assert http.put("/admin/operaciones/plantillas/receta", headers=headers[4], json=payload).status_code == 403
