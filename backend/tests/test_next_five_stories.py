"""HU-002/004/036/061/120: HTTP, JWT y persistencia aislada; SMTP local real."""
import datetime as dt
import re
from email import message_from_bytes, policy
from queue import Empty, Queue
from socketserver import StreamRequestHandler, ThreadingTCPServer
from threading import Thread
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from test_priority_stories import operations
from test_admin_clinical_flows import clinic
from app.config import get_settings
from app.models.clinic import Cita, EstadoCita, Mascota, Notificacion, Producto
from app.models.operations import CompraProveedor, DesafioCuenta, Egreso, MensajeSalida, MovimientoInventario, Sucursal
from app.models.user import Cliente, PermisoRol, TipoUsuario, Usuario
from app.services import access_service, messaging_service
from app.services.access_service import now
from app.services.messaging_service import MessagingService
from app.services.user_service import UserService


@pytest.fixture
def mailbox(operations, monkeypatch):
    """Recibe el correo por TCP/SMTP, sin sustituir smtplib ni enviar fuera del equipo."""
    messages = Queue()

    class SMTP(StreamRequestHandler):
        def reply(self, line):
            self.wfile.write(line + b"\r\n")
            self.wfile.flush()

        def handle(self):
            self.reply(b"220 localhost test SMTP")
            while line := self.rfile.readline():
                command = line.split(b" ", 1)[0].strip().upper()
                if command == b"DATA":
                    self.reply(b"354 End with a dot")
                    data = []
                    while (line := self.rfile.readline()) not in (b".\r\n", b""):
                        data.append(line[1:] if line.startswith(b"..") else line)
                    messages.put(message_from_bytes(b"".join(data), policy=policy.default))
                    self.reply(b"250 Queued")
                elif command == b"QUIT":
                    self.reply(b"221 Bye")
                    return
                elif command == b"MAIL" and self.server.reject:
                    self.reply(b"550 Sender rejected for test")
                else:
                    self.reply(b"250 OK")

    server = ThreadingTCPServer(("127.0.0.1", 0), SMTP)
    server.daemon_threads = True
    server.reject = False
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    settings = get_settings()
    for field, value in {"smtp_host": "127.0.0.1", "smtp_port": server.server_address[1], "smtp_ssl": False,
                         "smtp_starttls": False, "smtp_username": "", "smtp_password": "", "mail_from": "clinic@example.com",
                         "frontend_url": "http://localhost:4200", "whatsapp_access_token": ""}.items():
        monkeypatch.setattr(settings, field, value)
    # Las tareas posteriores a la respuesta también usan la misma SQLite aislada.
    monkeypatch.setattr(messaging_service, "SessionLocal", sessionmaker(bind=operations[1].get_bind()))
    try:
        yield messages, server
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def register(http, mailbox, email="new+code@example.com"):
    response = http.post("/auth/register", json={"nombre": "  Nueva   Cliente  ", "correo": email, "password": "Inicial123", "telefono": "999888777"})
    assert response.status_code == 201, response.text
    message = mailbox[0].get(timeout=5)
    return response.json(), re.search(r"\b\d{6}\b", message.get_content())[0], message


def recovery(http, mailbox, email):
    response = http.post("/auth/recuperar-clave", json={"correo": email})
    assert response.status_code == 202, response.text
    message = mailbox[0].get(timeout=5)
    url = re.search(r"http://\S+", message.get_content())[0].rstrip(".")
    return parse_qs(urlsplit(url).query)


