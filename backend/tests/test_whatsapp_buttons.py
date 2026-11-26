"""Alcance por botones: referencias, textos actuales, enlaces y filtros autorizados."""
import datetime as dt
import re
from uuid import uuid4

import pytest
from sqlalchemy import select

from test_admin_clinical_flows import clinic
from test_priority_stories import operations, create_order
from test_manual_whatsapp import manual
from test_next_five_stories import start_attention
from app.config import get_settings
from app.models.clinic import Cita, EstadoCita, ProcesoAtencion, ProcesoAtencionMedica
from app.models.operations import MensajeSalida, OrdenPendiente, Sucursal
from app.services.access_service import now
from app.services.messaging_service import MessagingService
from scripts.set_clinic_whatsapp import set_phone

BASE = "/operaciones/comunicaciones/manuales"


def prepare(http, headers, item, **data):
    return http.post(f"{BASE}/{item.id}/preparar", headers=headers, json=data)


@pytest.mark.parametrize("hours,event", [(12, "recordatorio_24h"), (1, "recordatorio_2h")])
def test_reply_from_each_reminder_registers_attendance_without_another_portal_message(operations, manual, hours, event):
    http, db, headers, *_ = operations
    appointment = db.get(Cita, 1)
    appointment.estado = EstadoCita.CONFIRMADA
    appointment.fecha_hora_programada = now() + dt.timedelta(hours=hours)
    appointment.fecha_hora_fin_programada = appointment.fecha_hora_programada + dt.timedelta(minutes=30)
    db.commit()
    set_phone(db, "938304590")
    result = http.post("/admin/operaciones/automatizaciones", headers=headers[4], json={})
    assert result.status_code == 200, result.text
    assert result.json()["mensajes_preparados"] == 1
    item = db.scalar(select(MensajeSalida).where(MensajeSalida.evento == event))
    prepared = prepare(http, headers[4], item)
    assert prepared.status_code == 200, prepared.text
    command = re.search(r"ASISTIRE 1 [0-9a-f]{16}\b", prepared.json()["contenido"])[0]
    response = http.post("/admin/operaciones/citas/1/asistencia-manual", headers=headers[4], json={
        "telefono_remitente": appointment.telefono_contacto or appointment.mascota.cliente.usuario.telefono, "referencia": command
    })
    assert response.status_code == 200, response.text
    assert appointment.asistencia_confirmada_en is not None


def test_preparing_an_existing_reminder_refreshes_its_reference_after_contact_changes(operations, manual):
    http, db, headers, *_ = operations
    appointment = db.get(Cita, 1)
    appointment.estado = EstadoCita.CONFIRMADA
    appointment.fecha_hora_programada = now() + dt.timedelta(hours=12)
    appointment.fecha_hora_fin_programada = appointment.fecha_hora_programada + dt.timedelta(minutes=30)
    db.commit()
    http.post("/admin/operaciones/automatizaciones", headers=headers[4], json={})
    item = db.scalar(select(MensajeSalida).where(MensajeSalida.evento == "recordatorio_24h"))
    previous = prepare(http, headers[4], item).json()["contenido"]
    appointment.telefono_contacto = "988777666"; db.commit()
    refreshed = prepare(http, headers[4], item).json()
    assert refreshed["destinatario"] == "51988777666" and refreshed["contenido"] != previous
    old_reference = re.search(r"ASISTIRE 1 [0-9a-f]{16}", previous)[0]
    endpoint = "/admin/operaciones/citas/1/asistencia-manual"
    assert http.post(endpoint, headers=headers[4], json={"telefono_remitente": "988777666", "referencia": old_reference}).status_code == 409
    assert http.post(endpoint, headers=headers[4], json={"telefono_remitente": "988777666", "referencia": refreshed["contenido"]}).status_code == 200


def test_customizing_text_updates_pending_buttons_and_preserves_managed_history(operations, manual):
    http, db, headers, _, product = operations
    first, _ = create_order(http, headers[5], product)
    second, _ = create_order(http, headers[5], product)
    old = db.scalar(select(MensajeSalida).where(MensajeSalida.clave == f"orden:{first['id']}"))
    pending = db.scalar(select(MensajeSalida).where(MensajeSalida.clave == f"orden:{second['id']}"))
    original = old.contenido
    assert http.post(f"{BASE}/{old.id}/gestionar", headers=headers[5], json={}).status_code == 200
    template = next(row for row in MessagingService(db).templates() if row["evento"] == "orden_creada")
    payload = {key: value for key, value in template.items() if key != "evento"}
    payload.update(contenido="Hola {nombre}. Tu orden {codigo}: S/ {total}. Texto personalizado.", variables=["total", "codigo", "nombre"])
    saved = http.put("/admin/operaciones/plantillas/orden_creada", headers=headers[4], json=payload)
    assert saved.status_code == 200, saved.text
    result = prepare(http, headers[5], pending)
    assert result.status_code == 200, result.text
    assert second["codigo"] in result.json()["contenido"] and "S/ 40.00. Texto personalizado." in result.json()["contenido"]
    assert old.estado == "gestionado_manual" and old.contenido == original


