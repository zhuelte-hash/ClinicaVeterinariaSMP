"""HU-036/050/098: eventos HTTP/JWT, PDF, reintentos y webhook firmado.

El transporte de Meta es controlado: estas pruebas no acreditan entrega externa.
HU-002/004 conservan las pruebas SMTP reales locales de test_next_five_stories.
"""
import datetime as dt
import hashlib
import hmac
import json
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import select

from test_admin_clinical_flows import clinic
from test_priority_stories import operations
from test_next_five_stories import start_attention
from app.config import get_settings
from app.models.clinic import Cita, EstadoCita, Producto, ProcesoAtencion, Servicio
from app.models.operations import MensajeSalida, OrdenPendiente, PlantillaMensaje
from app.services import messaging_service
from app.services.access_service import now
from app.services.messaging_service import EVENTS, MessagingService


def messages(db, event):
    return db.scalars(select(MensajeSalida).where(MensajeSalida.evento == event)).all()


def webhook(http, monkeypatch, statuses):
    monkeypatch.setattr(get_settings(), "whatsapp_app_secret", "test-webhook-secret")
    body = json.dumps({"entry": [{"changes": [{"value": {"statuses": statuses}}]}]}).encode()
    signature = "sha256=" + hmac.new(b"test-webhook-secret", body, hashlib.sha256).hexdigest()
    return http.post("/whatsapp/webhook", content=body, headers={"Content-Type": "application/json", "X-Hub-Signature-256": signature})


@pytest.fixture
def provider(operations, monkeypatch):
    _http, db, *_ = operations
    settings = get_settings()
    monkeypatch.setattr(settings, "whatsapp_phone_number_id", "test-number")
    monkeypatch.setattr(settings, "whatsapp_access_token", "test-token")
    for event in ("cita_confirmada", "cita_reprogramada", "cita_cancelada", "receta"):
        db.add(PlantillaMensaje(evento=event, nombre_proveedor=f"test_{event}", contenido=EVENTS[event][0], variables=EVENTS[event][1], idioma="es_PE", activa=True))
    db.commit()
    calls = []

    def post(url, **kwargs):
        calls.append((url, kwargs))
        payload = {"id": "media-pdf"} if url.endswith("/media") else {"messages": [{"id": f"wamid.{len(calls)}"}]}
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(messaging_service.httpx, "post", post)
    return calls


def prescribe(http, headers, process, product=None):
    detail = {"medicamento": "Medicina", "dosis": "1", "unidad": "tableta", "via": "oral", "frecuencia": "cada 12 horas", "duracion": "2 días"}
    if product:
        detail.update(producto_id=product, cantidad_producto=2)
    response = http.put(f"/portal/veterinario/atenciones/{process}/receta", headers=headers[2], json={"indicaciones_generales": "Completar tratamiento", "detalles": [detail]})
    assert response.status_code == 200, response.text


def close(http, headers, process):
    return http.patch(f"/portal/veterinario/atenciones/{process}/estado", headers=headers[2], json={"estado": "cerrada"})


def test_admin_confirm_reschedule_cancel_produce_one_event_each(operations, provider):
    http, db, headers, start, _ = operations
    for payload, event in [
        ({"estado": "confirmada"}, "cita_confirmada"),
        ({"fecha_hora_programada": (start + dt.timedelta(hours=3)).isoformat()}, "cita_reprogramada"),
        ({"estado": "cancelada", "nota_coordinacion": "Cancelación coordinada"}, "cita_cancelada"),
    ]:
        response = http.patch("/admin/citas/1", headers=headers[4], json=payload)
        assert response.status_code == 200, response.text
        assert len(messages(db, event)) == 1
        outgoing = messages(db, event)[0]
        assert outgoing.destinatario == "51999888777" and outgoing.entidad_id == 1
        MessagingService(db).deliver(outgoing); db.commit()
        assert outgoing.estado == "enviado"
    assert len(provider) == 3
    assert "13:00" in messages(db, "cita_reprogramada")[0].contenido  # 18:00 UTC = 13:00 Lima.