def start_attention(http, db, headers):
    db.get(Cita, 1).estado = EstadoCita.CONFIRMADA
    db.commit()
    response = http.post("/portal/veterinario/solicitudes/1/atencion/iniciar", headers=headers[2])
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_cancellation_records_reason_frees_slot_and_does_not_repeat_messages(operations):
    http, db, headers, start, _ = operations
    db.get(Cita, 1).estado = EstadoCita.CONFIRMADA
    db.commit()
    params = {"servicio_id": 1, "fecha": start.astimezone(dt.timezone(dt.timedelta(hours=-5))).date().isoformat()}

    def slot_available():
        return any(row["veterinario_id"] == 2 and dt.datetime.fromisoformat(row["fecha_hora"]) == start
                   for row in http.get("/portal/disponibilidad", params=params).json())

    assert not slot_available()
    response = http.patch("/portal/citas/1/cancelar", headers=headers[1], json={"motivo": "  Viaje familiar  "})
    assert response.status_code == 200, response.text
    assert response.json()["nota_coordinacion"] == "Viaje familiar"
    assert response.json()["estado"] == "cancelada" and slot_available()
    assert db.get(Cita, 1).estado_actualizado_por == 1
    assert db.scalar(select(Notificacion).where(Notificacion.tipo == "cita_cancelada", Notificacion.usuario_id == 2))
    messages = db.scalars(select(MensajeSalida).where(MensajeSalida.evento == "cita_cancelada")).all()
    assert len(messages) == 1 and "Viaje familiar" in messages[0].contenido
    assert messages[0].destinatario == "51999888777"
    assert http.patch("/portal/citas/1/cancelar", headers=headers[1], json={"motivo": "Reintento de cancelación"}).status_code == 200
    assert len(db.scalars(select(MensajeSalida).where(MensajeSalida.evento == "cita_cancelada")).all()) == 1
    assert db.get(Cita, 1).nota_coordinacion == "Viaje familiar"


@pytest.mark.parametrize("kind", ["late", "no_show", "attended", "started", "other_owner", "permission"])
def test_cancellation_enforces_time_clinical_state_owner_and_permission(operations, kind):
    http, db, headers, _start, _ = operations
    appointment = db.get(Cita, 1)
    if kind == "late":
        appointment.fecha_hora_programada = now() + dt.timedelta(hours=1)
    elif kind in {"no_show", "attended"}:
        appointment.estado = EstadoCita.NO_ASISTIO if kind == "no_show" else EstadoCita.ATENDIDA
    elif kind == "other_owner":
        db.add(Usuario(id=6, nombre="Otro dueño", correo="other-owner@example.com", tipo=TipoUsuario.CLIENTE, contrasena="hash"))
        db.flush(); db.add(Cliente(usuario_id=6)); db.flush()
        db.get(Mascota, 1).cliente_id = 6
    elif kind == "permission":
        db.add(PermisoRol(rol=TipoUsuario.CLIENTE, modulo="citas", puede_ver=True, puede_editar=False))
    db.commit()
    if kind == "started":
        start_attention(http, db, headers)
    response = http.patch("/portal/citas/1/cancelar", headers=headers[1], json={"motivo": "Cambio de planes"})
    assert response.status_code == (404 if kind == "other_owner" else 403 if kind == "permission" else 409), response.text
    assert db.get(Cita, 1).estado != EstadoCita.CANCELADA


@pytest.mark.parametrize("payload", [{}, {"motivo": "   "}])
def test_cancellation_requires_a_real_reason(operations, payload):
    http, db, headers, *_ = operations
    assert http.patch("/portal/citas/1/cancelar", headers=headers[1], json=payload).status_code == 422
    assert db.get(Cita, 1).estado == EstadoCita.PENDIENTE_CONTACTO


def test_cancellation_uses_the_booking_contact_when_profile_has_no_phone(operations):
    http, db, headers, *_ = operations
    db.get(Usuario, 1).cliente.telefono = None
    db.get(Cita, 1).telefono_contacto = "987 654 321"
    db.commit()
    assert http.patch("/portal/citas/1/cancelar", headers=headers[1], json={"motivo": "Cambio de horario"}).status_code == 200
    message = db.scalar(select(MensajeSalida).where(MensajeSalida.evento == "cita_cancelada"))
    assert message.destinatario == "51987654321"


