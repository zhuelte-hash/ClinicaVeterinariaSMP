"""Cierre funcional manual: teléfono público, asistencia, bandejas y avisos vigentes."""
import datetime as dt
import json
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from sqlalchemy import select

from test_admin_clinical_flows import clinic
from test_priority_stories import operations, create_order, proof
from test_next_five_stories import start_attention
from test_priority_communications import prescribe, close
from test_fundamental_stories import prepare_attendance
from test_manual_whatsapp import manual
from app.config import get_settings
from app.models.clinic import AplicacionPreventiva, Cita, ConfiguracionClinica, EstadoCita, Notificacion, OrdenCobro, ProcesoAtencion, ProcesoAtencionMedica, Producto
from app.models.operations import DesafioCuenta, EventoAuditoria, EventoCita, MensajeSalida, Sucursal
from app.models.user import PermisoRol, TipoUsuario, Usuario
from app.services import automation_service, messaging_service
from app.services.access_service import digest, now
from app.services.messaging_service import MessagingService
from app.services.policy_service import ZONE
from scripts.set_clinic_whatsapp import set_phone

BASE = "/operaciones/comunicaciones/manuales"


def messages(db, event):
    return db.scalars(select(MensajeSalida).where(MensajeSalida.evento == event).order_by(MensajeSalida.id)).all()


def attention(operations):
    http, db, headers, _, product = operations
    process = start_attention(http, db, headers)
    prescribe(http, headers, process, product)
    assert close(http, headers, process).status_code == 200
    return process, messages(db, "receta")[-1], messages(db, "orden_creada")[-1]


def reference(operations):
    http, db, headers, *_ = operations
    prepare_attendance(db)
    set_phone(db, "938304590")
    data = http.get("/portal/citas/1/asistencia-whatsapp", headers=headers[1]).json()
    return {"telefono_remitente": "999888777", "referencia": data["comando"]}, data


def test_configured_phone_is_shared_by_public_contact_checkout_and_client_links(operations, manual):
    http, db, headers, _, product = operations
    db.add(ConfiguracionClinica(nombre="Clínica original", correo="clinic@example.com", telefono="965939522", direccion="Conservar dirección", recordatorios_citas=False)); db.commit()
    assert set_phone(db, "938304590") == "51938304590"
    contact = http.get("/publico/contacto").json()
    assert contact["telefono"] == "938304590" and contact["telefono_mostrado"] == "938 304 590"
    assert contact["whatsapp"] == contact["internacional"] == "51938304590"
    assert "correo" not in contact and "secret_key" not in contact
    assert http.get("/pedidos-web/configuracion").json()["whatsappNumber"] == "51938304590"
    config = http.get("/admin/configuracion", headers=headers[4]).json()
    assert config["direccion"] == "Conservar dirección" and not config["recordatorios_citas"]
    order, _ = create_order(http, headers[5], product)
    result = http.post(f"/operaciones/ordenes/{order['id']}/preparar-whatsapp", headers=headers[1], json={"monto": "40.00", "medio": "yape"})
    assert urlsplit(result.json()["whatsapp_url"]).path == "/51938304590"