@pytest.mark.parametrize("event", ["laboratorio", "encuesta"])
def test_buttons_use_current_application_origin_and_keep_it_when_finishing(operations, manual, monkeypatch, event):
    http, db, headers, *_ = operations
    monkeypatch.setattr(get_settings(), "frontend_url", "https://tunel-antiguo.invalid")
    if event == "laboratorio":
        process = start_attention(http, db, headers)
        assert http.patch(f"/portal/veterinario/atenciones/{process}/resultados", headers=headers[2], json={"examenes_resultados": "Privado"}).status_code == 200
    else:
        process = ProcesoAtencion(mascota_id=1, tipo="medica", estado="cerrada", fecha_cierre=now() - dt.timedelta(hours=25))
        db.add(process); db.flush(); db.add(ProcesoAtencionMedica(proceso_id=process.id, veterinario_id=2)); db.commit()
        http.post("/admin/operaciones/automatizaciones", headers=headers[4], json={})
    item = db.scalar(select(MensajeSalida).where(MensajeSalida.evento == event))
    origin = "https://clinica-botones.example.test"
    prepared = prepare(http, headers[2], item, url_aplicacion=origin)
    assert prepared.status_code == 200, prepared.text
    assert origin + ("/encuesta/" if event == "encuesta" else "/mis-mascotas") in prepared.json()["contenido"]
    assert "tunel-antiguo" not in prepared.json()["contenido"] and "Privado" not in prepared.json()["contenido"]
    finished = http.post(f"{BASE}/{item.id}/gestionar", headers=headers[2], json={"url_aplicacion": origin})
    assert finished.status_code == 200, finished.text
    assert origin in item.contenido and item.estado == "gestionado_manual"
    assert item.enviado_en is None and item.entregado_en is None


@pytest.mark.parametrize("origin", ["javascript:alert(1)", "https://user:password@example.test", "https://example.test/private", "https://example.test/?token=1", "https://example.test/#token"])
def test_application_origin_rejects_non_web_urls_credentials_and_extra_paths(operations, manual, origin):
    http, _db, headers, *_ = operations
    assert http.post(f"{BASE}/1/preparar", headers=headers[4], json={"url_aplicacion": origin}).status_code == 422


def test_context_filters_keep_order_and_sale_messages_separate_from_other_operations(operations, manual):
    http, db, headers, _, product = operations
    first, _ = create_order(http, headers[5], product)
    second, _ = create_order(http, headers[5], product)
    for order in (first, second):
        response = http.post(f"/operaciones/ordenes/{order['id']}/abonos", headers=headers[5], json={
            "monto": "40.00", "medio": "efectivo", "canal": "caja", "clave_idempotencia": str(uuid4())
        })
        assert response.status_code == 201, response.text
        if order is first:
            sale = response.json()["venta_id"]
    first_messages = http.get(BASE, headers=headers[5], params={"tipo": "orden", "referencia": first["id"]}).json()["mensajes"]
    assert {row["evento"] for row in first_messages} == {"orden_creada", "pago_validado"}
    assert all(row["entidad_id"] == first["id"] for row in first_messages)
    receipt, = http.get(BASE, headers=headers[5], params={"tipo": "venta", "referencia": sale}).json()["mensajes"]
    assert receipt["evento"] == "pago_validado"
    legacy = db.get(MensajeSalida, receipt["id"]); legacy.entidad_id = None; db.commit()
    assert http.get(BASE, headers=headers[5], params={"tipo": "venta", "referencia": sale}).json()["mensajes"][0]["id"] == receipt["id"]
    assert http.get(BASE, headers=headers[5], params={"tipo": "atencion", "referencia": 1}).json()["mensajes"] == []
    db.add(Sucursal(id=2, nombre="Otra sede")); db.commit()
    assert http.get(BASE, headers={**headers[4], "X-Sucursal-ID": "2"}, params={"tipo": "orden", "referencia": first["id"]}).json()["mensajes"] == []
    assert http.get(BASE, headers=headers[5], params={"tipo": "orden"}).status_code == 422


def test_scheduled_button_only_prepares_current_branch_without_processing_transports_or_expiring_operations(operations, manual, monkeypatch):
    http, db, headers, _, product = operations
    monkeypatch.setattr(MessagingService, "process", lambda *_a, **_kw: pytest.fail("El botón solo prepara avisos"))
    appointment = db.get(Cita, 1)
    appointment.estado = EstadoCita.CONFIRMADA
    appointment.fecha_hora_programada = now() - dt.timedelta(hours=2)
    appointment.fecha_hora_fin_programada = appointment.fecha_hora_programada + dt.timedelta(minutes=30)
    order, _ = create_order(http, headers[5], product)
    expired = db.get(OrdenPendiente, order["id"]); expired.fecha = now() - dt.timedelta(hours=49)
    db.add(Sucursal(id=2, nombre="Otra sede")); db.flush()
    other = Cita(mascota_id=1, servicio_id=1, veterinario_id=2, sucursal_id=2, estado=EstadoCita.CONFIRMADA,
                 fecha_hora_programada=now() + dt.timedelta(hours=12), fecha_hora_fin_programada=now() + dt.timedelta(hours=13))
    db.add(other); db.commit()
    result = http.post("/admin/operaciones/automatizaciones", headers=headers[4], json={})
    assert result.status_code == 200, result.text
    assert result.json() == {"mensajes_procesados": 0, "mensajes_preparados": 0}
    assert appointment.estado == EstadoCita.CONFIRMADA and expired.estado == "pendiente"
    assert not db.scalars(select(MensajeSalida).where(MensajeSalida.evento.in_(["recordatorio_24h", "recordatorio_2h"]))).all()
    assert http.post("/admin/operaciones/automatizaciones", headers=headers[5], json={}).status_code == 403