def test_private_notes_persist_and_stay_out_of_customer_history_and_audit(operations):
    http, db, headers, *_ = operations
    process = start_attention(http, db, headers)
    url = f"/portal/veterinario/atenciones/{process}/notas-privadas"
    secret = "Observación interna reservada del profesional"
    assert http.put(url, headers=headers[2], json={"notas": secret}).status_code == 200
    saved = http.get(url, headers=headers[2])
    assert saved.json() == {"notas": secret}
    assert saved.headers["cache-control"] == "private, no-store"
    for role in (1, 3, 4, 5):
        assert http.get(url, headers=headers[role]).status_code in {403, 404}
        assert http.put(url, headers=headers[role], json={"notas": "Cambio ajeno"}).status_code in {403, 404}
    for path, role in [("/portal/mascotas/1/historial", 1), ("/admin/historial-clinico", 4), ("/admin/operaciones/auditoria", 4)]:
        result = http.get(path, headers=headers[role])
        assert result.status_code == 200, result.text
        assert secret not in result.text and '"notas_privadas"' not in result.text
    assert http.get(url, headers=headers[2]).json()["notas"] == secret


def test_private_notes_read_only_size_and_clear(operations):
    http, db, headers, *_ = operations
    process = start_attention(http, db, headers)
    url = f"/portal/veterinario/atenciones/{process}/notas-privadas"
    assert http.put(url, headers=headers[2], json={"notas": "x" * 10001}).status_code == 422
    assert http.put(url, headers=headers[2], json={"notas": "Nota anterior"}).status_code == 200
    assert http.put(url, headers=headers[2], json={"notas": ""}).json() == {"notas": ""}
    db.add(PermisoRol(rol=TipoUsuario.VETERINARIO, modulo="historias_clinicas", puede_ver=True, puede_editar=False)); db.commit()
    assert http.get(url, headers=headers[2]).status_code == 200
    assert http.put(url, headers=headers[2], json={"notas": "No autorizado"}).status_code == 403


def test_email_registration_delivers_smtp_code_and_requires_verification(operations, mailbox):
    http, db, *_ = operations
    data, code, message = register(http, mailbox, "New+Code@example.com")
    assert data["verification_required"] and data["access_token"] == ""
    assert data["user"]["nombre"] == "Nueva Cliente" and code not in str(data)
    assert message["To"] == "new+code@example.com"
    credentials = {"identifier": "new+code@example.com", "password": "Inicial123"}
    assert http.post("/auth/login", json=credentials).status_code == 403
    wrong = "000000" if code != "000000" else "111111"
    assert http.post("/auth/verificar-correo", json={"correo": credentials["identifier"], "codigo": wrong}).status_code == 400
    verified = http.post("/auth/verificar-correo", json={"correo": credentials["identifier"].upper(), "codigo": code})
    assert verified.status_code == 200 and verified.json()["access_token"]
    assert http.post("/auth/login", json=credentials).status_code == 200
    assert http.post("/auth/verificar-correo", json={"correo": credentials["identifier"], "codigo": code}).status_code == 400
    challenge = db.scalar(select(DesafioCuenta).where(DesafioCuenta.usuario_id == data["user"]["id"]))
    assert challenge.secreto_hash != code and challenge.usado_en is not None


def test_email_resend_throttles_and_invalidates_previous_code(operations, mailbox, monkeypatch):
    http, db, *_ = operations
    codes = iter((123456, 654321))
    monkeypatch.setattr(access_service.secrets, "randbelow", lambda maximum: next(codes))
    data, old_code, _ = register(http, mailbox)
    request = {"correo": data["user"]["correo"]}
    throttled = http.post("/auth/reenviar-verificacion", json=request)
    assert throttled.status_code == 429 and int(throttled.headers["retry-after"]) > 0
    challenge = db.scalar(select(DesafioCuenta).where(DesafioCuenta.usuario_id == data["user"]["id"]))
    challenge.creado_en = now() - dt.timedelta(seconds=61)
    message = db.scalar(select(MensajeSalida).where(MensajeSalida.entidad_id == challenge.id, MensajeSalida.canal == "correo"))
    message.estado = "error"
    db.commit()
    assert http.post("/auth/reenviar-verificacion", json=request).status_code == 202
    new_code = re.search(r"\b\d{6}\b", mailbox[0].get(timeout=5).get_content())[0]
    db.expire_all()
    assert db.get(MensajeSalida, message.id).estado == "cancelado"
    assert http.post("/auth/verificar-correo", json={**request, "codigo": old_code}).status_code == 400
    assert http.post("/auth/verificar-correo", json={**request, "codigo": new_code}).status_code == 200