def test_manual_attendance_persists_in_all_agendas_once_with_operator_audit(operations, manual):
    http, db, headers, *_ = operations
    payload, instructions = reference(operations)
    assert "ASISTIRE 1 " in payload["referencia"]
    assert urlsplit(instructions["whatsapp_url"]).path == "/51938304590"
    assert parse_qs(urlsplit(instructions["whatsapp_url"]).query)["text"] == [payload["referencia"]]
    endpoint = "/admin/operaciones/citas/1/asistencia-manual"
    for _ in range(2):
        response = http.post(endpoint, headers=headers[4], json=payload)
        assert response.status_code == 200, response.text
        assert response.json()["canal"] == "whatsapp_manual"
        assert response.headers["cache-control"] == "private, no-store"
    assert db.get(Cita, 1).asistencia_confirmada_en is not None
    events = db.scalars(select(EventoCita).where(EventoCita.cita_id == 1, EventoCita.accion == "asistencia_confirmada")).all()
    assert len(events) == 1 and events[0].usuario_id == 4
    assert len(db.scalars(select(Notificacion).where(Notificacion.tipo == "asistencia_confirmada")).all()) == 1
    own = http.get("/portal/citas", headers=headers[1]).json()
    assert next(item for item in own if item["id"] == 1)["asistencia_confirmada_en"]
    admin = http.get("/admin/citas", headers=headers[4]).json()
    assert next(item for item in admin if item["id"] == 1)["asistencia_confirmada_en"]
    vet = http.get("/portal/veterinario/solicitudes?incluir_finalizadas=true", headers=headers[2]).json()
    assert next(item for item in vet if item["id"] == 1)["asistencia_confirmada_en"]


@pytest.mark.parametrize("case", ["phone", "code", "other_id", "date", "inactive", "unverified", "arrived", "started", "cancelled", "permission", "branch", "client"])
def test_invalid_or_obsolete_manual_attendance_does_not_confirm(operations, manual, case):
    http, db, headers, *_ = operations
    payload, _ = reference(operations)
    appointment = db.get(Cita, 1)
    request_headers = headers[4]
    expected = 409
    if case == "phone": payload["telefono_remitente"] = "988777666"
    if case == "code": payload["referencia"] = "ASISTIRE 1 " + "0" * 16
    if case == "other_id": payload["referencia"] = payload["referencia"].replace("ASISTIRE 1 ", "ASISTIRE 2 ")
    if case == "date": appointment.fecha_hora_programada += dt.timedelta(hours=1)
    if case == "inactive": db.get(Usuario, 1).activo = False
    if case == "unverified": db.get(Usuario, 1).correo_verificado = False
    if case == "arrived": appointment.fecha_hora_llegada = now()
    if case == "started": db.add(ProcesoAtencion(cita_id=1, mascota_id=1, tipo="medica", estado="en_atencion"))
    if case == "cancelled": appointment.estado = EstadoCita.CANCELADA
    if case == "permission":
        db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="citas", puede_ver=True, puede_editar=False)); expected = 403
    if case == "branch":
        db.add(Sucursal(id=2, nombre="Otra sede")); request_headers = {**headers[4], "X-Sucursal-ID": "2"}; expected = 404
    if case == "client": request_headers = headers[1]; expected = 403
    db.commit()
    response = http.post("/admin/operaciones/citas/1/asistencia-manual", headers=request_headers, json=payload)
    assert response.status_code == expected, response.text
    assert appointment.asistencia_confirmada_en is None
    assert not db.scalars(select(Notificacion).where(Notificacion.tipo == "asistencia_confirmada")).all()


def test_rescheduling_invalidates_old_manual_reference_and_accepts_new_one(operations, manual):
    http, db, headers, *_ = operations
    previous, _ = reference(operations)
    appointment = db.get(Cita, 1)
    appointment.fecha_hora_programada += dt.timedelta(minutes=30)
    appointment.fecha_hora_fin_programada += dt.timedelta(minutes=30)
    db.commit()
    endpoint = "/admin/operaciones/citas/1/asistencia-manual"
    assert http.post(endpoint, headers=headers[4], json=previous).status_code == 409
    updated = http.get("/portal/citas/1/asistencia-whatsapp", headers=headers[1]).json()
    assert http.post(endpoint, headers=headers[4], json={**previous, "referencia": updated["comando"]}).status_code == 200


