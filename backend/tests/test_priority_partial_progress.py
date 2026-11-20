"""E32: avance de HU-002/004/036/039/050, con HTTP/JWT y SMTP TCP local."""
import datetime as dt
import hashlib
import hmac
import json
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from test_admin_clinical_flows import clinic
from test_priority_stories import operations
from test_next_five_stories import mailbox, register, start_attention
from test_priority_communications import provider, prescribe, close, messages
from test_fundamental_stories import prepare_attendance
from app.config import get_settings
from app.models.clinic import Cita, EstadoCita, ProcesoAtencion
from app.models.operations import DesafioCuenta, MensajeEntrante, MensajeSalida, OrdenPendiente, Sucursal
from app.models.user import Cliente, PermisoRol, TipoUsuario, Usuario
from app.security import create_access_token
from app.services.access_service import AccessService, now
from app.services.messaging_service import MessagingService


def signed_command(http, monkeypatch, command, message_id="progress-attendance", **extra):
    monkeypatch.setattr(get_settings(), "whatsapp_app_secret", "progress-secret")
    value = {"messages": [{"id": message_id, "from": "51999888777", "type": "text", "text": {"body": command}, **extra}]}
    body = json.dumps({"entry": [{"changes": [{"value": value}]}]}).encode()
    signature = "sha256=" + hmac.new(b"progress-secret", body, hashlib.sha256).hexdigest()
    return http.post("/whatsapp/webhook", content=body, headers={"X-Hub-Signature-256": signature, "Content-Type": "application/json"})


def test_registration_rolls_back_account_when_challenge_cannot_be_created(operations, mailbox, monkeypatch):
    http, db, *_ = operations
    original = AccessService.issue

    def unavailable(*_args, **_kwargs):
        raise HTTPException(503, "No se pudo preparar el correo")

    monkeypatch.setattr(AccessService, "issue", unavailable)
    data = {"nombre": "Cliente transaccional", "correo": "atomic@example.com", "password": "Inicial123", "telefono": "999888777"}
    assert http.post("/auth/register", json=data).status_code == 503
    assert db.scalar(select(Usuario).where(Usuario.correo == data["correo"])) is None
    assert not db.scalars(select(DesafioCuenta)).all() and mailbox[0].empty()
    monkeypatch.setattr(AccessService, "issue", original)
    response = http.post("/auth/register", json=data)
    assert response.status_code == 201, response.text
    assert mailbox[0].get(timeout=5)["To"] == data["correo"]


@pytest.mark.parametrize("event", ["verificar", "recuperar"])
@pytest.mark.parametrize("change", ["inactive", "email_changed"])
def test_queued_account_mail_is_cancelled_after_account_changes(operations, mailbox, event, change):
    _, db, *_ = operations
    owner = db.get(Usuario, 1); owner.correo_verificado = False; db.commit()
    identifier = AccessService(db).issue(owner, event)
    if change == "inactive":
        owner.activo = False
    else:
        owner.correo = "changed@example.com"
    db.commit()
    item = db.get(MensajeSalida, identifier)
    MessagingService(db).deliver(item); db.commit()
    assert item.estado == "cancelado" and item.contenido == "" and item.intentos == 0
    assert mailbox[0].empty()


def test_already_verified_account_does_not_receive_a_delayed_verification_code(operations, mailbox):
    _, db, *_ = operations
    owner = db.get(Usuario, 1); owner.correo_verificado = False; db.commit()
    identifier = AccessService(db).issue(owner, "verificar")
    owner.correo_verificado = True; db.commit()
    item = db.get(MensajeSalida, identifier); MessagingService(db).deliver(item)
    assert item.estado == "cancelado" and mailbox[0].empty()


@pytest.mark.parametrize("event", ["cita_cancelada", "receta"])
def test_clinical_notice_waits_for_corrected_reservation_phone_without_consuming_attempts(operations, provider, event):
    http, db, headers, *_ = operations
    if event == "receta":
        process = start_attention(http, db, headers); prescribe(http, headers, process)
        assert close(http, headers, process).status_code == 200
    else:
        assert http.patch("/portal/citas/1/cancelar", headers=headers[1], json={"motivo": "Cambio de planes"}).status_code == 200
    db.get(Cita, 1).telefono_contacto = "123"; db.commit()
    item = messages(db, event)[0]
    MessagingService(db).deliver(item); db.commit()
    assert item.estado == "pendiente_configuracion" and item.intentos == 0 and not provider
    db.get(Cita, 1).telefono_contacto = "987654321"; db.commit()
    assert http.post(f"/admin/operaciones/mensajes/{item.id}/reintentar", headers=headers[4]).status_code == 200
    MessagingService(db).deliver(item); db.commit()
    assert item.estado == "enviado" and item.destinatario == "51987654321"