@pytest.mark.parametrize("kind", ["expired", "attempts"])
def test_email_verification_rejects_expiry_and_five_wrong_codes(operations, mailbox, kind):
    http, db, *_ = operations
    data, code, _ = register(http, mailbox)
    challenge = db.scalar(select(DesafioCuenta).where(DesafioCuenta.usuario_id == data["user"]["id"]))
    if kind == "expired":
        challenge.expira_en = now() - dt.timedelta(seconds=1); db.commit()
    else:
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(5):
            assert http.post("/auth/verificar-correo", json={"correo": data["user"]["correo"], "codigo": wrong}).status_code == 400
    assert http.post("/auth/verificar-correo", json={"correo": data["user"]["correo"], "codigo": code}).status_code == 400
    assert not db.get(Usuario, data["user"]["id"]).correo_verificado


def test_password_reset_smtp_link_preserves_plus_email_revokes_sessions_and_is_single_use(operations, mailbox):
    http, db, headers, *_ = operations
    user = db.get(Usuario, 1)
    user.correo = "owner+recovery@example.com"
    user.contrasena = UserService(db)._hash_password("Anterior123")
    db.commit()
    query = recovery(http, mailbox, user.correo.upper())
    assert query["correo"] == [user.correo]
    payload = {"token": query["token"][0], "password": "Actualizada123"}
    response = http.post("/auth/restablecer-clave", params={"correo": user.correo}, json=payload)
    assert response.status_code == 204, response.text
    assert http.get("/auth/me", headers=headers[1]).status_code == 401
    assert http.post("/auth/login", json={"identifier": user.correo, "password": "Anterior123"}).status_code == 401
    assert http.post("/auth/login", json={"identifier": user.correo, "password": "Actualizada123"}).status_code == 200
    assert http.post("/auth/restablecer-clave", params={"correo": user.correo}, json=payload).status_code == 400


@pytest.mark.parametrize("kind", ["expired", "replaced", "inactive"])
def test_password_reset_rejects_expired_replaced_or_deactivated_account_links(operations, mailbox, kind):
    http, db, *_ = operations
    user = db.get(Usuario, 1)
    original = user.contrasena
    query = recovery(http, mailbox, user.correo)
    challenge = db.scalar(select(DesafioCuenta).where(DesafioCuenta.usuario_id == user.id))
    if kind == "expired":
        challenge.expira_en = now() - dt.timedelta(seconds=1)
    elif kind == "inactive":
        user.activo = False
    else:
        challenge.creado_en = now() - dt.timedelta(seconds=61)
    db.commit()
    if kind == "replaced":
        recovery(http, mailbox, user.correo)
    response = http.post("/auth/restablecer-clave", params={"correo": user.correo}, json={"token": query["token"][0], "password": "Actualizada123"})
    assert response.status_code == 400, response.text
    assert db.get(Usuario, 1).contrasena == original


def test_unknown_recovery_has_generic_response_and_does_not_send_mail(operations, mailbox):
    http, *_ = operations
    response = http.post("/auth/recuperar-clave", json={"correo": "unknown@example.com"})
    assert response.status_code == 202 and "token" not in response.text
    with pytest.raises(Empty):
        mailbox[0].get_nowait()


def test_missing_smtp_reports_unavailability_without_creating_a_blocked_account(operations, monkeypatch):
    http, db, *_ = operations
    monkeypatch.setattr(get_settings(), "smtp_host", "")
    response = http.post("/auth/register", json={"nombre": "Nueva Cliente", "correo": "unconfigured@example.com", "password": "Inicial123"})
    assert response.status_code == 503 and "configurado" in response.json()["detail"]
    assert UserService(db).get_by_email("unconfigured@example.com") is None
    for path in ("/auth/recuperar-clave", "/auth/reenviar-verificacion"):
        assert http.post(path, json={"correo": "unknown@example.com"}).status_code == 503


