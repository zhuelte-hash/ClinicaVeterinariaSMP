"""HU-043/062/094/099/107/108: HTTP/JWT, persistencia y proveedor controlado."""
import datetime as dt
import re
import json
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select

from test_admin_clinical_flows import clinic
from test_priority_stories import operations, proof
from test_next_five_stories import start_attention
from test_priority_communications import webhook
from app.config import get_settings
from app.models.clinic import BloqueoHorario, Caja, Cita, EstadoCita, HorarioVeterinario, ProcesoAtencion
from app.models.clinic import Producto
from app.models.purchase import PedidoWeb
from app.security import create_access_token
from app.models.operations import DesafioCuenta, EncuestaConsulta, MensajeSalida, PlantillaMensaje, Sucursal
from app.models.user import PermisoRol, TipoUsuario, Usuario
from app.services.access_service import digest, now
from app.services.automation_service import run_automations
from app.services.messaging_service import EVENTS, MessagingService


def messages(db, event):
    return db.scalars(select(MensajeSalida).where(MensajeSalida.evento == event)).all()


@pytest.fixture
def customer_provider(operations, monkeypatch):
    _, db, *_ = operations
    monkeypatch.setattr(get_settings(), "whatsapp_phone_number_id", "controlled-number")
    monkeypatch.setattr(get_settings(), "whatsapp_access_token", "controlled-token")
    for event in ("bienvenida", "laboratorio", "encuesta"):
        db.add(PlantillaMensaje(evento=event, nombre_proveedor=event, contenido=EVENTS[event][0], variables=EVENTS[event][1], idioma="es", activa=True))
    db.commit()
    calls = []

    def post(url, **kwargs):
        calls.append(kwargs["json"])
        return httpx.Response(200, json={"messages": [{"id": f"controlled-{len(calls)}"}]}, request=httpx.Request("POST", url))

    monkeypatch.setattr("app.services.messaging_service.httpx.post", post)
    return calls


def test_occupancy_intersects_hours_breaks_and_merges_overlapping_blocks(operations):
    http, db, headers, start, _ = operations
    # 08–20 menos descanso (60 min) y dos bloqueos superpuestos (90 min).
    db.add_all([BloqueoHorario(veterinario_id=2, fecha_hora_inicio=start + dt.timedelta(minutes=15), fecha_hora_fin=start + dt.timedelta(hours=1), motivo="Permiso"), BloqueoHorario(veterinario_id=2, fecha_hora_inicio=start + dt.timedelta(minutes=45), fecha_hora_fin=start + dt.timedelta(hours=1, minutes=45), motivo="Vacaciones")])
    db.get(Cita, 1).estado = EstadoCita.CONFIRMADA
    db.commit()
    response = http.get("/admin/operaciones/ocupacion", headers=headers[4], params={"desde": start.date().isoformat(), "hasta": start.date().isoformat(), "veterinario_id": 2})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["capacidad_minutos"] == 570 and data["ocupados_minutos"] == 15
    assert data["porcentaje"] == round(15 / 570 * 100, 2)
    assert len(data["detalle"]) == 1 and data["detalle"][0]["veterinario_id"] == 2


@pytest.mark.parametrize("query,code", [("desde=2026-11-02&hasta=2026-11-01", 422), ("desde=2024-01-01&hasta=2026-11-01", 422), ("desde=2026-11-01&hasta=2026-11-01&veterinario_id=0", 422), ("desde=2026-11-01&hasta=2026-11-01&veterinario_id=999", 404)])
def test_occupancy_invalid_selection(operations, query, code):
    http, _, headers, *_ = operations
    assert http.get("/admin/operaciones/ocupacion?" + query, headers=headers[4]).status_code == code


def test_occupancy_closed_day_empty_branch_and_read_permission(operations):
    http, db, headers, *_ = operations
    query = "?desde=2026-11-22&hasta=2026-11-22"
    assert http.get("/admin/operaciones/ocupacion" + query, headers=headers[4]).json()["capacidad_minutos"] == 0
    db.add(Sucursal(id=2, nombre="Segunda")); db.commit()
    assert http.get("/admin/operaciones/ocupacion" + query, headers={**headers[4], "X-Sucursal-ID": "2"}).json()["detalle"] == []
    assert http.get("/admin/operaciones/ocupacion" + query, headers=headers[1]).status_code == 403
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="citas", puede_ver=False)); db.commit()
    assert http.get("/admin/operaciones/ocupacion" + query, headers=headers[4]).status_code == 403