def test_vet_and_cashier_send_only_their_authorized_operational_messages(operations, manual):
    http, db, headers, *_ = operations
    _, recipe, order = attention(operations)
    vet = http.get(BASE, headers=headers[2])
    assert vet.status_code == 200, vet.text
    assert {recipe.id, order.id} <= {item["id"] for item in vet.json()["mensajes"]}
    assert "contenido" not in vet.json()["mensajes"][0]
    assert http.post(f"{BASE}/{recipe.id}/preparar", headers=headers[2], json={}).status_code == 200
    assert http.post(f"{BASE}/{recipe.id}/pdf", headers=headers[2], json={}).content == recipe.documento
    assert http.post(f"{BASE}/{recipe.id}/preparar", headers=headers[3], json={}).status_code == 404
    cashier = http.get(BASE, headers=headers[5])
    assert cashier.status_code == 200
    assert order.id in {item["id"] for item in cashier.json()["mensajes"]}
    assert recipe.id not in {item["id"] for item in cashier.json()["mensajes"]}
    assert http.post(f"{BASE}/{recipe.id}/pdf", headers=headers[5], json={}).status_code == 404
    assert http.post(f"{BASE}/{order.id}/preparar", headers=headers[5], json={}).status_code == 200
    for _ in range(2):
        assert http.post(f"{BASE}/{recipe.id}/gestionar", headers=headers[2], json={}).status_code == 200
    audit = db.scalars(select(EventoAuditoria).where(EventoAuditoria.entidad == "mensajes_salida", EventoAuditoria.registro_id == str(recipe.id))).all()
    assert len(audit) == 1 and audit[0].usuario_id == 2
    assert "contenido" not in str(audit[0].cambios)
    assert recipe.enviado_en is None and recipe.entregado_en is None


def test_accepted_referral_grants_manual_access_only_to_the_referred_case(operations, manual):
    http, db, headers, *_ = operations
    process, recipe, _ = attention(operations)
    assert http.post(f"{BASE}/{recipe.id}/preparar", headers=headers[3], json={}).status_code == 404
    referral = http.post(f"/portal/veterinario/atenciones/{process}/derivaciones", headers=headers[2], json={"receptor_id": 3, "motivo": "Continuación del caso"})
    assert referral.status_code == 201, referral.text
    assert http.post(f"/portal/veterinario/derivaciones/{referral.json()['id']}/responder", headers=headers[3], json={"aceptar": True, "respuesta": "Acepto el caso"}).status_code == 200
    assert http.post(f"{BASE}/{recipe.id}/preparar", headers=headers[3], json={}).status_code == 200
    assert db.get(Cita, 1).veterinario_id == 2


def test_staff_list_and_actions_are_isolated_by_selected_branch(operations, manual):
    http, db, headers, _, product = operations
    _, _ = create_order(http, headers[5], product)
    item = messages(db, "orden_creada")[-1]
    db.add(Sucursal(id=2, nombre="Segunda sede")); db.commit()
    other = {**headers[4], "X-Sucursal-ID": "2"}
    assert http.get(BASE, headers=other).json()["mensajes"] == []
    assert http.post(f"{BASE}/{item.id}/preparar", headers=other, json={}).status_code == 404
    assert http.get(BASE, headers={**headers[5], "X-Sucursal-ID": "2"}).status_code == 403


def test_revoked_modules_hide_messages_and_cannot_be_bypassed_with_manual_api(operations, manual):
    http, db, headers, *_ = operations
    _, recipe, _ = attention(operations)
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="historias_clinicas", puede_ver=False)); db.commit()
    data = http.get(BASE, headers=headers[4]).json()
    assert recipe.id not in {row["id"] for row in data["mensajes"]}
    assert http.post(f"{BASE}/{recipe.id}/preparar", headers=headers[4], json={}).status_code == 403
    assert http.get(BASE, headers=headers[1]).status_code == 403