@pytest.mark.parametrize("change", ["same_time", "assignment", "attendance", "proposal"])
def test_non_event_edits_do_not_send_new_confirmation(operations, change):
    http, db, headers, start, _ = operations
    assert http.patch("/admin/citas/1", headers=headers[4], json={"estado": "confirmada"}).status_code == 200
    before = len(db.scalars(select(MensajeSalida)).all())
    appointment = db.get(Cita, 1)
    if change == "same_time":
        response = http.patch("/admin/citas/1", headers=headers[4], json={"fecha_hora_programada": start.isoformat()})
        assert response.status_code == 200, response.text
    elif change == "assignment":
        response = http.patch("/admin/citas/1", headers=headers[4], json={"veterinario_id": 3})
        assert response.status_code == 200, response.text
    elif change == "attendance":
        appointment.asistencia_confirmada_en = now(); db.commit()
    else:
        appointment.fecha_hora_propuesta = start + dt.timedelta(hours=3); db.commit()
    assert len(db.scalars(select(MensajeSalida)).all()) == before


def test_veterinarian_confirmation_and_client_acceptance_notify_actual_time(operations):
    http, db, headers, start, _ = operations
    proposal = start + dt.timedelta(hours=3)
    response = http.patch("/portal/veterinario/solicitudes/1", headers=headers[2], json={"estado": "requiere_otro_horario", "fecha_hora_propuesta": proposal.isoformat()})
    assert response.status_code == 200, response.text
    assert not messages(db, "cita_reprogramada")
    response = http.patch("/portal/citas/1/aceptar-horario", headers=headers[1])
    assert response.status_code == 200, response.text
    assert len(messages(db, "cita_reprogramada")) == 1
    assert "13:00" in messages(db, "cita_reprogramada")[0].contenido
    assert http.patch("/portal/citas/1/aceptar-horario", headers=headers[1]).status_code == 409
    assert len(messages(db, "cita_reprogramada")) == 1


def test_veterinarian_confirmation_is_queued(operations):
    http, db, headers, *_ = operations
    response = http.patch("/portal/veterinario/solicitudes/1", headers=headers[2], json={"estado": "confirmada"})
    assert response.status_code == 200, response.text
    assert len(messages(db, "cita_confirmada")) == 1


def test_failed_appointment_update_rolls_back_messages(operations):
    http, db, headers, start, _ = operations
    response = http.patch("/admin/citas/1", headers=headers[4], json={"estado": "confirmada", "veterinario_id": 3, "fecha_hora_programada": (start + dt.timedelta(hours=1)).isoformat()})
    assert response.status_code == 409
    assert not messages(db, "cita_confirmada")


@pytest.mark.parametrize("preexisting", [False, True])
def test_closure_queues_pdf_and_one_matching_order_even_if_preissued(operations, provider, preexisting):
    http, db, headers, _, product = operations
    db.get(Cita, 1).telefono_contacto = "987 654 321"; db.commit()
    process = start_attention(http, db, headers)
    prescribe(http, headers, process, product)
    if preexisting:
        response = http.post("/operaciones/ordenes", headers=headers[2], json={"cliente_id": 1, "proceso_id": process, "detalles": [{"servicio_id": 1, "cantidad": 1}, {"producto_id": product, "cantidad": 2}], "clave_idempotencia": "preissued"})
        assert response.status_code == 201, response.text
    response = close(http, headers, process)
    assert response.status_code == 200, response.text
    assert len(db.scalars(select(OrdenPendiente)).all()) == 1
    order = db.scalar(select(OrdenPendiente))
    assert order.total == Decimal("90.00") and db.get(Producto, product).stock_actual == 10
    recipe = messages(db, "receta")[0]
    assert recipe.entidad_id == process and recipe.destinatario == "51987654321"
    assert recipe.documento.startswith(b"%PDF") and order.codigo in recipe.contenido
    MessagingService(db).deliver(recipe); db.commit()
    assert recipe.estado == "enviado" and len(provider) == 2
    upload, send = provider
    assert upload[0].endswith("/media") and upload[1]["files"]["file"][1].startswith(b"%PDF")
    template = send[1]["json"]["template"]
    assert template["name"] == "test_receta"
    assert send[1]["json"]["to"] == "51987654321"
    assert template["components"][0]["parameters"][0]["document"]["id"] == "media-pdf"
    assert [p["text"] for p in template["components"][1]["parameters"]] == ["María Pérez", "Luna", order.codigo]
    assert close(http, headers, process).status_code in {200, 409}
    assert len(messages(db, "receta")) == 1


