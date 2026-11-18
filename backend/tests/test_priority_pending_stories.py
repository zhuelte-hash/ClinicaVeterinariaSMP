"""HU-032/097/066/100/101: ventanas, vigencia, transacciones y entrega controlada."""
import datetime as dt
from decimal import Decimal
from io import BytesIO
import json
from uuid import uuid4

import httpx
from pypdf import PdfReader
import pytest
from sqlalchemy import select

from test_admin_clinical_flows import clinic
from test_priority_stories import create_order, operations, proof
from app.config import get_settings
from app.models.clinic import Cita, ConfiguracionClinica, EstadoCita, EstadoPago, OrdenCobro, Producto
from app.models.operations import AbonoOrden, MensajeSalida, OrdenPendiente, PlantillaMensaje, Sucursal
from app.models.user import Usuario
from app.services import access_service, automation_service, messaging_service
from app.services.cashier_service import CashierService
from app.services.messaging_service import EVENTS, MessagingService


@pytest.fixture
def clock(monkeypatch):
    clock = {"now": dt.datetime.now(dt.timezone.utc).replace(microsecond=0)}
    monkeypatch.setattr(automation_service, "now", lambda: clock["now"])
    monkeypatch.setattr(messaging_service, "now", lambda: clock["now"])
    monkeypatch.setattr(access_service, "now", lambda: clock["now"])
    return clock


@pytest.fixture
def provider(operations, monkeypatch):
    _http, db, *_ = operations
    settings = get_settings()
    monkeypatch.setattr(settings, "whatsapp_access_token", "controlled-token")
    monkeypatch.setattr(settings, "whatsapp_phone_number_id", "controlled-number")
    for event in ("recordatorio_24h", "recordatorio_2h", "orden_creada", "orden_recordatorio", "pago_validado"):
        db.add(PlantillaMensaje(evento=event, nombre_proveedor="approved_" + event, idioma="es", contenido=EVENTS[event][0], variables=EVENTS[event][1], activa=True))
    db.commit()
    calls = []
    def post(url, **kwargs):
        calls.append((url, kwargs))
        result = {"id": "controlled-pdf"} if url.endswith("/media") else {"messages": [{"id": f"wamid.controlled.{len(calls)}"}]}
        return httpx.Response(200, request=httpx.Request("POST", url), json=result)
    monkeypatch.setattr(messaging_service.httpx, "post", post)
    return calls


def messages(db, event):
    return db.scalars(select(MensajeSalida).where(MensajeSalida.evento == event).order_by(MensajeSalida.id)).all()


def appointment(db, clock, remaining):
    row = db.get(Cita, 1)
    row.estado = EstadoCita.CONFIRMADA
    row.fecha_hora_programada = clock["now"] + remaining
    row.fecha_hora_fin_programada = row.fecha_hora_programada + dt.timedelta(minutes=30)
    row.telefono_contacto = "987654321"
    db.commit()
    return row


@pytest.mark.parametrize("seconds,event", [(86401, None), (86400, "recordatorio_24h"), (7201, "recordatorio_24h"), (7200, "recordatorio_2h"), (1, "recordatorio_2h"), (0, None), (-1, None)])
def test_appointment_reminder_boundaries_and_booking_phone(operations, provider, clock, seconds, event):
    _http, db, *_ = operations
    appointment(db, clock, dt.timedelta(seconds=seconds))
    for _ in range(2):
        automation_service.run_automations(db)
    rows = messages(db, "recordatorio_24h") + messages(db, "recordatorio_2h")
    assert len(rows) == (1 if event else 0)
    if event:
        assert rows[0].evento == event and rows[0].estado == "enviado"
        assert rows[0].destinatario == "51987654321"
        sent = [data["json"] for url, data in provider if url.endswith("/messages")]
        assert len(sent) == 1 and sent[0]["template"]["name"] == "approved_" + event
        assert sent[0]["template"]["language"]["code"] == "es"