def test_referral_acceptance_grants_only_referred_case_and_persists_answer(operations):
    http, db, headers, *_ = operations
    process = start_attention(http, db, headers)
    url = f"/portal/veterinario/atenciones/{process}/notas-privadas"
    assert http.get(url, headers=headers[3]).status_code == 404
    created = http.post(f"/portal/veterinario/atenciones/{process}/derivaciones", headers=headers[2], json={"receptor_id": 3, "motivo": "Evaluación por especialista"})
    assert created.status_code == 201, created.text
    referral_id = created.json()["id"]
    assert http.post(f"/portal/veterinario/derivaciones/{referral_id}/responder", headers=headers[2], json={"aceptar": True, "respuesta": "Respuesta ajena"}).status_code == 404
    answered = http.post(f"/portal/veterinario/derivaciones/{referral_id}/responder", headers=headers[3], json={"aceptar": True, "respuesta": "Acepto continuar evaluación"})
    assert answered.status_code == 200 and answered.json()["aceptada_en"]
    assert http.put(url, headers=headers[3], json={"notas": "Seguimiento especialista"}).status_code == 200
    assert http.get(url, headers=headers[2]).json()["notas"] == "Seguimiento especialista"
    assert process in [row["id"] for row in http.get("/portal/veterinario/mascotas/1/historial", headers=headers[3]).json()]
    assert process in [row["id"] for row in http.get("/portal/veterinario/atenciones", headers=headers[3]).json()]
    assert http.post(f"/portal/veterinario/derivaciones/{referral_id}/responder", headers=headers[3], json={"aceptar": False, "respuesta": "Otra respuesta"}).status_code == 409
    assert http.get("/portal/veterinario/derivaciones", headers=headers[3]).json()[0]["mascota"] == "Luna"


@pytest.mark.parametrize("target", [1, 2, 999])
def test_referral_rejects_invalid_specialist(operations, target):
    http, db, headers, *_ = operations
    process = start_attention(http, db, headers)
    assert http.post(f"/portal/veterinario/atenciones/{process}/derivaciones", headers=headers[2], json={"receptor_id": target, "motivo": "Revisar caso"}).status_code == 422


def test_referral_rejection_duplicates_branch_and_permission(operations):
    http, db, headers, *_ = operations
    process = start_attention(http, db, headers)
    url = f"/portal/veterinario/atenciones/{process}/derivaciones"
    data = {"receptor_id": 3, "motivo": "Segunda opinión"}
    created = http.post(url, headers=headers[2], json=data)
    assert created.status_code == 201
    assert http.post(url, headers=headers[2], json=data).status_code == 409
    answer = http.post(f"/portal/veterinario/derivaciones/{created.json()['id']}/responder", headers=headers[3], json={"aceptar": False, "respuesta": "Especialidad no disponible"})
    assert answer.status_code == 200
    assert http.get(f"/portal/veterinario/atenciones/{process}/notas-privadas", headers=headers[3]).status_code == 404
    db.add(Sucursal(id=2, nombre="Otra sede")); db.get(Usuario, 3).sucursal_id = 2; db.commit()
    assert http.post(url, headers=headers[2], json=data).status_code == 422
    assert http.get("/portal/veterinario/derivaciones", headers=headers[3]).json() == []
    db.add(PermisoRol(rol=TipoUsuario.VETERINARIO, modulo="historias_clinicas", puede_ver=True, puede_crear=False)); db.commit()
    assert http.post(url, headers=headers[2], json=data).status_code == 403


def test_branches_crud_duplicate_deactivation_and_read_only(operations):
    http, db, headers, *_ = operations
    data = {"nombre": "Sede Norte", "direccion": "Av. Principal 123", "telefono": "999111222", "activa": True}
    created = http.post("/admin/operaciones/sucursales", headers=headers[4], json=data)
    assert created.status_code == 201, created.text
    identifier = created.json()["id"]
    assert http.post("/admin/operaciones/sucursales", headers=headers[4], json={**data, "nombre": "sede norte"}).status_code == 409
    assert http.put(f"/admin/operaciones/sucursales/{identifier}", headers=headers[4], json={**data, "activa": False}).status_code == 200
    assert identifier not in [row["id"] for row in http.get("/publico/sucursales").json()]
    assert http.put("/admin/operaciones/sucursales/1", headers=headers[4], json={**data, "nombre": "Principal", "activa": False}).status_code == 409
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="usuarios", puede_ver=True, puede_crear=False, puede_editar=False)); db.commit()
    assert http.get("/admin/operaciones/sucursales", headers=headers[4]).status_code == 200
    assert http.post("/admin/operaciones/sucursales", headers=headers[4], json={**data, "nombre": "Sur"}).status_code == 403
    assert http.get("/admin/operaciones/sucursales", headers=headers[5]).status_code == 403


