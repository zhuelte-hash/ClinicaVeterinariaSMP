"""Twilio Sandbox con HTTP/JWT, firmas reales del SDK y transporte aislado."""
import datetime as dt
from contextlib import contextmanager
from io import BytesIO
from urllib.parse import urlsplit

import httpx
import pytest
from dotenv import dotenv_values
from pypdf import PdfReader
from sqlalchemy import select
from twilio.request_validator import RequestValidator

from test_admin_clinical_flows import clinic
from test_priority_stories import operations, create_order, proof
from test_next_five_stories import start_attention
from test_priority_communications import prescribe, close
from test_fundamental_stories import prepare_attendance
from app.config import get_settings
from app.models.clinic import Cita, EstadoCita, Notificacion, OrdenCobro, Producto
from app.models.operations import AbonoOrden, MensajeEntrante, MensajeSalida, OrdenPendiente, PlantillaMensaje
from app.models.user import PermisoRol, TipoUsuario
from app.services import twilio_service
from app.services.access_service import now
from app.services.document_service import make_pdf
from app.services.messaging_service import MessagingService
from app.services.whatsapp_service import WhatsAppService
from scripts.configure_twilio import save_values

ACCOUNT = "AC" + "a" * 32
TOKEN = "private-twilio-test-token"
SENDER = "whatsapp:+14155238886"
ORIGIN = "https://clinic.example.test"
SID = "SM" + "b" * 32
MEDIA = "ME" + "c" * 32


