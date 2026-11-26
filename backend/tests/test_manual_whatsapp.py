"""WhatsApp manual: enlaces y PDF privados, sin llamadas externas ni pagos implícitos."""
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import select

from test_admin_clinical_flows import clinic
from test_priority_stories import operations, create_order
from test_next_five_stories import mailbox, start_attention
from test_priority_communications import prescribe, close
from test_fundamental_stories import prepare_attendance
from app.config import get_settings
from app.models.clinic import Cita, ConfiguracionClinica, EstadoCita, OrdenCobro, Producto
from app.models.operations import AbonoOrden, MensajeSalida, OrdenPendiente, PlantillaMensaje
from app.models.user import PermisoRol, TipoUsuario, Usuario
from app.services.access_service import AccessService
from app.services.messaging_service import MessagingService
from app.services.whatsapp_service import WhatsAppService


@pytest.fixture
def manual(operations, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "whatsapp_provider", "manual")
    # Aunque existan credenciales anteriores, el modo manual nunca usa su transporte.
    for field in ("whatsapp_phone_number_id", "whatsapp_access_token", "whatsapp_app_secret", "twilio_account_sid", "twilio_auth_token"):
        monkeypatch.setattr(settings, field, "unused-provider-value")
    monkeypatch.setattr("app.services.messaging_service.httpx.post", lambda *_a, **_kw: pytest.fail("El modo manual no debe llamar a Meta/Twilio"))


def event_message(db, event):
    return db.scalar(select(MensajeSalida).where(MensajeSalida.evento == event))


def order_message(operations):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    return order, event_message(db, "orden_creada")


def action(http, headers, item, name):
    return http.post(f"/admin/operaciones/mensajes/{item.id}/{name}", headers=headers)


def test_readiness_uses_clinic_phone_and_requires_no_provider_or_webhook(operations, manual):
    http, db, headers, *_ = operations
    response = http.get("/admin/operaciones/comunicaciones/estado", headers=headers[4])
    assert response.json()["proveedor_whatsapp"] == "manual"
    assert not response.json()["telefono_clinica_valido"]
    db.add(ConfiguracionClinica(nombre="Clínica", correo="clinic@example.com", telefono="+51 999 888 777")); db.commit()
    response = http.get("/admin/operaciones/comunicaciones/estado", headers=headers[4])
    data = response.json()
    assert data["whatsapp"]["configurado"] and not data["whatsapp"]["faltantes"]
    assert data["webhook"] == {"configurado": False, "faltantes": [], "requerido": False}
    assert data["twilio"] is None and data["manual"]["telefono_clinica"] == "51999888777"
    assert urlsplit(data["manual"]["prueba_url"]).path == "/51999888777"
    assert "unused-provider-value" not in response.text
    assert response.headers["cache-control"] == "private, no-store"


def test_prepared_order_encodes_exact_text_without_sending_or_affecting_money(operations, manual):
    http, db, headers, _, product = operations
    db.get(Usuario, 1).nombre = "María + José & familia"; db.commit()
    _, item = order_message(operations)
    assert item.estado == "pendiente_manual"
    response = action(http, headers[4], item, "preparar-manual")
    assert response.status_code == 200, response.text
    data = response.json()
    assert parse_qs(urlsplit(data["whatsapp_url"]).query)["text"] == [item.contenido]
    assert urlsplit(data["whatsapp_url"]).path == "/51999888777"
    assert "María + José & familia" in data["contenido"]
    assert response.headers["cache-control"] == "private, no-store"
    assert item.intentos == 0 and item.proveedor_id is None and item.enviado_en is None and item.entregado_en is None
    assert db.get(Producto, product).stock_actual == 10
    assert not db.scalars(select(OrdenCobro)).all() and not db.scalars(select(AbonoOrden)).all()


@pytest.mark.parametrize("previous", ["pendiente", "pendiente_configuracion", "error"])
def test_worker_converts_previous_pending_notices_without_provider_attempts(operations, manual, previous):
    _, db, *_ = operations
    _, item = order_message(operations)
    item.estado = previous; db.commit()
    MessagingService(db).process()
    assert item.estado == "pendiente_manual" and item.intentos == 0
    assert item.proveedor_id is None and item.enviado_en is None
    assert MessagingService(db).process() == 0