def test_staff_assignment_scopes_lists_validates_branch_and_preserves_open_work(operations):
    http, db, headers, *_ = operations
    db.add(Sucursal(id=2, nombre="Segunda")); db.commit()
    payload = {"nombre": "Nuevo cajero", "correo": "newcash@example.test", "contrasena": "ClaveSegura123", "tipo": "cajero", "sucursal_id": 2}
    created = http.post("/usuarios", headers=headers[4], json=payload)
    assert created.status_code == 201, created.text
    user_id = created.json()["id"]
    assert user_id not in [u["id"] for u in http.get("/usuarios?solo_personal=true", headers=headers[4]).json()]
    assert user_id in [u["id"] for u in http.get("/usuarios?solo_personal=true", headers={**headers[4], "X-Sucursal-ID": "2"}).json()]
    assert http.patch("/usuarios/5", headers=headers[4], json={"sucursal_id": 2}).status_code == 409
    assert http.patch("/usuarios/2", headers=headers[4], json={"sucursal_id": 2}).status_code == 409
    assert http.patch(f"/usuarios/{user_id}", headers=headers[4], json={"sucursal_id": 999}).status_code == 422
    db.add(Caja(cajero_id=user_id, sucursal_id=2, estado_caja="abierta", fondo_inicial=0)); db.commit()
    assert http.put("/admin/operaciones/sucursales/2", headers=headers[4], json={"nombre": "Segunda", "activa": False}).status_code == 409


def test_branch_selection_separates_calendar_inventory_and_reports(operations):
    http, db, headers, start, _ = operations
    db.add(Sucursal(id=2, nombre="Segunda")); db.commit()
    second = {**headers[4], "X-Sucursal-ID": "2"}
    assert http.get("/admin/citas", headers=second).json() == []
    assert http.get("/admin/productos", headers=second).json() == []
    assert http.get("/admin/operaciones/valorizacion", headers=second).json()["total"] == 0
    report = http.get(f"/admin/operaciones/dashboard?desde={start.date()}&hasta={start.date()}", headers=second).json()
    assert report["sucursal_id"] == 2 and not any(report["citas_por_estado"].values())
    assert http.get("/caja/resumen", headers={**headers[5], "X-Sucursal-ID": "2"}).status_code == 403


def test_staff_move_revokes_session_disables_old_hours_and_walk_in_uses_new_branch(operations):
    http, db, headers, *_ = operations
    db.add(Sucursal(id=2, nombre="Segunda")); db.get(Cita, 2).estado = EstadoCita.CANCELADA; db.commit()
    moved = http.patch("/usuarios/3", headers=headers[4], json={"sucursal_id": 2})
    assert moved.status_code == 200, moved.text
    assert http.get("/portal/veterinario/solicitudes", headers=headers[3]).status_code == 401
    user = db.get(Usuario, 3)
    new_headers = {"Authorization": "Bearer " + create_access_token(3, user.version_sesion)}
    assert all(not row.activo for row in db.scalars(select(HorarioVeterinario).where(HorarioVeterinario.veterinario_id == 3).execution_options(skip_branch_filter=True)).all())
    walked = http.post("/portal/veterinario/atenciones/iniciar", headers=new_headers, json={"mascota_id": 1, "servicio_id": 1, "motivo": "Atención en nueva sede", "es_urgente": False})
    assert walked.status_code == 201, walked.text
    assert db.scalar(select(Cita.sucursal_id).where(Cita.id == walked.json()["id"]).execution_options(skip_branch_filter=True)) == 2
    assert 3 not in [row["id"] for row in http.get("/admin/citas/veterinarios", headers=headers[4]).json()]
    assert 3 in [row["id"] for row in http.get("/admin/citas/veterinarios", headers={**headers[4], "X-Sucursal-ID": "2"}).json()]