def test_two_reminder_stages_each_send_once_and_deliver_is_idempotent(operations, provider, clock):
    _http, db, *_ = operations
    appointment(db, clock, dt.timedelta(hours=24))
    automation_service.run_automations(db)
    clock["now"] += dt.timedelta(hours=22)
    for _ in range(2):
        automation_service.run_automations(db)
    rows = messages(db, "recordatorio_24h") + messages(db, "recordatorio_2h")
    assert len(rows) == 2 and all(row.estado == "enviado" for row in rows)
    for row in rows:
        MessagingService(db).deliver(row)
    assert len(provider) == 2


@pytest.mark.parametrize("change", ["cancelled", "rescheduled", "arrived", "inactive_owner", "window_passed"])
def test_queued_reminder_is_cancelled_before_provider_when_obsolete(operations, provider, clock, monkeypatch, change):
    http, db, headers, *_ = operations
    row = appointment(db, clock, dt.timedelta(hours=23))
    monkeypatch.setattr(get_settings(), "whatsapp_access_token", "")
    automation_service.run_automations(db)
    reminder = messages(db, "recordatorio_24h")[0]
    if change == "cancelled": row.estado = EstadoCita.CANCELADA
    if change == "rescheduled": row.fecha_hora_programada += dt.timedelta(hours=1)
    if change == "arrived": row.fecha_hora_llegada = clock["now"]
    if change == "inactive_owner": db.get(Usuario, 1).activo = False
    if change == "window_passed": clock["now"] += dt.timedelta(hours=22)
    db.commit()
    monkeypatch.setattr(get_settings(), "whatsapp_access_token", "controlled-token")
    response = http.post(f"/admin/operaciones/mensajes/{reminder.id}/reintentar", headers=headers[4])
    assert response.status_code == 409, response.text
    assert reminder.estado == "cancelado" and reminder.intentos == 0 and not provider
    MessagingService(db).deliver(reminder)
    assert not provider


def test_disabling_reminders_pauses_pending_and_reenable_recovers_same_message(operations, provider, clock, monkeypatch):
    _http, db, *_ = operations
    appointment(db, clock, dt.timedelta(hours=23))
    monkeypatch.setattr(get_settings(), "whatsapp_access_token", "")
    automation_service.run_automations(db)
    reminder = messages(db, "recordatorio_24h")[0]
    config = ConfiguracionClinica(nombre="SMP", correo="clinic@example.com", recordatorios_citas=False)
    db.add(config); db.commit()
    monkeypatch.setattr(get_settings(), "whatsapp_access_token", "controlled-token")
    MessagingService(db).deliver(reminder)
    assert reminder.estado == "pendiente_configuracion" and reminder.intentos == 0 and not provider
    config.recordatorios_citas = True; db.commit()
    MessagingService(db).deliver(reminder)
    assert reminder.estado == "enviado" and len(provider) == 1


def test_reminders_for_second_branch_survive_global_queue_processing(operations, provider, clock):
    _http, db, *_ = operations
    row = appointment(db, clock, dt.timedelta(hours=1))
    db.add(Sucursal(id=2, nombre="Segunda sede")); db.flush()
    row.sucursal_id = 2; db.commit()
    automation_service.run_automations(db)
    assert db.info["sucursal_id"] == 1
    reminder = messages(db, "recordatorio_2h")[0]
    assert reminder.estado == "enviado" and len(provider) == 1


def test_created_order_message_is_unique_has_exact_amount_and_does_not_sell(operations, provider, clock):
    http, db, headers, _, product = operations
    order, payload = create_order(http, headers[5], product)
    assert http.post("/operaciones/ordenes", headers=headers[5], json=payload).status_code == 201
    rows = messages(db, "orden_creada")
    assert len(rows) == 1 and rows[0].parametros == ["María Pérez", order["codigo"], "40.00"]
    assert rows[0].entidad_id == order["id"] and db.get(Producto, product).stock_actual == 10
    assert not db.scalars(select(OrdenCobro)).all()
    MessagingService(db).deliver(rows[0]); db.commit()
    assert rows[0].estado == "enviado" and len(provider) == 1