def test_operator_can_finish_idempotently_without_claiming_delivery(operations, manual):
    http, db, headers, _, product = operations
    _, item = order_message(operations)
    for _ in range(2):
        response = action(http, headers[4], item, "gestionar-manual")
        assert response.status_code == 200 and response.json()["estado"] == "gestionado_manual"
    MessagingService(db).deliver(item)
    assert item.estado == "gestionado_manual" and item.intentos == 0
    assert item.enviado_en is None and item.entregado_en is None and item.proveedor_id is None
    assert action(http, headers[4], item, "preparar-manual").status_code == 409
    assert db.get(Producto, product).stock_actual == 10 and not db.scalars(select(OrdenCobro)).all()


@pytest.mark.parametrize("state", ["enviado", "entregado", "leido", "cancelado"])
def test_finished_or_provider_messages_cannot_be_prepared_or_marked_again(operations, manual, state):
    http, db, headers, *_ = operations
    _, item = order_message(operations)
    item.estado = state; db.commit()
    assert action(http, headers[4], item, "preparar-manual").status_code == 409
    assert action(http, headers[4], item, "gestionar-manual").status_code == 409
    assert item.estado == state


@pytest.mark.parametrize("state", ["pagada", "anulada", "vencida"])
def test_obsolete_order_is_cancelled_before_opening_whatsapp(operations, manual, state):
    http, db, headers, *_ = operations
    order, item = order_message(operations)
    db.get(OrdenPendiente, order["id"]).estado = state; db.commit()
    assert action(http, headers[4], item, "preparar-manual").status_code == 409
    assert item.estado == "cancelado" and item.intentos == 0


def test_preparation_uses_corrected_contact_and_rejects_inactive_customer(operations, manual):
    http, db, headers, *_ = operations
    _, item = order_message(operations)
    owner = db.get(Usuario, 1)
    owner.cliente.telefono = "988777666"; db.commit()
    response = action(http, headers[4], item, "preparar-manual")
    assert response.json()["destinatario"] == "51988777666"
    owner.activo = False; db.commit()
    assert action(http, headers[4], item, "preparar-manual").status_code == 409
    assert item.estado == "cancelado"


@pytest.mark.parametrize("phone", ["123", "00000000000", "+0 999888777"])
def test_invalid_phone_never_prepares_a_link(operations, manual, phone):
    http, db, headers, *_ = operations
    _, item = order_message(operations)
    db.get(Usuario, 1).cliente.telefono = phone; db.commit()
    assert action(http, headers[4], item, "preparar-manual").status_code == 409
    assert item.intentos == 0


def test_private_prescription_is_downloaded_only_by_authorized_operator(operations, manual):
    http, db, headers, _, product = operations
    process = start_attention(http, db, headers); prescribe(http, headers, process, product)
    assert close(http, headers, process).status_code == 200
    item = event_message(db, "receta")
    response = action(http, headers[4], item, "preparar-manual")
    assert response.status_code == 200 and response.json()["documento_disponible"]
    pdf = action(http, headers[4], item, "pdf-manual")
    assert pdf.status_code == 200 and pdf.content == item.documento and pdf.content.startswith(b"%PDF")
    assert pdf.headers["cache-control"] == "private, no-store"
    status = http.get("/portal/citas/1/comunicaciones", headers=headers[1])
    assert status.status_code == 200 and status.json()["mensajes"][0]["estado"] == "pendiente_manual"
    assert not {"contenido", "parametros", "destinatario"} & status.json()["mensajes"][0].keys()
    assert action(http, headers[1], item, "pdf-manual").status_code == 403
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="historias_clinicas", puede_ver=False)); db.commit()
    assert action(http, headers[4], item, "pdf-manual").status_code == 403
    assert item.estado == "pendiente_manual" and item.intentos == 0
    assert db.get(Producto, product).stock_actual == 10