@pytest.fixture
def twilio(operations, monkeypatch):
    settings = get_settings()
    for field, value in {"whatsapp_provider": "twilio", "twilio_account_sid": ACCOUNT, "twilio_auth_token": TOKEN,
                         "twilio_whatsapp_from": SENDER, "twilio_public_url": ORIGIN,
                         "whatsapp_phone_number_id": "", "whatsapp_access_token": ""}.items():
        monkeypatch.setattr(settings, field, value)
    clock = [now()]
    monkeypatch.setattr(twilio_service, "now", lambda: clock[0])
    monkeypatch.setattr("app.routers.messaging.now", lambda: clock[0])
    monkeypatch.setattr("app.services.messaging_service.now", lambda: clock[0])
    calls, state = [], {"code": None, "network": False}

    def post(url, **kwargs):
        assert url == f"{twilio_service.API}/Accounts/{ACCOUNT}/Messages.json"
        calls.append(kwargs)
        if state["network"]:
            raise httpx.ConnectError("Transporte controlado no disponible")
        if state["code"]:
            return httpx.Response(400, json={"code": state["code"], "message": "private-provider-description"}, request=httpx.Request("POST", url))
        return httpx.Response(201, json={"sid": f"SM{len(calls):032x}", "status": "queued"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(twilio_service.httpx, "post", post)
    return calls, state, clock


def signed_post(http, path, form, *, signature_url=None):
    signature = RequestValidator(TOKEN).compute_signature(signature_url or ORIGIN + path, form)
    return http.post(path, data=form, headers={"X-Twilio-Signature": signature})


def incoming(http, *, sid=SID, phone="51999888777", body="hola", **extra):
    form = {"AccountSid": ACCOUNT, "MessageSid": sid, "From": f"whatsapp:+{phone}",
            "To": SENDER, "Body": body, "NumMedia": "0", **extra}
    return signed_post(http, "/whatsapp/twilio/incoming", form)


def queued(db, key="twilio-test", **extra):
    item = MensajeSalida(clave=key, canal="whatsapp", evento="prueba_twilio", destinatario="51999888777", contenido="Mensaje de prueba", **extra)
    db.add(item); db.commit()
    return item


def window(db, clock, **extra):
    values = {"proveedor_id": f"twilio:{SID}", "telefono": "51999888777", "contenido": "hola", "fecha": clock[0], **extra}
    db.add(MensajeEntrante(**values)); db.commit()


def test_readiness_uses_twilio_and_does_not_expose_credentials(operations, twilio):
    http, _, headers, *_ = operations
    response = http.get("/admin/operaciones/comunicaciones/estado", headers=headers[4])
    data = response.json()
    assert data["proveedor_whatsapp"] == "twilio"
    assert data["whatsapp"]["configurado"] and data["webhook"]["configurado"]
    assert data["telefono_clinica_valido"]
    assert data["twilio"]["urls"]["entrada"] == ORIGIN + "/whatsapp/twilio/incoming"
    assert "24" in data["twilio"]["instrucciones"] and TOKEN not in response.text and ACCOUNT not in response.text
    assert response.headers["cache-control"] == "private, no-store"


@pytest.mark.parametrize("field", ["twilio_account_sid", "twilio_auth_token", "twilio_whatsapp_from", "twilio_public_url"])
def test_missing_configuration_waits_without_consuming_attempts(operations, twilio, monkeypatch, field):
    http, db, headers, *_ = operations
    monkeypatch.setattr(get_settings(), field, "")
    data = http.get("/admin/operaciones/comunicaciones/estado", headers=headers[4]).json()
    assert field.upper() in data["whatsapp"]["faltantes"]
    item = queued(db)
    MessagingService(db).deliver(item)
    assert item.estado == "pendiente_configuracion" and item.intentos == 0 and not twilio[0]


@pytest.mark.parametrize("url", ["http://public.example", "https://localhost", "https://private:password@example.com", "https://example.com/path", "https://example.com?token=private"])
def test_public_url_requires_https_origin(operations, twilio, monkeypatch, url):
    http, _, headers, *_ = operations
    monkeypatch.setattr(get_settings(), "twilio_public_url", url)
    data = http.get("/admin/operaciones/comunicaciones/estado", headers=headers[4]).json()
    assert not data["whatsapp"]["configurado"]
    assert any(value.startswith("TWILIO_PUBLIC_URL") for value in data["whatsapp"]["faltantes"])
    assert data["twilio"]["urls"] == {}


def test_incoming_opens_window_only_once_and_ignores_duplicate_age(operations, twilio):
    http, db, *_ = operations
    calls, _, clock = twilio
    assert incoming(http, FutureTwilioField="accepted").status_code == 200
    row = db.scalar(select(MensajeEntrante))
    assert row.telefono == "51999888777" and row.proveedor_id == f"twilio:{SID}"
    assert twilio_service.has_window(db, row.telefono)
    clock[0] += dt.timedelta(hours=25)
    assert incoming(http).status_code == 200
    assert len(db.scalars(select(MensajeEntrante)).all()) == 1
    assert not twilio_service.has_window(db, row.telefono) and not calls


@pytest.mark.parametrize("case", ["signature", "url", "account", "receiver", "sms", "sid"])
def test_incoming_rejects_invalid_signature_account_channel_and_receiver(operations, twilio, case):
    http, db, *_ = operations
    form = {"AccountSid": ACCOUNT, "MessageSid": SID, "From": "whatsapp:+51999888777", "To": SENDER, "Body": "hola", "NumMedia": "0"}
    if case == "account": form["AccountSid"] = "AC" + "d" * 32
    if case == "receiver": form["To"] = "whatsapp:+51900000000"
    if case == "sms": form["From"] = "+51999888777"
    if case == "sid": form["MessageSid"] = "not-a-message"
    if case == "signature":
        response = http.post("/whatsapp/twilio/incoming", data=form, headers={"X-Twilio-Signature": "invalid"})
    else:
        response = signed_post(http, "/whatsapp/twilio/incoming", form, signature_url="http://localhost/whatsapp/twilio/incoming" if case == "url" else None)
    assert response.status_code == (422 if case == "sid" else 403)
    assert not db.scalars(select(MensajeEntrante)).all() and not twilio[0]


def test_admin_test_is_queued_then_sent_with_callback_and_real_sid(operations, twilio):
    http, db, headers, *_ = operations
    path = "/admin/operaciones/comunicaciones/prueba-twilio"
    assert http.post(path, headers=headers[4], json={"telefono": "999888777"}).status_code == 409
    assert incoming(http).status_code == 200
    response = http.post(path, headers=headers[4], json={"telefono": "+51 999888777"})
    assert response.status_code == 201 and not twilio[0]
    item = db.get(MensajeSalida, response.json()["id"])
    MessagingService(db).process()
    assert item.estado == "enviado" and item.intentos == 1
    call, = twilio[0]
    assert call["auth"] == (ACCOUNT, TOKEN)
    assert call["data"]["From"] == SENDER and call["data"]["To"] == "whatsapp:+51999888777"
    assert "Prueba de conexión" in call["data"]["Body"]
    assert call["data"]["StatusCallback"] == f"{ORIGIN}/whatsapp/twilio/status?message_id={item.id}"
    assert item.proveedor_id.startswith("SM")
    MessagingService(db).deliver(item)
    assert len(twilio[0]) == 1


def test_admin_test_requires_write_permission_and_provider(operations, twilio, monkeypatch):
    http, db, headers, *_ = operations
    path, payload = "/admin/operaciones/comunicaciones/prueba-twilio", {"telefono": "999888777"}
    assert http.post(path, json=payload).status_code == 401
    assert http.post(path, headers=headers[1], json=payload).status_code == 403
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="usuarios", puede_ver=True, puede_editar=False)); db.commit()
    assert http.post(path, headers=headers[4], json=payload).status_code == 403
    db.query(PermisoRol).delete(); db.commit()
    monkeypatch.setattr(get_settings(), "whatsapp_provider", "meta")
    assert http.post(path, headers=headers[4], json=payload).status_code == 409
    assert not db.scalars(select(MensajeSalida)).all()