@pytest.mark.parametrize("role,module", [(2, "historias_clinicas"), (5, "ventas")])
def test_read_only_staff_can_consult_but_not_prepare_messages(operations, manual, role, module):
    http, db, headers, *_ = operations
    _, recipe, order = attention(operations)
    target = recipe if role == 2 else order
    db.add(PermisoRol(rol=TipoUsuario.VETERINARIO if role == 2 else TipoUsuario.CAJERO, modulo=module, puede_ver=True, puede_editar=False, puede_crear=False)); db.commit()
    data = http.get(BASE, headers=headers[role]).json()
    assert not data["puede_gestionar"]
    assert http.post(f"{BASE}/{target.id}/preparar", headers=headers[role], json={}).status_code == 403


@pytest.mark.parametrize("case", ["cancelled", "time", "inactive", "contact"])
def test_client_appointment_notice_rechecks_state_date_and_current_contact(operations, manual, case):
    http, db, headers, start, _ = operations
    assert http.patch("/admin/citas/1", headers=headers[4], json={"estado": "confirmada"}).status_code == 200
    item = messages(db, "cita_confirmada")[-1]
    if case == "cancelled":
        assert http.patch("/portal/citas/1/cancelar", headers=headers[1], json={"motivo": "Cambio de planes"}).status_code == 200
    if case == "time":
        assert http.patch("/admin/citas/1", headers=headers[4], json={"fecha_hora_programada": (start + dt.timedelta(hours=3)).isoformat()}).status_code == 200
    if case == "inactive": db.get(Usuario, 1).activo = False; db.commit()
    if case == "contact": db.get(Cita, 1).telefono_contacto = "938304590"; db.commit()
    result = http.post(f"{BASE}/{item.id}/preparar", headers=headers[4], json={})
    if case == "contact":
        assert result.status_code == 200 and result.json()["destinatario"] == "51938304590"
    else:
        assert result.status_code == 409 and item.estado == "cancelado"
    assert item.intentos == 0


def test_professional_notice_is_invalidated_by_cancel_or_reassignment(operations, manual):
    http, db, headers, start, _ = operations
    db.get(Usuario, 2).telefono_personal = "988777666"; db.commit()
    assert http.patch("/admin/citas/1", headers=headers[4], json={"estado": "confirmada"}).status_code == 200
    assert http.patch("/admin/citas/1", headers=headers[4], json={"fecha_hora_programada": (start + dt.timedelta(hours=3)).isoformat()}).status_code == 200
    old = messages(db, "veterinario_reprogramacion")[-1]
    assert http.patch("/portal/citas/1/cancelar", headers=headers[1], json={"motivo": "Cambio de planes"}).status_code == 200
    assert http.post(f"{BASE}/{old.id}/preparar", headers=headers[4], json={}).status_code == 409
    cancelled = messages(db, "veterinario_cancelacion")[-1]
    db.get(Usuario, 2).telefono_personal = "938304590"; db.commit()
    result = http.post(f"{BASE}/{cancelled.id}/preparar", headers=headers[4], json={})
    assert result.status_code == 200 and result.json()["destinatario"] == "51938304590"


def vaccine_notice(operations, monkeypatch):
    _, db, *_ = operations
    fixed = now()
    monkeypatch.setattr(automation_service, "now", lambda: fixed)
    monkeypatch.setattr(messaging_service, "now", lambda: fixed)
    process = ProcesoAtencion(mascota_id=1, tipo="medica", estado="en_atencion")
    db.add(process); db.flush(); db.add(ProcesoAtencionMedica(proceso_id=process.id, veterinario_id=2))
    vaccine = AplicacionPreventiva(proceso_id=process.id, veterinario_id=2, tipo="vacuna", producto="Vacuna anual", proxima_fecha=fixed.astimezone(ZONE).date() + dt.timedelta(days=3))
    db.add(vaccine); db.commit()
    automation_service.run_automations(db)
    return vaccine, messages(db, "vacuna")[-1], fixed