def test_web_order_keeps_branch_and_is_excluded_from_other_branch_reports(operations, monkeypatch):
    http, db, headers, start, product = operations
    for key, value in {"purchase_yape_holder": "Clínica", "purchase_yape_phone": "999888777", "purchase_yape_qr_url": "/qr-test.png"}.items():
        monkeypatch.setattr(get_settings(), key, value)
    db.add(Sucursal(id=2, nombre="Segunda")); db.get(Producto, product).sucursal_id = 2; db.commit()
    data = {"clave_idempotencia": str(uuid4()), "cliente": {"nombreCompleto": "María Pérez", "celular": "999888777", "correo": "owner@example.com", "tipoEntrega": "Recojo en clínica", "tipoComprobante": "Boleta", "dni": "12345678"}, "items": [{"producto_id": product, "cantidad": 2}], "metodo_pago": "yape", "numero_operacion": "WEB-SEDE", "total_esperado": "40.00"}
    created = http.post("/pedidos-web", headers={**headers[1], "X-Sucursal-ID": "2"}, data={"datos": json.dumps(data)}, files={"comprobante": ("pago.png", proof(), "image/png")})
    assert created.status_code == 201, created.text
    identifier = created.json()["id"]
    assert db.scalar(select(PedidoWeb.sucursal_id).where(PedidoWeb.id == identifier).execution_options(skip_branch_filter=True)) == 2
    assert http.get(f"/pedidos-web/{identifier}", headers=headers[4]).status_code == 404
    url = f"/admin/operaciones/dashboard?desde={start.date()}&hasta={start.date()}"
    assert http.get(url, headers=headers[4]).json()["pagos_web_por_validar"] == 0
    assert http.get(url, headers={**headers[4], "X-Sucursal-ID": "2"}).json()["pagos_web_por_validar"] == 1


def test_welcome_is_enqueued_after_verification_once_and_delivered_with_webhook(operations, customer_provider, monkeypatch):
    http, db, _, *_ = operations
    owner = db.get(Usuario, 1); owner.correo_verificado = False
    db.add(DesafioCuenta(usuario_id=1, proposito="verificar", secreto_hash=digest("1:verificar:123456"), expira_en=now() + dt.timedelta(minutes=15))); db.commit()
    assert messages(db, "bienvenida") == []
    payload = {"correo": owner.correo, "codigo": "123456"}
    assert http.post("/auth/verificar-correo", json=payload).status_code == 200
    assert http.post("/auth/verificar-correo", json=payload).status_code == 400
    row, = messages(db, "bienvenida")
    MessagingService(db).deliver(row); db.commit()
    assert row.estado == "enviado" and customer_provider[0]["to"] == "51999888777"
    assert webhook(http, monkeypatch, [{"id": row.proveedor_id, "status": "delivered"}]).status_code == 200
    assert row.estado == "entregado"


@pytest.mark.parametrize("event", ["bienvenida", "laboratorio", "encuesta"])
def test_customer_messages_pause_bad_phone_recheck_current_contact_and_cancel_inactive(operations, customer_provider, event):
    _, db, _, *_ = operations
    owner = db.get(Usuario, 1); owner.cliente.telefono = "123"
    process = ProcesoAtencion(mascota_id=1, tipo="medica", estado="cerrada", fecha_cierre=now() - dt.timedelta(days=1)); db.add(process); db.flush()
    db.add(EncuestaConsulta(proceso_id=process.id, token_hash=digest("test-survey"), expira_en=now() + dt.timedelta(days=1)))
    row = MessagingService(db).to_user(owner, event, f"{event}:test", {"nombre": owner.nombre, "mascota": "Luna", "enlace": "https://example.test"}, entity_id=process.id); db.commit()
    MessagingService(db).deliver(row)
    assert row.estado == "pendiente_configuracion" and row.intentos == 0 and not customer_provider
    owner.cliente.telefono = "999222333"; db.commit(); MessagingService(db).deliver(row); db.commit()
    assert row.estado == "enviado" and row.destinatario == "51999222333"
    row.estado = "pendiente"; owner.activo = False; db.commit(); MessagingService(db).deliver(row)
    assert row.estado == "cancelado" and len(customer_provider) == 1


