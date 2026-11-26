"""HU-067/098/104/105/106: webhook firmado, archivos limitados y avisos controlados."""
import datetime as dt
from contextlib import contextmanager
import hashlib
import hmac
import json
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from sqlalchemy import select

from test_admin_clinical_flows import clinic
from test_priority_stories import operations, create_order, proof
from app.config import get_settings
from app.models.clinic import Cita, ConfiguracionClinica, OrdenCobro, Producto
from app.models.operations import AbonoOrden, MensajeEntrante, MensajeSalida, OrdenPendiente, PlantillaMensaje
from app.models.user import Cliente, PermisoRol, TipoUsuario, Usuario
from app.routers import messaging
from app.services.messaging_service import EVENTS, MessagingService


@pytest.fixture
def media_provider(operations, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "whatsapp_app_secret", "five-stories-test-secret")
    monkeypatch.setattr(settings, "whatsapp_access_token", "test-token")
    state = {"content": proof(), "mime": "image/png", "size": 100, "failure": False, "stream_failure": False, "downloads": 0}

    def metadata(url, **kwargs):
        if state["failure"]:
            raise httpx.ConnectError("Proveedor no disponible")
        return httpx.Response(200, request=httpx.Request("GET", url), json={"url": "https://media.example.test/proof", "file_size": state["size"], "mime_type": state["mime"]})

    @contextmanager
    def download(method, url, **kwargs):
        state["downloads"] += 1
        if state["stream_failure"]:
            raise httpx.ReadError("Descarga interrumpida")
        yield httpx.Response(200, request=httpx.Request(method, url), content=state["content"])

    monkeypatch.setattr(messaging.httpx, "get", metadata)
    monkeypatch.setattr(messaging.httpx, "stream", download)
    return state


def incoming(http, code, *, message_id="wamid.proof", phone="51999888777", caption=None):
    payload = {"entry": [{"changes": [{"value": {"messages": [{"id": message_id, "from": phone, "type": "image", "image": {"id": "media-proof", "caption": caption or f"{code} MONTO=40.00 MEDIO=yape OPERACION=OP-1"}}]}}]}]}
    raw = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(b"five-stories-test-secret", raw, hashlib.sha256).hexdigest()
    return http.post("/whatsapp/webhook", content=raw, headers={"Content-Type": "application/json", "X-Hub-Signature-256": signature})