def test_failed_smtp_delivery_is_retried_and_expired_codes_are_not_delivered(operations, mailbox):
    http, db, *_ = operations
    mailbox[1].reject = True
    response = http.post("/auth/recuperar-clave", json={"correo": "owner@example.com"})
    assert response.status_code == 202
    db.expire_all()
    outgoing = db.scalar(select(MensajeSalida).where(MensajeSalida.canal == "correo"))
    assert outgoing.estado == "error" and outgoing.intentos == 1
    outgoing.proximo_intento = now() - dt.timedelta(seconds=1); db.commit()
    mailbox[1].reject = False
    MessagingService(db).process()
    assert outgoing.estado == "enviado" and mailbox[0].get(timeout=5)
    challenge = db.get(DesafioCuenta, outgoing.entidad_id)
    challenge.expira_en = now() - dt.timedelta(seconds=1)
    outgoing.estado = "pendiente"; outgoing.proximo_intento = None; db.commit()
    MessagingService(db).process()
    assert outgoing.estado == "cancelado" and outgoing.contenido == ""
    with pytest.raises(Empty):
        mailbox[0].get_nowait()


def test_receiving_tracks_supplier_actor_cost_lots_and_normalized_duplicate_document(operations):
    http, db, headers, _start, product = operations
    future = (dt.date.today() + dt.timedelta(days=60)).isoformat()
    payload = {"proveedor_id": 1, "documento": "  fac-001  ", "detalles": [
        {"producto_id": product, "cantidad": 2, "costo_unitario": 3, "lote": "A-001", "vencimiento": future},
        {"producto_id": product, "cantidad": 3, "costo_unitario": 4, "lote": "A-002", "vencimiento": future},
    ]}
    response = http.post("/admin/operaciones/compras", headers=headers[4], json=payload)
    assert response.status_code == 201, response.text
    receipt = response.json()
    assert receipt["documento"] == "FAC-001" and receipt["proveedor_nombre"] == "Proveedor"
    assert receipt["usuario_nombre"] == "Administración" and float(receipt["total"]) == 18
    assert db.get(Producto, product).stock_actual == 15
    assert float(db.get(Producto, product).costo_unitario) == 1.2
    assert db.scalar(select(Egreso).where(Egreso.compra_id == receipt["id"])).monto == 18
    history = http.get("/admin/operaciones/compras", headers=headers[4]).json()
    assert history == [receipt]
    assert http.post("/admin/operaciones/compras", headers=headers[4], json={**payload, "documento": "FaC-001"}).status_code == 409
    assert db.get(Producto, product).stock_actual == 15
    db.add(Sucursal(id=2, nombre="Otra sede")); db.commit()
    assert http.get("/admin/operaciones/compras", headers={**headers[4], "X-Sucursal-ID": "2"}).json() == []
    assert len(db.scalars(select(MovimientoInventario).where(MovimientoInventario.tipo == "compra")).all()) == 2


def test_receiving_read_only_and_invalid_line_roll_back_everything(operations):
    http, db, headers, _start, product = operations
    payload = {"proveedor_id": 1, "documento": "ROLLBACK-001", "detalles": [
        {"producto_id": product, "cantidad": 2, "costo_unitario": 3, "lote": "VALID"},
        {"producto_id": product, "cantidad": 3, "costo_unitario": 4, "lote": "EXPIRED", "vencimiento": "2000-01-01"},
    ]}
    assert http.post("/admin/operaciones/compras", headers=headers[4], json=payload).status_code == 422
    assert db.get(Producto, product).stock_actual == 10 and db.get(Producto, product).costo_unitario == 0
    assert not db.scalars(select(CompraProveedor)).all() and not db.scalars(select(Egreso)).all()
    assert not db.scalars(select(MovimientoInventario).where(MovimientoInventario.tipo == "compra")).all()
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="inventario", puede_ver=True, puede_crear=False)); db.commit()
    assert http.get("/admin/operaciones/compras", headers=headers[4]).status_code == 200
    assert http.post("/admin/operaciones/compras", headers=headers[4], json=payload).status_code == 403
    assert http.get("/admin/operaciones/compras", headers=headers[1]).status_code == 403