@pytest.mark.parametrize("case", ["date", "past", "owner", "type", "contact", "product"])
def test_vaccine_notice_revalidates_actual_schedule_owner_and_contact(operations, manual, monkeypatch, case):
    http, db, headers, *_ = operations
    vaccine, item, fixed = vaccine_notice(operations, monkeypatch)
    if case == "date": vaccine.proxima_fecha += dt.timedelta(days=1)
    if case == "past": vaccine.proxima_fecha = fixed.astimezone(ZONE).date() - dt.timedelta(days=1)
    if case == "owner": db.get(Usuario, 1).activo = False
    if case == "type": vaccine.tipo = "desparasitacion"
    if case == "contact": db.get(Usuario, 1).cliente.telefono = "938304590"
    if case == "product": vaccine.producto = "Vacuna corregida"
    db.commit()
    response = http.post(f"{BASE}/{item.id}/preparar", headers=headers[4], json={})
    if case in {"contact", "product"}:
        assert response.status_code == 200, response.text
        if case == "contact": assert response.json()["destinatario"] == "51938304590"
        if case == "product": assert "Vacuna corregida" in response.json()["contenido"]
    else:
        assert response.status_code == 409 and item.estado == "cancelado"
    assert item.intentos == 0


def test_reduced_vaccine_window_waits_and_can_be_prepared_again_when_restored(operations, manual, monkeypatch):
    http, db, headers, *_ = operations
    _, item, _ = vaccine_notice(operations, monkeypatch)
    assert http.put("/admin/operaciones/politicas-vacunas", headers=headers[4], json={"dias_recordatorio_vacuna": 0}).status_code == 200
    assert http.post(f"{BASE}/{item.id}/preparar", headers=headers[4], json={}).status_code == 409
    assert item.estado == "pendiente_configuracion"
    assert http.put("/admin/operaciones/politicas-vacunas", headers=headers[4], json={"dias_recordatorio_vacuna": 3}).status_code == 200
    assert http.post(f"{BASE}/{item.id}/preparar", headers=headers[4], json={}).status_code == 200
    assert len(messages(db, "vacuna")) == 1


def test_scheduled_survey_is_private_in_inbox_and_closes_after_owner_response(operations, manual):
    http, db, headers, *_ = operations
    process = ProcesoAtencion(mascota_id=1, tipo="medica", estado="cerrada", fecha_cierre=now() - dt.timedelta(hours=25))
    db.add(process); db.flush(); db.add(ProcesoAtencionMedica(proceso_id=process.id, veterinario_id=2)); db.commit()
    assert http.post("/admin/operaciones/automatizaciones", headers=headers[4], json={}).status_code == 200
    item = messages(db, "encuesta")[-1]
    assert len(messages(db, "encuesta")) == 1
    inbox = http.get(BASE, headers=headers[2]).json()
    assert item.id in {row["id"] for row in inbox["mensajes"]}
    assert "encuesta/" not in str(inbox)
    prepared = http.post(f"{BASE}/{item.id}/preparar", headers=headers[2], json={}).json()
    from re import search
    token = search(r"/encuesta/([A-Za-z0-9_-]+)", prepared["contenido"])[1]
    assert http.post(f"/encuestas/{token}", json={"valoracion": 5, "comentario": "Prueba manual"}).status_code == 204
    assert http.post(f"{BASE}/{item.id}/preparar", headers=headers[2], json={}).status_code == 409
    assert item.estado == "cancelado"


def test_laboratory_notice_can_be_prepared_by_attending_vet_without_results_in_text(operations, manual):
    http, db, headers, *_ = operations
    process = start_attention(http, db, headers)
    assert http.patch(f"/portal/veterinario/atenciones/{process}/resultados", headers=headers[2], json={"examenes_resultados": "Resultado clínico privado"}).status_code == 200
    item = messages(db, "laboratorio")[-1]
    result = http.post(f"{BASE}/{item.id}/preparar", headers=headers[2], json={})
    assert result.status_code == 200, result.text
    assert "/mis-mascotas" in result.json()["contenido"] and "clínico privado" not in result.json()["contenido"]
    assert http.post(f"{BASE}/{item.id}/preparar", headers=headers[3], json={}).status_code == 404


