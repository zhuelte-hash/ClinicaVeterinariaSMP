"""HU-018/056/103/104/105: aceptación aislada, sin acreditar proveedores externos."""
import datetime as dt
from io import BytesIO

import httpx
import pytest
from PIL import Image
from sqlalchemy import select

from test_admin_clinical_flows import clinic
from test_priority_stories import operations
from app.config import get_settings
from app.models.clinic import AplicacionPreventiva, ProcesoAtencion, ProcesoAtencionMedica
from app.models.operations import MensajeSalida, PlantillaMensaje, Sucursal
from app.models.user import PermisoRol, TipoUsuario, Usuario
from app.routers import operations as routes
from app.schemas.operations import TemplateWrite
from app.services import automation_service, messaging_service
from app.services.messaging_service import EVENTS, MessagingService
from app.services.policy_service import ZONE


def photo():
    buffer = BytesIO()
    Image.new("RGB", (20, 20), "green").save(buffer, "PNG")
    return buffer.getvalue()


def test_gallery_upload_publish_reorder_and_remove_preserve_other_policies(operations, tmp_path, monkeypatch):
    http, _db, headers, *_ = operations
    monkeypatch.setattr(routes, "INSTALLATIONS_DIR", tmp_path)
    before = http.get("/publico/institucional").json()
    photos = []
    for title in ("Consultorio principal", "Recepción de la clínica"):
        response = http.post("/admin/operaciones/instalaciones", headers=headers[4], files={"archivo": ("real.png", photo(), "image/png")})
        assert response.status_code == 200, response.text
        photos.append({"url": response.json()["url"], "titulo": title})
    assert len(list(tmp_path.iterdir())) == 2
    assert http.get("/publico/institucional").json()["galeria"] == []
    url = "/admin/operaciones/galeria"
    response = http.put(url, headers=headers[4], json={"galeria": photos[::-1]})
    assert response.status_code == 200, response.text
    assert http.get("/publico/institucional").json() == {**before, "galeria": photos[::-1]}
    assert http.put(url, headers=headers[4], json={"galeria": photos[:1]}).status_code == 200
    assert http.put(url, headers=headers[4], json={"galeria": []}).status_code == 200
    assert http.get("/publico/institucional").json() == before


@pytest.mark.parametrize("gallery", [
    [{"url": "/uploads/instalaciones/abc.png", "titulo": "No subida"}],
    [{"url": "https://example.com/fake.jpg", "titulo": "Externa"}],
    [{"url": "/uploads/instalaciones/../abc.png", "titulo": "Ruta inválida"}],
    [{"url": "/uploads/instalaciones/abc.png", "titulo": "x"}],
    [{"url": "/uploads/instalaciones/abc.png", "titulo": "Duplicada"}] * 2,
])
def test_gallery_rejects_unpublished_missing_invalid_and_duplicate_photos(operations, gallery):
    http, _db, headers, *_ = operations
    assert http.put("/admin/operaciones/galeria", headers=headers[4], json={"galeria": gallery}).status_code == 422
    assert http.get("/publico/institucional").json()["galeria"] == []


def test_gallery_and_vaccine_policy_enforce_write_permissions_and_image_content(operations, tmp_path, monkeypatch):
    http, db, headers, *_ = operations
    monkeypatch.setattr(routes, "INSTALLATIONS_DIR", tmp_path)
    assert http.post("/admin/operaciones/instalaciones", headers=headers[4], files={"archivo": ("fake.png", b"not a photo", "image/png")}).status_code == 422
    assert not list(tmp_path.iterdir())
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="usuarios", puede_ver=True, puede_editar=False)); db.commit()
    for user in (1, 4):
        assert http.put("/admin/operaciones/galeria", headers=headers[user], json={"galeria": []}).status_code == 403
        assert http.put("/admin/operaciones/politicas-vacunas", headers=headers[user], json={"dias_recordatorio_vacuna": 2}).status_code == 403
        assert http.post("/admin/operaciones/instalaciones", headers=headers[user], files={"archivo": ("real.png", photo(), "image/png")}).status_code == 403