@pytest.mark.parametrize("case,allowed", [("absent", False), ("23h", True), ("24h", False), ("future", False), ("other_phone", False), ("meta", False)])
def test_window_limits_and_origin_are_respected(operations, twilio, case, allowed):
    _, db, *_ = operations
    calls, _, clock = twilio
    if case != "absent":
        changes = {"fecha": clock[0] + (dt.timedelta(minutes=1) if case == "future" else -dt.timedelta(hours=24 if case == "24h" else 23))}
        if case == "other_phone": changes["telefono"] = "51988777666"
        if case == "meta": changes["proveedor_id"] = "wamid.other-provider"
        window(db, clock, **changes)
    item = queued(db)
    MessagingService(db).deliver(item)
    assert bool(calls) == allowed
    assert item.intentos == (1 if allowed else 0)
    assert item.estado == ("enviado" if allowed else "pendiente_configuracion")


def test_rate_limit_defers_second_message_and_resumes_at_three_seconds(operations, twilio):
    _, db, *_ = operations
    calls, _, clock = twilio
    window(db, clock)
    first, second = queued(db, "first"), queued(db, "second")
    MessagingService(db).process()
    assert len(calls) == 1 and first.estado == "enviado" and second.estado == "pendiente"
    assert second.intentos == 0
    clock[0] += dt.timedelta(seconds=3)
    MessagingService(db).process()
    assert len(calls) == 2 and second.estado == "enviado"


@pytest.mark.parametrize("code,state", [(63015, "pendiente_configuracion"), (63016, "pendiente_configuracion"), (20003, "pendiente_configuracion"), (21608, "pendiente_configuracion"), (99999, "error")])
def test_provider_errors_preserve_queue_with_actionable_safe_message(operations, twilio, code, state):
    _, db, *_ = operations
    window(db, twilio[2]); twilio[1]["code"] = code
    item = queued(db)
    MessagingService(db).deliver(item)
    assert item.estado == state and item.intentos == 1 and str(code) in item.error
    assert "private-" not in item.error and item.proximo_intento is not None


def test_network_error_retries_only_when_due(operations, twilio):
    _, db, *_ = operations
    calls, state, clock = twilio
    window(db, clock); state["network"] = True
    item = queued(db)
    MessagingService(db).process()
    assert item.estado == "error" and item.intentos == 1
    MessagingService(db).process()
    assert len(calls) == 1
    state["network"] = False; clock[0] += dt.timedelta(minutes=3)
    MessagingService(db).process()
    assert item.estado == "enviado" and item.intentos == 2 and len(calls) == 2


def test_prescription_pdf_is_sent_without_caption_and_contains_order_code(operations, twilio):
    http, db, headers, _, product = operations
    window(db, twilio[2])
    process = start_attention(http, db, headers); prescribe(http, headers, process, product)
    assert close(http, headers, process).status_code == 200
    item = db.scalar(select(MensajeSalida).where(MensajeSalida.evento == "receta"))
    order = db.scalar(select(OrdenPendiente).where(OrdenPendiente.proceso_id == process))
    MessagingService(db).deliver(item); db.commit()
    data = twilio[0][0]["data"]
    assert "MediaUrl" in data and "Body" not in data
    url = urlsplit(data["MediaUrl"])
    response = http.get(url.path + "?" + url.query)
    assert response.status_code == 200 and response.content == item.documento
    assert order.codigo in "\n".join(page.extract_text() for page in PdfReader(BytesIO(response.content)).pages)
    assert response.headers["cache-control"] == "private, no-store"
    head = http.head(url.path + "?" + url.query)
    assert head.status_code == 200 and not head.content and int(head.headers["content-length"]) == len(item.documento)
    assert db.get(Producto, product).stock_actual == 10