def test_client_prepares_caption_without_creating_a_payment(operations):
    http, db, headers, _, product = operations
    db.add(ConfiguracionClinica(nombre="SMP", correo="clinic@example.com", telefono="965939522")); db.commit()
    order, _ = create_order(http, headers[5], product)
    response = http.post(f"/operaciones/ordenes/{order['id']}/preparar-whatsapp", headers=headers[1], json={"monto": "40.00", "medio": "yape", "codigo_operacion": "OP-1"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["leyenda"] == f"{order['codigo']} MONTO=40.00 MEDIO=yape OPERACION=OP-1"
    assert parse_qs(urlsplit(data["whatsapp_url"]).query)["text"] == [data["leyenda"]]
    assert response.headers["cache-control"] == "private, no-store"
    assert not db.scalars(select(AbonoOrden)).all()
    assert db.get(Producto, product).stock_actual == 10


@pytest.mark.parametrize("case,expected", [("owner", 404), ("amount", 409), ("phone", 409), ("closed", 409), ("permission", 403), ("staff", 403)])
def test_preparation_checks_owner_balance_phone_permission_and_order_state(operations, case, expected):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    if case == "owner":
        db.add(Usuario(id=6, nombre="Otro cliente", correo="other-wa@example.com", tipo=TipoUsuario.CLIENTE, contrasena="hash")); db.flush(); db.add(Cliente(usuario_id=6)); db.flush()
        db.get(OrdenPendiente, order["id"]).cliente_id = 6
    elif case == "phone":
        db.get(Usuario, 1).cliente.telefono = None
    elif case == "closed":
        db.get(OrdenPendiente, order["id"]).estado = "anulada"
    elif case == "permission":
        db.add(PermisoRol(rol=TipoUsuario.CLIENTE, modulo="ventas", puede_ver=True, puede_crear=False))
    db.commit()
    response = http.post(f"/operaciones/ordenes/{order['id']}/preparar-whatsapp", headers=headers[5 if case == "staff" else 1], json={"monto": "41.00" if case == "amount" else "40.00", "medio": "yape"})
    assert response.status_code == expected, response.text


def test_signed_proof_received_once_then_cashier_validates_atomically(operations, media_provider):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    for _ in range(2):
        response = incoming(http, order["codigo"])
        assert response.status_code == 200, response.text
    payments = db.scalars(select(AbonoOrden)).all()
    assert len(payments) == 1 and payments[0].canal == "whatsapp" and payments[0].estado == "enviado"
    assert media_provider["downloads"] == 1
    assert db.get(Producto, product).stock_actual == 10 and not db.scalars(select(OrdenCobro)).all()
    assert http.get(f"/operaciones/pagos/{payments[0].id}/comprobante", headers=headers[1]).content == proof()
    assert http.post(f"/operaciones/pagos/{payments[0].id}/validar", headers=headers[1]).status_code == 403
    response = http.post(f"/operaciones/pagos/{payments[0].id}/validar", headers=headers[5])
    assert response.status_code == 200 and response.json()["estado"] == "pagada"
    assert db.get(Producto, product).stock_actual == 8
    assert http.post(f"/operaciones/pagos/{payments[0].id}/validar", headers=headers[5]).status_code == 200
    assert db.get(Producto, product).stock_actual == 8


@pytest.mark.parametrize("case", ["wrong_phone", "inactive", "permission"])
def test_proof_rejects_unauthorized_sender_before_download(operations, media_provider, case):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    if case == "inactive":
        db.get(Usuario, 1).activo = False
    elif case == "permission":
        db.add(PermisoRol(rol=TipoUsuario.CLIENTE, modulo="ventas", puede_ver=True, puede_crear=False))
    db.commit()
    assert incoming(http, order["codigo"], phone="51900000000" if case == "wrong_phone" else "51999888777").status_code == 200
    assert not db.scalars(select(AbonoOrden)).all() and media_provider["downloads"] == 0
    assert not db.scalar(select(MensajeEntrante)).resultado.startswith("comprobante_vinculado")


@pytest.mark.parametrize("case", ["declared_size", "actual_size", "mime", "corrupt", "amount_format", "overpayment"])
def test_proof_limits_and_invalid_content_do_not_create_payments(operations, media_provider, case):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    caption = None
    if case == "declared_size": media_provider["size"] = 5 * 1024 * 1024 + 1
    if case == "actual_size": media_provider["content"] = b"x" * (5 * 1024 * 1024 + 1)
    if case == "mime": media_provider["mime"] = "application/octet-stream"
    if case == "corrupt": media_provider["content"] = b"not-a-png"
    if case == "amount_format": caption = f"{order['codigo']} MONTO=40.001 MEDIO=yape"
    if case == "overpayment": caption = f"{order['codigo']} MONTO=41.00 MEDIO=yape"
    assert incoming(http, order["codigo"], caption=caption).status_code == 200
    assert not db.scalars(select(AbonoOrden)).all()
    assert db.get(Producto, product).stock_actual == 10
    result = db.scalar(select(MensajeEntrante)).resultado
    assert not result.startswith("comprobante_vinculado")


@pytest.mark.parametrize("stage", ["failure", "stream_failure"])
def test_transient_media_failure_does_not_consume_incoming_message_id(operations, media_provider, stage):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    media_provider[stage] = True
    assert incoming(http, order["codigo"]).status_code == 503
    assert not db.scalars(select(MensajeEntrante)).all() and not db.scalars(select(AbonoOrden)).all()
    media_provider[stage] = False
    assert incoming(http, order["codigo"]).status_code == 200
    assert len(db.scalars(select(AbonoOrden)).all()) == 1


def test_incoming_log_is_private_and_does_not_expose_file_caption(operations, media_provider):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    assert incoming(http, order["codigo"]).status_code == 200
    path = "/admin/operaciones/mensajes-entrantes"
    assert http.get(path, headers=headers[1]).status_code == 403
    response = http.get(path, headers=headers[4])
    assert response.status_code == 200 and response.headers["cache-control"] == "private, no-store"
    assert response.json()[0]["resultado"] == f"comprobante_vinculado:{order['codigo']}"
    assert "contenido" not in response.json()[0] and "OP-1" not in response.text


def test_client_acceptance_and_admin_cancellation_notify_correct_veterinarian_once(operations, monkeypatch):
    http, db, headers, start, _ = operations
    db.get(Usuario, 2).telefono_personal = "988777666"
    settings = get_settings()
    monkeypatch.setattr(settings, "whatsapp_phone_number_id", "test-number")
    monkeypatch.setattr(settings, "whatsapp_access_token", "test-token")
    for event in ("cita_reprogramada", "cita_cancelada", "veterinario_reprogramacion", "veterinario_cancelacion"):
        db.add(PlantillaMensaje(evento=event, nombre_proveedor="test_" + event, contenido=EVENTS[event][0], variables=EVENTS[event][1], idioma="es_PE", activa=True))
    db.commit()
    sent = []
    def post(url, **kwargs):
        sent.append(kwargs["json"])
        return httpx.Response(200, request=httpx.Request("POST", url), json={"messages": [{"id": f"wamid.out.{len(sent)}"}]})
    monkeypatch.setattr(messaging.httpx, "post", post)
    response = http.patch("/portal/veterinario/solicitudes/1", headers=headers[2], json={"estado": "requiere_otro_horario", "fecha_hora_propuesta": (start + dt.timedelta(hours=3)).isoformat()})
    assert response.status_code == 200, response.text
    assert not db.scalars(select(MensajeSalida).where(MensajeSalida.evento == "veterinario_reprogramacion")).all()
    assert http.patch("/portal/citas/1/aceptar-horario", headers=headers[1]).status_code == 200
    assert http.patch("/portal/citas/1/aceptar-horario", headers=headers[1]).status_code == 409
    assert http.patch("/admin/citas/1", headers=headers[4], json={"estado": "cancelada", "nota_coordinacion": "Coordinado"}).status_code == 200
    rows = db.scalars(select(MensajeSalida).where(MensajeSalida.evento.in_(["cita_reprogramada", "cita_cancelada", "veterinario_reprogramacion", "veterinario_cancelacion"]))).all()
    assert len(rows) == 4
    for row in rows:
        if row.evento.startswith("veterinario_"):
            assert row.usuario_id == 2 and row.destinatario == "51988777666"
        else:
            assert row.usuario_id == 1 and row.destinatario == "51999888777"
        MessagingService(db).deliver(row)
        assert row.estado == ("cancelado" if row.evento in {"cita_reprogramada", "veterinario_reprogramacion"} else "enviado")
    assert len(sent) == 2  # La cancelación posterior invalida los avisos de reprogramación aún pendientes.


def test_all_templates_are_editable_with_correct_variables_and_read_only_is_enforced(operations):
    http, db, headers, *_ = operations
    status = http.get("/admin/operaciones/comunicaciones/estado", headers=headers[4]).json()
    assert {row["evento"] for row in status["plantillas"]} == set(EVENTS)
    for event in ("cita_confirmada", "cita_reprogramada", "veterinario_reprogramacion", "veterinario_cancelacion"):
        body, variables = EVENTS[event]
        payload = {"nombre_proveedor": "approved_" + event, "contenido": body, "variables": variables, "idioma": "es_PE", "activa": True}
        response = http.put(f"/admin/operaciones/plantillas/{event}", headers=headers[4], json=payload)
        assert response.status_code == 200, response.text
        assert response.json()["nombre_proveedor"] == "approved_" + event
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="usuarios", puede_ver=True, puede_editar=False)); db.commit()
    assert http.get("/admin/operaciones/comunicaciones/estado", headers=headers[4]).status_code == 200
    assert http.put("/admin/operaciones/plantillas/veterinario_cancelacion", headers=headers[4], json=payload).status_code == 403