@pytest.mark.parametrize("change", ["owner_inactive", "branch_inactive", "appointment_changed"])
def test_cancel_notice_rechecks_operation_before_delivery_or_retry(operations, provider, change):
    http, db, headers, *_ = operations
    assert http.patch("/portal/citas/1/cancelar", headers=headers[1], json={"motivo": "Cambio de planes"}).status_code == 200
    item = messages(db, "cita_cancelada")[0]
    if change == "owner_inactive":
        db.get(Usuario, 1).activo = False
    elif change == "appointment_changed":
        db.get(Cita, 1).estado = EstadoCita.CONFIRMADA
    else:
        db.get(Sucursal, 1).activa = False
    db.commit()
    MessagingService(db).deliver(item); db.commit()
    assert item.estado == "cancelado" and item.intentos == 0 and not provider


@pytest.mark.parametrize("change", ["order_voided", "order_expired", "pdf_missing", "attention_changed"])
def test_prescription_notice_does_not_deliver_obsolete_order_or_missing_pdf(operations, provider, change):
    http, db, headers, *_ = operations
    process = start_attention(http, db, headers); prescribe(http, headers, process)
    assert close(http, headers, process).status_code == 200
    item = messages(db, "receta")[0]
    if change.startswith("order_"):
        db.scalar(select(OrdenPendiente).where(OrdenPendiente.proceso_id == process)).estado = "anulada" if change == "order_voided" else "vencida"
    elif change == "pdf_missing":
        item.documento = None
    else:
        db.get(ProcesoAtencion, process).estado = "cancelada"
    db.commit()
    MessagingService(db).deliver(item); db.commit()
    assert item.estado == ("pendiente_configuracion" if change == "pdf_missing" else "cancelado")
    assert item.intentos == 0 and not provider


def test_client_can_follow_cancellation_without_access_to_internal_message_fields(operations):
    http, db, headers, *_ = operations
    assert http.patch("/portal/citas/1/cancelar", headers=headers[1], json={"motivo": "Cambio de planes"}).status_code == 200
    response = http.get("/portal/citas/1/comunicaciones", headers=headers[1])
    assert response.status_code == 200 and response.headers["cache-control"] == "private, no-store"
    item = response.json()["mensajes"][0]
    assert item["evento"] == "cita_cancelada" and item["estado"] == "pendiente"
    assert not {"contenido", "parametros", "documento", "destinatario", "error"} & item.keys()
    assert not response.json()["receta_disponible"] and response.json()["orden"] is None
    assert http.get("/portal/citas/2/comunicaciones", headers=headers[1]).json()["mensajes"] == []


def test_owner_downloads_same_private_pdf_as_whatsapp_with_order_details(operations):
    http, db, headers, _, product = operations
    process = start_attention(http, db, headers); prescribe(http, headers, process, product)
    assert close(http, headers, process).status_code == 200
    item = messages(db, "receta")[0]
    status = http.get("/portal/citas/1/comunicaciones", headers=headers[1]).json()
    assert status["receta_disponible"] and float(status["orden"]["total"]) == 90
    assert status["orden"]["codigo"] in item.contenido
    response = http.get("/portal/citas/1/receta-pdf", headers=headers[1])
    assert response.status_code == 200 and response.content == item.documento
    assert response.headers["cache-control"] == "private, no-store" and response.headers["content-type"] == "application/pdf"
    assert "receta-cita-1.pdf" in response.headers["content-disposition"]
    db.add(PermisoRol(rol=TipoUsuario.CLIENTE, modulo="historias_clinicas", puede_ver=False)); db.commit()
    assert not http.get("/portal/citas/1/comunicaciones", headers=headers[1]).json()["receta_disponible"]
    assert http.get("/portal/citas/1/receta-pdf", headers=headers[1]).status_code == 403