@pytest.mark.parametrize("state", ["anulada", "pagada", "vencida"])
def test_created_order_message_not_sent_after_order_finalization(operations, provider, clock, state):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    db.get(OrdenPendiente, order["id"]).estado = state; db.commit()
    item = messages(db, "orden_creada")[0]
    MessagingService(db).deliver(item)
    assert item.estado == "cancelado" and not provider


@pytest.mark.parametrize("age,expected", [(7199, None), (7200, "pendiente"), (172799, "pendiente"), (172800, "vencida"), (172801, "vencida")])
def test_unpaid_order_reminder_starts_at_two_hours_and_expires_at_48(operations, provider, clock, age, expected):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    row = db.get(OrdenPendiente, order["id"])
    row.fecha = clock["now"] - dt.timedelta(seconds=age); db.commit()
    for _ in range(2): automation_service.run_automations(db)
    reminders = messages(db, "orden_recordatorio")
    assert len(reminders) == (1 if expected == "pendiente" else 0)
    if reminders: assert reminders[0].estado == "enviado"
    assert row.estado == (expected or "pendiente")
    if expected == "vencida":
        assert http.get("/operaciones/ordenes", headers=headers[5], params={"estado": "vencida"}).json()[0]["id"] == row.id
        assert http.get("/operaciones/ordenes", headers=headers[5], params={"sin_comprobante": True}).json() == []
        response = http.post(f"/operaciones/ordenes/{row.id}/abonos", headers=headers[5], json={"monto": 40, "medio": "efectivo", "canal": "caja", "clave_idempotencia": str(uuid4())})
        assert response.status_code == 409


@pytest.mark.parametrize("payment_state", ["proof", "validated_partial", "rejected"])
def test_two_hour_followup_excludes_pending_proof_and_validated_installment(operations, provider, clock, payment_state):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    row = db.get(OrdenPendiente, order["id"]); row.fecha = clock["now"] - dt.timedelta(hours=3)
    db.add(AbonoOrden(orden_id=row.id, registrado_por=1, monto=Decimal("10.00"), medio="yape", canal="web", comprobante=proof(), comprobante_tipo="image/png", estado={"proof": "enviado", "validated_partial": "validado", "rejected": "rechazado"}[payment_state], clave_idempotencia=str(uuid4()))); db.commit()
    automation_service.run_automations(db)
    assert len(messages(db, "orden_recordatorio")) == (1 if payment_state == "rejected" else 0)


def test_order_reminder_revalidates_proof_uploaded_after_enqueue(operations, provider, clock, monkeypatch):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    row = db.get(OrdenPendiente, order["id"]); row.fecha = clock["now"] - dt.timedelta(hours=3); db.commit()
    monkeypatch.setattr(get_settings(), "whatsapp_access_token", "")
    automation_service.run_automations(db)
    reminder = messages(db, "orden_recordatorio")[0]
    data = {"monto": "40.00", "medio": "yape", "canal": "web", "clave_idempotencia": str(uuid4())}
    response = http.post(f"/operaciones/ordenes/{row.id}/comprobantes", headers=headers[1], data={"datos": json.dumps(data)}, files={"archivo": ("proof.png", proof(), "image/png")})
    assert response.status_code == 201, response.text
    monkeypatch.setattr(get_settings(), "whatsapp_access_token", "controlled-token")
    MessagingService(db).deliver(reminder)
    assert reminder.estado == "cancelado" and not provider


def test_full_payment_queues_single_real_pdf_only_after_validation(operations, provider, clock):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    data = {"monto": "40.00", "medio": "yape", "canal": "web", "clave_idempotencia": str(uuid4())}
    response = http.post(f"/operaciones/ordenes/{order['id']}/comprobantes", headers=headers[1], data={"datos": json.dumps(data)}, files={"archivo": ("proof.png", proof(), "image/png")})
    assert response.status_code == 201, response.text
    assert not messages(db, "pago_validado")
    payment = response.json()["abonos"][0]["id"]
    for _ in range(2):
        response = http.post(f"/operaciones/pagos/{payment}/validar", headers=headers[5])
        assert response.status_code == 200, response.text
    rows = messages(db, "pago_validado")
    assert len(rows) == 1 and rows[0].entidad_id == order["id"]
    assert rows[0].parametros == ["María Pérez", order["codigo"]]
    pdf = PdfReader(BytesIO(rows[0].documento))
    assert "40.00" in pdf.pages[0].extract_text() and "Medicina" in pdf.pages[0].extract_text()
    MessagingService(db).deliver(rows[0]); db.commit()
    assert rows[0].estado == "enviado" and len(provider) == 2
    assert provider[0][0].endswith("/media")
    payload = provider[1][1]["json"]
    assert payload["template"]["components"][0]["parameters"][0]["document"]["id"] == "controlled-pdf"
    assert db.get(Producto, product).stock_actual == 8