@pytest.mark.parametrize("case", ["signature", "unicode_signature", "expired", "changed_pdf", "changed_recipient", "cancelled", "other_id"])
def test_document_links_are_bound_to_pdf_recipient_state_and_expiry(operations, twilio, case):
    http, db, *_ = operations
    item = queued(db, documento=make_pdf("Prueba", ["Documento ficticio"]))
    url = urlsplit(twilio_service.document_url(item))
    path = url.path + "?" + url.query
    if case == "signature": path += "x"
    if case == "unicode_signature": path = url.path + f"?expires={int(twilio[2][0].timestamp()) + 120}&signature=ñ"
    if case == "expired": twilio[2][0] += dt.timedelta(minutes=31)
    if case == "changed_pdf": item.documento += b"changed"
    if case == "changed_recipient": item.destinatario = "51900000000"
    if case == "cancelled": item.estado = "cancelado"
    if case == "other_id": path = path.replace(f"documents/{item.id}?", "documents/999?")
    db.commit()
    assert http.get(path).status_code == 404


def test_pdf_can_be_fetched_during_a_retry_before_twilio_returns(operations, twilio, monkeypatch):
    http, db, *_ = operations
    window(db, twilio[2])
    item = queued(db, documento=make_pdf("Prueba", ["Documento ficticio"]), estado="error")
    original = twilio_service.httpx.post

    def post(url, **kwargs):
        media = urlsplit(kwargs["data"]["MediaUrl"])
        response = http.get(media.path + "?" + media.query)
        assert response.status_code == 200 and response.content == item.documento
        return original(url, **kwargs)

    monkeypatch.setattr(twilio_service.httpx, "post", post)
    MessagingService(db).deliver(item)
    assert item.estado == "enviado"


def test_disabled_text_and_oversized_body_wait_without_provider_calls(operations, twilio):
    _, db, *_ = operations
    window(db, twilio[2])
    item = queued(db)
    item.contenido = "x" * 1601; db.commit()
    MessagingService(db).deliver(item)
    assert item.intentos == 0 and "1600" in item.error and not twilio[0]
    item.contenido = "Mensaje corto"
    item.evento = "cita_confirmada"
    db.add(PlantillaMensaje(evento="cita_confirmada", nombre_proveedor="", contenido="Texto", variables=[], activa=False)); db.commit()
    MessagingService(db).deliver(item)
    assert item.intentos == 0 and "Activa el texto" in item.error and not twilio[0]


def test_delivery_callbacks_are_signed_monotonic_and_ignore_previous_attempt(operations, twilio):
    http, db, *_ = operations
    window(db, twilio[2]); item = queued(db)
    MessagingService(db).deliver(item); db.commit()
    path = f"/whatsapp/twilio/status?message_id={item.id}"
    form = {"AccountSid": ACCOUNT, "MessageSid": item.proveedor_id, "From": SENDER, "To": "whatsapp:+51999888777", "MessageStatus": "read"}
    assert http.post(path, data=form, headers={"X-Twilio-Signature": "invalid"}).status_code == 403
    assert item.estado == "enviado"
    for state in ("read", "delivered", "failed", "sent"):
        assert signed_post(http, path, {**form, "MessageStatus": state, "NewField": "accepted"}).status_code == 204
        assert item.estado == "leido" and item.entregado_en is not None
    item.estado = "enviado"; item.proveedor_id = "SM" + "f" * 32; db.commit()
    assert signed_post(http, path, {**form, "MessageStatus": "failed"}).status_code == 204
    assert item.estado == "enviado"
    assert signed_post(http, path, {**form, "MessageSid": item.proveedor_id, "To": "whatsapp:+51900000000"}).status_code == 403


def test_attendance_and_payment_links_use_sandbox_receiver(operations, twilio):
    http, db, headers, _, product = operations
    prepare_attendance(db)
    response = http.get("/portal/citas/1/asistencia-whatsapp", headers=headers[1])
    assert response.status_code == 200 and urlsplit(response.json()["whatsapp_url"]).path == "/14155238886"
    command = response.json()["comando"]
    assert incoming(http, body=command).status_code == 200
    assert db.get(Cita, 1).asistencia_confirmada_en is not None
    assert incoming(http, sid="SM" + "d" * 32, body=command).status_code == 200
    assert len(db.scalars(select(Notificacion).where(Notificacion.tipo == "asistencia_confirmada")).all()) == 1
    order, _ = create_order(http, headers[5], product)
    response = http.post(f"/operaciones/ordenes/{order['id']}/preparar-whatsapp", headers=headers[1], json={"monto": "40.00", "medio": "yape"})
    assert response.status_code == 200 and urlsplit(response.json()["whatsapp_url"]).path == "/14155238886"


@pytest.fixture
def media(monkeypatch):
    state = {"content": proof(), "failure": False, "redirect": None, "declared": 100, "calls": []}

    @contextmanager
    def stream(method, url, **kwargs):
        state["calls"].append((url, kwargs))
        if state["failure"]: raise httpx.ReadError("Transporte controlado")
        if state["redirect"] and "api.twilio.com" in url:
            yield httpx.Response(302, headers={"Location": state["redirect"]}, request=httpx.Request(method, url))
        else:
            yield httpx.Response(200, headers={"Content-Length": str(state["declared"])}, content=state["content"], request=httpx.Request(method, url))
    monkeypatch.setattr(twilio_service.httpx, "stream", stream)
    return state