def test_manual_welcome_is_created_only_once_after_email_verification(operations, manual):
    http, db, headers, *_ = operations
    owner = db.get(Usuario, 1); owner.correo_verificado = False
    db.add(DesafioCuenta(usuario_id=1, proposito="verificar", secreto_hash=digest("1:verificar:123456"), expira_en=now() + dt.timedelta(minutes=15))); db.commit()
    payload = {"correo": owner.correo, "codigo": "123456"}
    assert http.post("/auth/verificar-correo", json=payload).status_code == 200
    assert http.post("/auth/verificar-correo", json=payload).status_code == 400
    item, = messages(db, "bienvenida")
    prepared = http.post(f"{BASE}/{item.id}/preparar", headers=headers[4], json={})
    assert prepared.status_code == 200 and "María Pérez" in prepared.json()["contenido"]
    assert item.estado == "pendiente_manual" and item.intentos == 0 and item.enviado_en is None


def test_both_reminder_stages_are_prepared_once_and_old_stage_cannot_be_opened(operations, manual, monkeypatch):
    http, db, headers, *_ = operations
    clock = [now()]
    monkeypatch.setattr(automation_service, "now", lambda: clock[0])
    monkeypatch.setattr(messaging_service, "now", lambda: clock[0])
    appointment = db.get(Cita, 1); appointment.estado = EstadoCita.CONFIRMADA
    appointment.fecha_hora_programada = clock[0] + dt.timedelta(hours=3)
    appointment.fecha_hora_fin_programada = appointment.fecha_hora_programada + dt.timedelta(minutes=30); db.commit()
    for _ in range(2):
        assert http.post("/admin/operaciones/automatizaciones", headers=headers[4], json={}).status_code == 200
    early, = messages(db, "recordatorio_24h")
    assert http.post(f"{BASE}/{early.id}/preparar", headers=headers[4], json={}).status_code == 200
    clock[0] += dt.timedelta(hours=2)
    for _ in range(2):
        assert http.post("/admin/operaciones/automatizaciones", headers=headers[4], json={}).status_code == 200
    late, = messages(db, "recordatorio_2h")
    assert http.post(f"{BASE}/{early.id}/preparar", headers=headers[4], json={}).status_code == 409
    assert http.post(f"{BASE}/{late.id}/preparar", headers=headers[4], json={}).status_code == 200
    assert early.estado == "cancelado" and late.estado == "pendiente_manual"


def test_order_followup_is_prepared_then_invalidated_by_a_recorded_payment(operations, manual):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    from app.models.operations import OrdenPendiente
    pending = db.get(OrdenPendiente, order["id"]); pending.fecha = now() - dt.timedelta(hours=2, minutes=1); db.commit()
    assert http.post("/admin/operaciones/automatizaciones", headers=headers[4], json={}).status_code == 200
    follow, = messages(db, "orden_recordatorio")
    assert http.post(f"{BASE}/{follow.id}/preparar", headers=headers[5], json={}).status_code == 200
    response = http.post(f"/operaciones/ordenes/{order['id']}/abonos", headers=headers[5], json={"monto": "10.00", "medio": "efectivo", "canal": "caja", "clave_idempotencia": str(uuid4())})
    assert response.status_code == 201, response.text
    assert http.post(f"{BASE}/{follow.id}/preparar", headers=headers[5], json={}).status_code == 409
    assert follow.estado == "cancelado" and messages(db, "pago_validado") == []