def test_closure_rejects_an_order_that_omits_prescribed_products(operations):
    http, db, headers, _, product = operations
    process = start_attention(http, db, headers)
    prescribe(http, headers, process, product)
    response = http.post("/operaciones/ordenes", headers=headers[2], json={"cliente_id": 1, "proceso_id": process, "detalles": [{"servicio_id": 1, "cantidad": 1}], "clave_idempotencia": "incomplete"})
    assert response.status_code == 201, response.text
    response = close(http, headers, process)
    assert response.status_code == 409 and "no coincide" in response.json()["detail"]
    assert db.get(ProcesoAtencion, process).estado.value != "cerrada"
    assert not messages(db, "receta")


def test_free_service_still_generates_order_for_prescribed_products(operations):
    http, db, headers, _, product = operations
    db.get(Servicio, 1).precio_referencial = 0; db.commit()
    process = start_attention(http, db, headers)
    prescribe(http, headers, process, product)
    response = close(http, headers, process)
    assert response.status_code == 200, response.text
    assert db.scalar(select(OrdenPendiente)).total == Decimal("40.00")
    assert len(messages(db, "receta")) == 1


def test_cancellation_delivery_retries_after_provider_failure(operations, provider, monkeypatch):
    http, db, headers, *_ = operations
    assert http.patch("/portal/citas/1/cancelar", headers=headers[1], json={"motivo": "Cambio de planes"}).status_code == 200
    item = messages(db, "cita_cancelada")[0]
    transport = messaging_service.httpx.post

    def unavailable(url, **kwargs):
        raise httpx.ConnectError("Proveedor no disponible", request=httpx.Request("POST", url))

    monkeypatch.setattr(messaging_service.httpx, "post", unavailable)
    MessagingService(db).deliver(item); db.commit()
    assert item.estado == "error" and item.intentos == 1 and item.proximo_intento
    monkeypatch.setattr(messaging_service.httpx, "post", transport)
    item.proximo_intento = now() - dt.timedelta(seconds=1); db.commit()
    MessagingService(db).process()
    assert item.estado == "enviado" and item.intentos == 2
    assert len(messages(db, "cita_cancelada")) == 1
    assert webhook(http, monkeypatch, [{"id": item.proveedor_id, "status": "delivered"}]).status_code == 200
    assert db.get(MensajeSalida, item.id).estado == "entregado"


def test_waiting_retries_do_not_starve_ready_messages(operations, provider):
    http, db, headers, *_ = operations
    assert http.patch("/admin/citas/1", headers=headers[4], json={"estado": "confirmada"}).status_code == 200
    earlier = messages(db, "cita_confirmada")[0]
    earlier.proximo_intento = now() + dt.timedelta(hours=1); db.commit()
    assert http.patch("/portal/citas/1/cancelar", headers=headers[1], json={"motivo": "Cambio de planes"}).status_code == 200
    assert MessagingService(db).process(limit=1) == 1
    assert messages(db, "cita_cancelada")[0].estado == "enviado"
    assert earlier.estado == "pendiente" and earlier.intentos == 0


def test_webhook_preserves_read_and_delivered_when_callbacks_arrive_out_of_order(operations, provider, monkeypatch):
    http, db, headers, *_ = operations
    assert http.patch("/admin/citas/1", headers=headers[4], json={"estado": "confirmada"}).status_code == 200
    item = messages(db, "cita_confirmada")[0]
    MessagingService(db).deliver(item); db.commit()
    for state, expected in [("delivered", "entregado"), ("failed", "entregado"), ("read", "leido"), ("delivered", "leido"), ("failed", "leido")]:
        assert webhook(http, monkeypatch, [{"id": item.proveedor_id, "status": state}]).status_code == 200
        db.refresh(item)
        assert item.estado == expected and item.error is None and item.entregado_en is not None
    assert http.post("/whatsapp/webhook", json={}).status_code == 403


def test_missing_whatsapp_configuration_preserves_message_for_later(operations, monkeypatch):
    http, db, headers, *_ = operations
    monkeypatch.setattr(get_settings(), "whatsapp_access_token", "")
    assert http.patch("/portal/citas/1/cancelar", headers=headers[1], json={"motivo": "Cambio de planes"}).status_code == 200
    item = messages(db, "cita_cancelada")[0]
    MessagingService(db).deliver(item); db.commit()
    assert item.estado == "pendiente_configuracion" and item.intentos == 0