def test_partial_payments_do_not_emit_full_payment_notice(operations, provider, clock):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    url = f"/operaciones/ordenes/{order['id']}/abonos"
    response = http.post(url, headers=headers[5], json={"monto": 10, "medio": "efectivo", "canal": "caja", "clave_idempotencia": str(uuid4())})
    assert response.status_code == 201 and response.json()["estado"] == "parcial"
    assert not messages(db, "pago_validado")
    response = http.post(url, headers=headers[5], json={"monto": 30, "medio": "efectivo", "canal": "caja", "clave_idempotencia": str(uuid4())})
    assert response.status_code == 201 and response.json()["estado"] == "pagada"
    assert len(messages(db, "pago_validado")) == 1


@pytest.mark.parametrize("customer", [1, None])
def test_direct_sale_payment_notice_requires_identified_customer_and_is_idempotent(operations, provider, clock, customer):
    http, db, headers, _, product = operations
    data = {"cliente_id": customer, "medio_pago": "efectivo", "items": [{"producto_id": product, "cantidad": 1}], "clave_idempotencia": str(uuid4())}
    response = http.post("/api/ventas", headers=headers[5], json=data)
    assert response.status_code == 201, response.text
    assert http.post("/api/ventas", headers=headers[5], json=data).status_code == 201
    rows = messages(db, "pago_validado")
    assert len(rows) == (1 if customer else 0)
    if customer:
        assert rows[0].entidad_id == response.json()["orden_id"] and rows[0].documento.startswith(b"%PDF")
        MessagingService(db).deliver(rows[0]); db.commit()
        assert rows[0].estado == "enviado" and len(provider) == 2


def test_void_sale_cancels_queued_payment_confirmation(operations, provider, clock):
    http, db, headers, _, product = operations
    response = http.post("/api/ventas", headers=headers[5], json={"cliente_id": 1, "medio_pago": "efectivo", "items": [{"producto_id": product, "cantidad": 1}]})
    assert response.status_code == 201, response.text
    id = response.json()["orden_id"]
    assert http.post(f"/operaciones/ventas/{id}/anular", headers=headers[5], json={"motivo": "Venta equivocada"}).status_code == 200
    item = messages(db, "pago_validado")[0]
    MessagingService(db).deliver(item)
    assert item.estado == "cancelado" and not provider


def test_sale_and_notice_are_rolled_back_together_on_failure(operations, provider, clock, monkeypatch):
    http, db, headers, _, product = operations
    original = CashierService._queue_payment_confirmation
    def fail(self, *args):
        original(self, *args)
        raise RuntimeError("Fallo después de encolar confirmación")
    monkeypatch.setattr(CashierService, "_queue_payment_confirmation", fail)
    with pytest.raises(RuntimeError, match="Fallo después"):
        http.post("/api/ventas", headers=headers[5], json={"cliente_id": 1, "medio_pago": "efectivo", "items": [{"producto_id": product, "cantidad": 1}]})
    assert not messages(db, "pago_validado") and not db.scalars(select(OrdenCobro)).all()
    assert db.get(Producto, product).stock_actual == 10