@pytest.mark.parametrize("name", ["preparar-manual", "pdf-manual", "gestionar-manual"])
def test_all_manual_actions_require_login_role_and_users_edit_permission(operations, manual, name):
    http, db, headers, *_ = operations
    _, item = order_message(operations)
    assert action(http, {}, item, name).status_code == 401
    assert action(http, headers[1], item, name).status_code == 403
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="usuarios", puede_ver=True, puede_editar=False)); db.commit()
    assert action(http, headers[4], item, name).status_code == 403
    assert item.estado == "pendiente_manual"


def test_manual_orders_also_require_sales_view_permission(operations, manual):
    http, db, headers, *_ = operations
    _, item = order_message(operations)
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="ventas", puede_ver=False)); db.commit()
    assert action(http, headers[4], item, "preparar-manual").status_code == 403


def test_manual_actions_do_not_process_email_or_run_in_other_modes(operations, manual, monkeypatch):
    http, db, headers, *_ = operations
    email = MensajeSalida(clave="manual-email", canal="correo", evento="recuperar", destinatario="private@example.com", contenido="private-token")
    db.add(email); db.commit()
    assert action(http, headers[4], email, "preparar-manual").status_code == 404
    assert email.estado == "pendiente" and email.intentos == 0
    _, item = order_message(operations)
    monkeypatch.setattr(get_settings(), "whatsapp_provider", "twilio")
    assert action(http, headers[4], item, "preparar-manual").status_code == 409


def test_disabled_message_stays_pending_configuration(operations, manual):
    http, db, headers, *_ = operations
    _, item = order_message(operations)
    db.add(PlantillaMensaje(evento="orden_creada", contenido="Texto", variables=["nombre", "codigo", "total"], activa=False)); db.commit()
    assert action(http, headers[4], item, "preparar-manual").status_code == 409
    assert item.estado == "pendiente_configuracion" and item.intentos == 0


def test_client_links_use_clinic_phone_and_explain_manual_handling(operations, manual):
    http, db, headers, _, product = operations
    prepare_attendance(db)
    attendance = http.get("/portal/citas/1/asistencia-whatsapp", headers=headers[1])
    assert attendance.status_code == 200 and attendance.json()["modo"] == "manual"
    assert "Hola, confirmo" in attendance.json()["comando"] and "automáticamente" in attendance.json()["instrucciones"]
    assert urlsplit(attendance.json()["whatsapp_url"]).path == "/51965939522"
    assert db.get(Cita, 1).asistencia_confirmada_en is None
    order, _ = create_order(http, headers[5], product)
    response = http.post(f"/operaciones/ordenes/{order['id']}/preparar-whatsapp", headers=headers[1], json={"monto": "40.00", "medio": "yape"})
    assert response.status_code == 200 and "registrar manualmente" in response.json()["instrucciones"]
    assert not db.scalars(select(AbonoOrden)).all()


def test_manual_mode_disables_automatic_receivers(operations, manual):
    http, *_ = operations
    assert http.post("/whatsapp/webhook", json={}).status_code == 503
    assert http.post("/whatsapp/twilio/incoming", data={"Body": "hola"}).status_code == 503


def test_no_show_is_queued_without_using_legacy_meta_transport(operations, manual):
    _, db, *_ = operations
    appointment = db.get(Cita, 1); appointment.estado = EstadoCita.NO_ASISTIO
    service = WhatsAppService(db)
    item = service.send_once(appointment, "cita_no_asistio", "Cita no atendida")
    db.commit()
    assert item.estado == "pendiente_manual"
    assert service.send_once(appointment, "cita_no_asistio", "No duplicar").id == item.id
    MessagingService(db).deliver(item)
    assert item.estado == "pendiente_manual" and item.intentos == 0


def test_smtp_still_sends_account_email_in_manual_whatsapp_mode(operations, manual, mailbox):
    _, db, *_ = operations
    message_id = AccessService(db).issue(db.get(Usuario, 1), "recuperar")
    item = db.get(MensajeSalida, message_id)
    MessagingService(db).deliver(item); db.commit()
    assert mailbox[0].get(timeout=5)["To"] == "owner@example.com"
    assert item.estado == "enviado" and item.proveedor_id.startswith("smtp:")