def test_laboratory_written_and_attached_results_notify_without_exposing_clinical_text(operations, customer_provider, tmp_path, monkeypatch):
    http, db, headers, *_ = operations
    process = start_attention(http, db, headers)
    response = http.patch(f"/portal/veterinario/atenciones/{process}/resultados", headers=headers[2], json={"examenes_resultados": "Resultado confidencial de laboratorio"})
    assert response.status_code == 200, response.text
    row, = messages(db, "laboratorio")
    assert "confidencial" not in row.contenido
    # El archivo solo se sirve mediante enlace privado autenticado; no se adjunta al aviso.
    from pathlib import Path
    original_write = Path.write_bytes
    monkeypatch.setattr(Path, "write_bytes", lambda path, content: original_write(tmp_path / path.name, content))
    uploaded = http.post(f"/portal/veterinario/atenciones/{process}/imagenes?tipo_examen=Laboratorio&fecha_estudio=2026-11-19", headers=headers[2], files={"archivo": ("resultado.pdf", b"%PDF-1.4 prueba", "application/pdf")})
    assert uploaded.status_code == 200, uploaded.text
    assert len(messages(db, "laboratorio")) == 2
    assert all(item.documento is None for item in messages(db, "laboratorio"))
    MessagingService(db).deliver(row); db.commit()
    assert row.estado == "enviado" and customer_provider[0]["template"]["name"] == "laboratorio"
    assert http.post(f"/portal/veterinario/atenciones/{process}/imagenes?tipo_examen=Laboratorio&fecha_estudio=2026-11-19", headers=headers[3], files={"archivo": ("resultado.pdf", b"%PDF", "application/pdf")}).status_code == 404


def prepare_survey(db, monkeypatch, *, with_appointment=False):
    monkeypatch.setattr(get_settings(), "whatsapp_access_token", "")
    current = now()
    monkeypatch.setattr("app.services.automation_service.now", lambda: current)
    # El proveedor permanece controlado por la fixture o sin configurar.
    process = ProcesoAtencion(mascota_id=1, cita_id=1 if with_appointment else None, tipo="medica", estado="cerrada", fecha_cierre=current - dt.timedelta(hours=24))
    db.add(process); db.commit()
    run_automations(db)
    row = messages(db, "encuesta")[0]
    token = re.search(r"/encuesta/([A-Za-z0-9_-]+)", row.contenido).group(1)
    return process, row, token


@pytest.mark.parametrize("with_appointment", [True, False])
def test_survey_24h_including_walk_in_persists_one_answer_and_hides_token_in_log(operations, monkeypatch, with_appointment):
    http, db, headers, *_ = operations
    process, row, token = prepare_survey(db, monkeypatch, with_appointment=with_appointment)
    assert db.scalar(select(EncuestaConsulta).where(EncuestaConsulta.proceso_id == process.id)).token_hash == digest(token)
    run_automations(db)
    assert len(messages(db, "encuesta")) == 1
    response = http.get(f"/encuestas/{token}")
    assert response.status_code == 200 and response.headers["cache-control"] == "private, no-store"
    assert not response.json()["respondida"] and "cliente" not in response.json()
    assert http.post(f"/encuestas/{token}", json={"valoracion": 5, "comentario": "Muy buena atención"}).status_code == 204
    assert http.post(f"/encuestas/{token}", json={"valoracion": 1}).status_code == 409
    assert http.get(f"/encuestas/{token}").json()["respondida"]
    logged = http.get("/admin/operaciones/mensajes?evento=encuesta", headers=headers[4])
    assert token not in logged.text and "contenido" not in logged.json()[0]
    assert http.post(f"/admin/operaciones/mensajes/{row.id}/reintentar", headers=headers[4]).status_code == 409
    saved = db.scalar(select(EncuestaConsulta).where(EncuestaConsulta.proceso_id == process.id))
    assert saved.valoracion == 5 and saved.comentario == "Muy buena atención"


def test_survey_does_not_run_early_or_for_inactive_owner_and_expires(operations, monkeypatch):
    http, db, _, *_ = operations
    db.add(ProcesoAtencion(mascota_id=1, tipo="medica", estado="cerrada", fecha_cierre=now() - dt.timedelta(hours=23))); db.commit()
    run_automations(db)
    assert not messages(db, "encuesta")
    _, _, token = prepare_survey(db, monkeypatch)
    survey = db.scalar(select(EncuestaConsulta)); survey.expira_en = now() - dt.timedelta(seconds=1); db.commit()
    assert http.get(f"/encuestas/{token}").status_code == 404
    assert http.post(f"/encuestas/{token}", json={"valoracion": 5}).status_code == 409
    assert http.get("/encuestas/token-inventado").status_code == 404


@pytest.mark.parametrize("payload", [{"valoracion": 0}, {"valoracion": 6}, {"valoracion": 5, "comentario": "x" * 2001}])
def test_survey_validates_answers(operations, monkeypatch, payload):
    http, db, _, *_ = operations
    _, _, token = prepare_survey(db, monkeypatch)
    assert http.post(f"/encuestas/{token}", json=payload).status_code == 422