def test_manual_proof_is_loaded_reviewed_and_exposes_one_receipt_in_cashier_inbox(operations, manual):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    data = {"monto": "40.00", "medio": "yape", "canal": "whatsapp", "clave_idempotencia": str(uuid4())}
    received = http.post(f"/operaciones/ordenes/{order['id']}/comprobantes", headers=headers[5], data={"datos": json.dumps(data)}, files={"archivo": ("pago.png", proof(), "image/png")})
    assert received.status_code == 201, received.text
    payment = received.json()["abonos"][0]
    assert payment["estado"] == "enviado" and db.get(Producto, product).stock_actual == 10
    for _ in range(2):
        assert http.post(f"/operaciones/pagos/{payment['id']}/validar", headers=headers[5]).status_code == 200
    receipt, = messages(db, "pago_validado")
    assert receipt.id in {row["id"] for row in http.get(BASE, headers=headers[5]).json()["mensajes"]}
    pdf = http.post(f"{BASE}/{receipt.id}/pdf", headers=headers[5], json={})
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert http.post(f"{BASE}/{receipt.id}/gestionar", headers=headers[5], json={}).status_code == 200
    assert db.get(Producto, product).stock_actual == 8
    assert len(db.scalars(select(OrdenCobro)).all()) == 1


def test_legacy_payment_reference_remains_available_in_correct_branch(operations, manual):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    paid = http.post(f"/operaciones/ordenes/{order['id']}/abonos", headers=headers[5], json={"monto": "40.00", "medio": "efectivo", "canal": "caja", "clave_idempotencia": str(uuid4())})
    assert paid.status_code == 201
    receipt, = messages(db, "pago_validado")
    receipt.entidad_id = None; db.commit()
    assert receipt.id in {item["id"] for item in http.get(BASE, headers=headers[5]).json()["mensajes"]}
    assert http.post(f"{BASE}/{receipt.id}/pdf", headers=headers[5], json={}).status_code == 200
    db.add(Sucursal(id=2, nombre="Otra sede")); db.commit()
    other = {**headers[4], "X-Sucursal-ID": "2"}
    assert http.post(f"{BASE}/{receipt.id}/pdf", headers=other, json={}).status_code == 404


@pytest.mark.parametrize("origin", ["direct", "web"])
def test_direct_and_web_sale_receipts_are_available_only_after_validation(operations, manual, monkeypatch, origin):
    http, db, headers, _, product = operations
    if origin == "direct":
        response = http.post("/api/ventas", headers=headers[5], json={"cliente_id": 1, "medio_pago": "efectivo", "clave_idempotencia": str(uuid4()), "items": [{"producto_id": product, "cantidad": 2}]})
        assert response.status_code == 201, response.text
    else:
        for field, value in {"purchase_yape_holder": "Clínica", "purchase_yape_phone": "938304590", "purchase_yape_qr_url": "/qr-prueba.png"}.items():
            monkeypatch.setattr(get_settings(), field, value)
        payload = {"clave_idempotencia": str(uuid4()), "cliente": {"nombreCompleto": "María Pérez", "celular": "999888777", "correo": "owner@example.com", "tipoEntrega": "Recojo en clínica", "tipoComprobante": "Boleta", "dni": "12345678"}, "items": [{"producto_id": product, "cantidad": 2}], "metodo_pago": "yape", "numero_operacion": "WEB-MANUAL", "total_esperado": "40.00"}
        created = http.post("/pedidos-web", headers=headers[1], data={"datos": json.dumps(payload)}, files={"comprobante": ("pago.png", proof(), "image/png")})
        assert created.status_code == 201, created.text
        assert not messages(db, "pago_validado")
        response = http.post(f"/pedidos-web/{created.json()['id']}/revision", headers=headers[5], json={"accion": "APROBAR", "motivo": "Validado manualmente"})
        assert response.status_code == 200, response.text
    receipt, = messages(db, "pago_validado")
    assert receipt.clave.startswith("venta-pagada:")
    assert receipt.id in {row["id"] for row in http.get(BASE, headers=headers[5]).json()["mensajes"]}
    assert http.post(f"{BASE}/{receipt.id}/preparar", headers=headers[5], json={}).status_code == 200
    assert http.post(f"{BASE}/{receipt.id}/pdf", headers=headers[5], json={}).status_code == 200
    assert db.get(Producto, product).stock_actual == 8