@pytest.mark.parametrize("days", [0, 30, -1, 31, 1.5])
def test_vaccine_policy_boundaries_preserve_unrelated_settings(operations, days):
    http, _db, headers, *_ = operations
    before = http.get("/publico/institucional").json()
    response = http.put("/admin/operaciones/politicas-vacunas", headers=headers[4], json={"dias_recordatorio_vacuna": days})
    valid = days in (0, 30)
    assert response.status_code == (200 if valid else 422), response.text
    assert http.get("/publico/institucional").json() == ({**before, "dias_recordatorio_vacuna": days} if valid else before)


@pytest.mark.parametrize("with_appointment", [False, True])
def test_vet_programs_next_vaccine_and_worker_notifies_exactly_once(operations, monkeypatch, with_appointment):
    http, db, headers, *_ = operations
    monkeypatch.setattr(get_settings(), "whatsapp_access_token", "")
    fixed = dt.datetime(2026, 11, 18, 2, tzinfo=dt.timezone.utc)  # Todavía 17/11 en Perú.
    monkeypatch.setattr(automation_service, "now", lambda: fixed)
    process = ProcesoAtencion(cita_id=1 if with_appointment else None, mascota_id=1, tipo="medica", estado="en_atencion")
    db.add(process); db.flush()
    db.add(ProcesoAtencionMedica(proceso_id=process.id, veterinario_id=2)); db.commit()
    date = fixed.astimezone(ZONE).date() + dt.timedelta(days=3)
    response = http.post(f"/portal/veterinario/atenciones/{process.id}/preventivos", headers=headers[2], json={"tipo": "vacuna", "producto": "Vacuna anual", "fecha_aplicacion": "2026-11-17", "proxima_fecha": date.isoformat()})
    assert response.status_code == 201, response.text
    assert response.json()["proxima_fecha"] == date.isoformat()
    for _ in range(2):
        automation_service.run_automations(db)
    rows = db.scalars(select(MensajeSalida).where(MensajeSalida.evento == "vacuna")).all()
    assert len(rows) == 1
    assert rows[0].usuario_id == 1 and rows[0].destinatario == "51999888777"
    assert rows[0].parametros == ["María Pérez", "Luna", "Vacuna anual", date.isoformat()]
    assert rows[0].estado == "pendiente_configuracion"


@pytest.mark.parametrize("branch,inactive", [(1, False), (2, False), (1, True)])
def test_vaccine_window_type_and_branch_do_not_duplicate_or_notify_inactive_owner(operations, monkeypatch, branch, inactive):
    _http, db, *_ = operations
    monkeypatch.setattr(get_settings(), "whatsapp_access_token", "")
    fixed = dt.datetime(2026, 11, 18, 2, tzinfo=dt.timezone.utc)
    monkeypatch.setattr(automation_service, "now", lambda: fixed)
    today = fixed.astimezone(ZONE).date()
    db.add(Sucursal(id=2, nombre="Segunda sede")); db.flush()
    owner = db.get(Usuario, 1); owner.sucursal_id = branch; owner.activo = not inactive
    process = ProcesoAtencion(mascota_id=1, tipo="medica", estado="en_atencion")
    db.add(process); db.flush()
    for product, kind, date in [("Hoy", "vacuna", today), ("Límite", "vacuna", today + dt.timedelta(days=3)), ("Lejana", "vacuna", today + dt.timedelta(days=4)), ("Vencida", "vacuna", today - dt.timedelta(days=1)), ("Sin fecha", "vacuna", None), ("Desparasitación", "desparasitacion", today)]:
        db.add(AplicacionPreventiva(proceso_id=process.id, veterinario_id=2, tipo=kind, producto=product, proxima_fecha=date))
    db.commit()
    for _ in range(2):
        automation_service.run_automations(db)
    rows = db.scalars(select(MensajeSalida).where(MensajeSalida.evento == "vacuna")).all()
    assert {row.parametros[2] for row in rows} == (set() if inactive else {"Hoy", "Límite"})
    assert len(rows) == (0 if inactive else 2)
    assert db.info["sucursal_id"] == 1