def test_invalid_contact_waits_without_attempt_then_uses_corrected_phone(operations, provider, clock):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    user = db.get(Usuario, 1); user.cliente.telefono = "123"; db.commit()
    item = messages(db, "orden_creada")[0]
    MessagingService(db).deliver(item)
    assert item.estado == "pendiente_configuracion" and item.intentos == 0 and not provider
    user.cliente.telefono = "999111222"; db.commit()
    MessagingService(db).deliver(item)
    assert item.estado == "enviado" and item.destinatario == "51999111222" and len(provider) == 1


@pytest.mark.parametrize("action", ["APROBAR", "RECHAZAR"])
def test_web_purchase_confirms_with_pdf_only_when_approved(operations, provider, clock, monkeypatch, action):
    http, db, headers, _, product = operations
    settings = get_settings()
    for name, value in {"purchase_yape_holder": "Clínica de prueba", "purchase_yape_phone": "999888777", "purchase_yape_qr_url": "/qr-test.png"}.items():
        monkeypatch.setattr(settings, name, value)
    db.get(Producto, product).imagen_url = "/test-product.png"; db.commit()
    payload = {"clave_idempotencia": str(uuid4()), "cliente": {"nombreCompleto": "María Pérez", "celular": "999888777", "correo": "owner@example.com", "tipoEntrega": "Recojo en clínica", "tipoComprobante": "Boleta", "dni": "12345678"}, "items": [{"producto_id": product, "cantidad": 2}], "metodo_pago": "yape", "numero_operacion": "WEB-123", "total_esperado": "40.00"}
    response = http.post("/pedidos-web", headers=headers[1], data={"datos": json.dumps(payload)}, files={"comprobante": ("proof.png", proof(), "image/png")})
    assert response.status_code == 201, response.text
    assert not messages(db, "pago_validado")
    id = response.json()["id"]
    response = http.post(f"/pedidos-web/{id}/revision", headers=headers[5], json={"accion": action, "motivo": "Revisión de prueba"})
    assert response.status_code == 200, response.text
    rows = messages(db, "pago_validado")
    assert len(rows) == (1 if action == "APROBAR" else 0)
    assert db.get(Producto, product).stock_actual == (8 if action == "APROBAR" else 10)
    if rows:
        assert rows[0].entidad_id == response.json()["venta_id"] and rows[0].documento.startswith(b"%PDF")
        MessagingService(db).deliver(rows[0])
        assert rows[0].estado == "enviado" and len(provider) == 2
        assert http.post(f"/pedidos-web/{id}/revision", headers=headers[5], json={"accion": action}).status_code == 409
        assert len(messages(db, "pago_validado")) == 1


def test_queued_order_reminder_is_not_delivered_after_48_hours(operations, provider, clock, monkeypatch):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    row = db.get(OrdenPendiente, order["id"]); row.fecha = clock["now"] - dt.timedelta(hours=3); db.commit()
    monkeypatch.setattr(get_settings(), "whatsapp_access_token", "")
    automation_service.run_automations(db)
    item = messages(db, "orden_recordatorio")[0]
    clock["now"] += dt.timedelta(hours=45)
    monkeypatch.setattr(get_settings(), "whatsapp_access_token", "controlled-token")
    automation_service.run_automations(db)
    assert row.estado == "vencida" and item.estado == "cancelado" and not provider


def test_confirmation_without_pdf_waits_and_does_not_send_plain_text(operations, provider, clock):
    http, db, headers, _, product = operations
    response = http.post("/api/ventas", headers=headers[5], json={"cliente_id": 1, "medio_pago": "efectivo", "items": [{"producto_id": product, "cantidad": 1}]})
    assert response.status_code == 201
    item = messages(db, "pago_validado")[0]
    item.documento = None; db.commit()
    MessagingService(db).deliver(item)
    assert item.estado == "pendiente_configuracion" and item.intentos == 0 and not provider


def test_future_confirmed_appointment_is_not_expired_by_no_show_query(operations, clock):
    _http, db, *_ = operations
    row = appointment(db, clock, dt.timedelta(hours=23))
    from app.services.appointment_service import AppointmentService
    assert AppointmentService(db).expire_unattended_appointments() == []
    db.refresh(row)
    assert row.estado == EstadoCita.CONFIRMADA and row.cancelacion_automatica_at is None