@pytest.mark.parametrize("route", ["comunicaciones", "receta-pdf"])
def test_communication_and_prescription_endpoints_enforce_role_ownership_and_branch(operations, route):
    http, db, headers, *_ = operations
    db.add_all([Sucursal(id=2, nombre="Otra sede"), Usuario(id=6, nombre="Otro cliente", correo="other-client@example.com", contrasena="hash", tipo="cliente")]); db.flush()
    db.add(Cliente(usuario_id=6)); db.commit()
    url = f"/portal/citas/1/{route}"
    assert http.get(url).status_code == 401
    assert http.get(url, headers=headers[2]).status_code == 403
    assert http.get(url, headers={"Authorization": "Bearer " + create_access_token(6)}).status_code == 404
    assert http.get(url, headers={**headers[1], "X-Sucursal-ID": "2"}).status_code == 404


def test_prescription_download_is_not_available_before_closure(operations):
    http, db, headers, *_ = operations
    process = start_attention(http, db, headers); prescribe(http, headers, process)
    assert http.get("/portal/citas/1/receta-pdf", headers=headers[1]).status_code == 404


def test_versioned_attendance_command_is_accepted_and_deduplicated(operations, monkeypatch):
    http, db, headers, *_ = operations
    prepare_attendance(db)
    response = http.get("/portal/citas/1/asistencia-whatsapp", headers=headers[1])
    assert response.status_code == 200, response.text
    command = response.json()["comando"]
    assert parse_qs(urlsplit(response.json()["whatsapp_url"]).query)["text"] == [command]
    assert db.get(Cita, 1).asistencia_confirmada_en is None
    for identifier in ("version-1", "version-1", "version-2"):
        assert signed_command(http, monkeypatch, command, identifier).status_code == 200
    assert db.get(Cita, 1).asistencia_confirmada_en is not None


@pytest.mark.parametrize("change", ["schedule", "contact", "session", "tampered"])
def test_stale_or_tampered_attendance_code_cannot_confirm_current_appointment(operations, monkeypatch, change):
    http, db, headers, *_ = operations
    prepare_attendance(db)
    command = http.get("/portal/citas/1/asistencia-whatsapp", headers=headers[1]).json()["comando"]
    appointment = db.get(Cita, 1)
    if change == "schedule":
        appointment.fecha_hora_programada += dt.timedelta(hours=1); appointment.fecha_hora_fin_programada += dt.timedelta(hours=1)
    elif change == "contact":
        appointment.telefono_contacto = "999111222"
    elif change == "session":
        db.get(Usuario, 1).version_sesion += 1
    else:
        command = command[:-1] + ("0" if command[-1] != "0" else "1")
    db.commit()
    assert signed_command(http, monkeypatch, command).status_code == 200
    assert appointment.asistencia_confirmada_en is None
    incoming = db.scalar(select(MensajeEntrante).where(MensajeEntrante.proveedor_id == "progress-attendance"))
    assert incoming.resultado != "asistencia_confirmada"


def test_legacy_attendance_sent_before_latest_schedule_is_rejected(operations, monkeypatch):
    http, db, headers, *_ = operations
    prepare_attendance(db)
    assert signed_command(http, monkeypatch, "ASISTIRE 1", timestamp="1").status_code == 200
    assert db.get(Cita, 1).asistencia_confirmada_en is None


def test_signed_webhook_for_different_business_number_does_not_process_attendance(operations, monkeypatch):
    http, db, headers, *_ = operations
    prepare_attendance(db)
    monkeypatch.setattr(get_settings(), "whatsapp_app_secret", "progress-secret")
    monkeypatch.setattr(get_settings(), "whatsapp_phone_number_id", "clinic-number")
    body = json.dumps({"entry": [{"changes": [{"value": {"metadata": {"phone_number_id": "other-number"}, "messages": [{"id": "wrong-business", "from": "51999888777", "type": "text", "text": {"body": "ASISTIRE 1"}}]}}]}]}).encode()
    signature = "sha256=" + hmac.new(b"progress-secret", body, hashlib.sha256).hexdigest()
    assert http.post("/whatsapp/webhook", content=body, headers={"X-Hub-Signature-256": signature}).status_code == 403
    assert db.get(Cita, 1).asistencia_confirmada_en is None
    assert db.scalar(select(MensajeEntrante).where(MensajeEntrante.proveedor_id == "wrong-business")) is None