def test_template_preview_uses_saved_order_without_sending_or_writing(operations, monkeypatch):
    http, db, headers, *_ = operations
    event = "veterinario_reprogramacion"
    payload = {"nombre_proveedor": "approved_vet", "contenido": EVENTS[event][0], "variables": ["fecha", "mascota", "cita"]}
    assert http.put(f"/admin/operaciones/plantillas/{event}", headers=headers[4], json=payload).status_code == 200
    monkeypatch.setattr(messaging_service.httpx, "post", lambda *_a, **_kw: pytest.fail("Una vista previa no debe conectar al proveedor"))
    values = {"cita": "123", "mascota": "Luna", "fecha": "20/11/2026 10:00"}
    response = http.post(f"/admin/operaciones/plantillas/{event}/vista-previa", headers=headers[4], json={"valores": values})
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json()["contenido"] == EVENTS[event][0].format_map(values)
    assert [p["valor"] for p in response.json()["parametros"]] == [values[name] for name in payload["variables"]]
    assert not db.scalars(select(MensajeSalida)).all()
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="usuarios", puede_ver=True, puede_editar=False)); db.commit()
    assert http.post(f"/admin/operaciones/plantillas/{event}/vista-previa", headers=headers[4], json={"valores": values}).status_code == 200
    assert http.post(f"/admin/operaciones/plantillas/{event}/vista-previa", headers=headers[1], json={"valores": values}).status_code == 403


@pytest.mark.parametrize("values", [{}, {"nombre": "x"}, {"nombre": "x", "mascota": "y", "codigo": "z", "extra": "x"}, {"nombre": "x" * 501, "mascota": "y", "codigo": "z"}])
def test_template_preview_rejects_missing_extra_and_oversized_examples(operations, values):
    http, _db, headers, *_ = operations
    assert http.post("/admin/operaciones/plantillas/receta/vista-previa", headers=headers[4], json={"valores": values}).status_code == 422


def test_template_variable_reorder_updates_pending_but_preserves_sent_history(operations):
    _http, db, *_ = operations
    service = MessagingService(db)
    event = "veterinario_reprogramacion"
    values = {"cita": "123", "mascota": "Luna", "fecha": "20/11/2026 10:00"}
    pending = service.to_user(db.get(Usuario, 2), event, "pending-vet", values)
    sent = service.to_user(db.get(Usuario, 2), event, "sent-vet", values)
    sent.estado = "enviado"; db.commit()
    service.save_template(event, TemplateWrite(contenido=EVENTS[event][0], variables=["fecha", "mascota", "cita"]))
    assert pending.parametros == [values["fecha"], "Luna", "123"]
    assert sent.parametros == ["123", "Luna", values["fecha"]]


@pytest.mark.parametrize("invalid_phone", [None, "123", "00000000000"])
def test_vet_message_waits_for_valid_phone_then_retries_to_corrected_contact(operations, monkeypatch, invalid_phone):
    _http, db, *_ = operations
    settings = get_settings()
    monkeypatch.setattr(settings, "whatsapp_access_token", "test-token")
    monkeypatch.setattr(settings, "whatsapp_phone_number_id", "test-number")
    event = "veterinario_reprogramacion"
    vet = db.get(Usuario, 2); vet.telefono_personal = invalid_phone
    db.add(PlantillaMensaje(evento=event, nombre_proveedor="approved_vet", contenido=EVENTS[event][0], variables=EVENTS[event][1], idioma="es", activa=True)); db.commit()
    calls = []
    def post(url, **kwargs):
        calls.append(kwargs["json"])
        return httpx.Response(200, request=httpx.Request("POST", url), json={"messages": [{"id": "wamid.corrected"}]})
    monkeypatch.setattr(messaging_service.httpx, "post", post)
    row = MessagingService(db).to_user(vet, event, "vet-retry", {"cita": 1, "mascota": "Luna", "fecha": "20/11/2026 10:00"})
    db.commit(); MessagingService(db).deliver(row)
    assert row.estado == "pendiente_configuracion" and row.intentos == 0 and not calls
    vet.telefono_personal = "+51 988 777 666"; db.commit()
    MessagingService(db).deliver(row)
    assert row.estado == "enviado" and calls[0]["to"] == "51988777666"


def test_deactivated_vet_does_not_receive_queued_notification(operations, monkeypatch):
    _http, db, *_ = operations
    vet = db.get(Usuario, 2)
    row = MessagingService(db).to_user(vet, "veterinario_reprogramacion", "vet-disabled", {"cita": 1, "mascota": "Luna", "fecha": "20/11/2026 10:00"})
    vet.activo = False; db.commit()
    monkeypatch.setattr(messaging_service.httpx, "post", lambda *_a, **_kw: pytest.fail("No enviar al profesional inactivo"))
    MessagingService(db).deliver(row)
    assert row.estado == "cancelado" and row.intentos == 0