def incoming_proof(http, code, **extra):
    return incoming(http, body=f"{code} MONTO=40.00 MEDIO=yape OPERACION=OP-1", NumMedia="1", MediaContentType0="image/png",
                    MediaUrl0=f"{twilio_service.API}/Accounts/{ACCOUNT}/Messages/{SID}/Media/{MEDIA}", **extra)


def test_payment_proof_received_once_downloaded_privately_then_validated_by_cashier(operations, twilio, media):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    for _ in range(2): assert incoming_proof(http, order["codigo"]).status_code == 200
    payment, = db.scalars(select(AbonoOrden)).all()
    assert payment.estado == "enviado" and payment.canal == "whatsapp"
    assert len(media["calls"]) == 1 and media["calls"][0][1]["auth"] == (ACCOUNT, TOKEN)
    assert db.get(Producto, product).stock_actual == 10 and not db.scalars(select(OrdenCobro)).all()
    assert http.get(f"/operaciones/pagos/{payment.id}/comprobante", headers=headers[1]).content == proof()
    for _ in range(2): assert http.post(f"/operaciones/pagos/{payment.id}/validar", headers=headers[5]).status_code == 200
    assert db.get(Producto, product).stock_actual == 8


@pytest.mark.parametrize("case", ["declared_size", "actual_size", "corrupt", "redirect", "foreign_host"])
def test_invalid_proof_and_unsafe_media_do_not_create_payments(operations, twilio, media, case):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    if case == "declared_size": media["declared"] = 5 * 1024 * 1024 + 1
    if case == "actual_size": media["content"] = b"x" * (5 * 1024 * 1024 + 1)
    if case == "corrupt": media["content"] = b"not-a-png"
    if case == "redirect": media["redirect"] = "http://127.0.0.1/private"
    if case == "foreign_host":
        response = incoming(http, body=f"{order['codigo']} MONTO=40.00 MEDIO=yape", NumMedia="1", MediaContentType0="image/png", MediaUrl0="https://attacker.example/proof")
        assert not media["calls"]
    else:
        response = incoming_proof(http, order["codigo"])
    assert response.status_code == 200
    assert not db.scalars(select(AbonoOrden)).all() and db.get(Producto, product).stock_actual == 10


def test_cdn_redirect_drops_credentials_and_transient_failure_can_be_redelivered(operations, twilio, media):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    media["failure"] = True
    assert incoming_proof(http, order["codigo"]).status_code == 503
    assert not db.scalars(select(MensajeEntrante)).all()
    media["failure"] = False; media["redirect"] = "https://mms.twiliocdn.com/private-media?signature=example"
    assert incoming_proof(http, order["codigo"]).status_code == 200
    assert media["calls"][-1][1]["auth"] is None
    assert len(db.scalars(select(AbonoOrden)).all()) == 1


def test_no_show_uses_queue_and_never_calls_meta(operations, twilio):
    _, db, *_ = operations
    window(db, twilio[2]); appointment = db.get(Cita, 1)
    appointment.estado = EstadoCita.NO_ASISTIO
    service = WhatsAppService(db)
    item = service.send_once(appointment, "cita_no_asistio", "Inasistencia registrada")
    db.commit()
    assert service.send_once(appointment, "cita_no_asistio", "No duplicar").id == item.id
    assert not twilio[0]
    MessagingService(db).deliver(item)
    assert item.estado == "enviado" and len(twilio[0]) == 1


def test_configuration_assistant_preserves_other_environment_keys(tmp_path):
    path = tmp_path / ".env"
    path.write_text("# Configuración existente\nDATABASE_URL='postgresql://example/database'\nSECRET_KEY='keep-this-secret'\nSMTP_HOST=smtp.example.com\n", encoding="utf-8")
    save_values(path, {"WHATSAPP_PROVIDER": "twilio", "TWILIO_AUTH_TOKEN": "new-local-token"})
    values = dotenv_values(path)
    assert values["DATABASE_URL"] == "postgresql://example/database"
    assert values["SECRET_KEY"] == "keep-this-secret" and values["SMTP_HOST"] == "smtp.example.com"
    assert values["WHATSAPP_PROVIDER"] == "twilio" and values["TWILIO_AUTH_TOKEN"] == "new-local-token"
    assert "# Configuración existente" in path.read_text(encoding="utf-8")
