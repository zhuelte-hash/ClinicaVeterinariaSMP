"""HU-023/HU-092: horarios publicados y agenda, con JWT y datos aislados."""
import copy
import datetime as dt

import pytest
from sqlalchemy import select

from test_admin_clinical_flows import clinic
from test_priority_stories import operations
from app.models.clinic import Cita, HorarioVeterinario
from app.models.operations import EventoAuditoria, Sucursal
from app.models.user import PermisoRol, TipoUsuario, Usuario
from app.services.policy_service import ZONE

HOURS_URL = "/admin/operaciones/horario-clinica"


def hours(http):
    policy = http.get("/publico/institucional").json()
    return {key: policy[key] for key in ("horarios", "excepciones")}


def test_schedule_editor_can_publish_hours_without_user_management_permission(operations):
    http, db, headers, start, _ = operations
    policy = http.get("/publico/institucional").json()
    policy.update(horas_cancelacion=12, horas_reprogramacion=8)
    assert http.put("/admin/operaciones/configuracion", headers=headers[4], json=policy).status_code == 200
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="usuarios", puede_ver=False))
    db.commit()
    assert http.get("/admin/operaciones/configuracion", headers=headers[4]).status_code == 403
    assert http.get("/admin/citas/veterinarios", headers=headers[4]).status_code == 200
    payload = hours(http)
    payload["horarios"][0]["inicio"] = "09:00"
    response = http.put(HOURS_URL, headers=headers[4], json=payload)
    assert response.status_code == 200, response.text
    published = http.get("/publico/institucional").json()
    assert published["horarios"][0]["inicio"] == "09:00:00"
    assert published["horas_cancelacion"] == 12 and published["horas_reprogramacion"] == 8
    forbidden = http.put(HOURS_URL, headers=headers[4], json={**payload, "horas_cancelacion": 0})
    assert forbidden.status_code == 422
    assert http.get("/publico/institucional").json() == published
    events = db.scalars(select(EventoAuditoria).where(EventoAuditoria.entidad == "politicas_clinica")).all()
    assert any(event.usuario_id == 4 and "horarios" in event.cambios for event in events)


def test_read_only_and_other_roles_cannot_change_clinic_or_vet_hours(operations):
    http, db, headers, start, _ = operations
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="citas", puede_ver=True, puede_crear=False, puede_editar=False))
    db.commit()
    payload = hours(http)
    schedule_url = "/admin/operaciones/horarios/2"
    rows = http.get(schedule_url, headers=headers[4]).json()
    schedule = {"dia_semana": start.weekday(), "hora_inicio": "08:00", "hora_fin": "20:00", "activo": False}
    for user in (1, 2, 5, 4):
        assert http.put(HOURS_URL, headers=headers[user], json=payload).status_code == 403
        assert http.post(schedule_url, headers=headers[user], json=schedule).status_code == 403
        assert http.put(f"{schedule_url}/{rows[0]['id']}", headers=headers[user], json=schedule).status_code == 403
    assert http.get("/publico/institucional").status_code == 200
    assert http.get(schedule_url, headers=headers[4]).status_code == 200


@pytest.mark.parametrize("invalid", ["missing_day", "duplicate_day", "reversed", "outside_break", "half_break", "duplicate_exception", "timezone"])
def test_invalid_hours_are_rejected_without_changing_published_schedule(operations, invalid):
    http, _, headers, start, _ = operations
    original = hours(http)
    payload = copy.deepcopy(original)
    if invalid == "missing_day":
        payload["horarios"].pop()
    elif invalid == "duplicate_day":
        payload["horarios"][0]["dia"] = 1
    elif invalid == "reversed":
        payload["horarios"][0].update(inicio="20:00", fin="08:00")
    elif invalid == "outside_break":
        payload["horarios"][0].update(inicio="09:00", fin="11:00", descanso_inicio="12:00", descanso_fin="13:00")
    elif invalid == "half_break":
        payload["horarios"][0]["descanso_fin"] = None
    elif invalid == "duplicate_exception":
        exception = {"dia": start.weekday(), "fecha": start.date().isoformat(), "motivo": "Feriado", "cerrado": True}
        payload["excepciones"] = [exception, exception]
    elif invalid == "timezone":
        payload["horarios"][0]["inicio"] = "08:00:00+03:00"
    response = http.put(HOURS_URL, headers=headers[4], json=payload)
    assert response.status_code == 422, response.text
    assert hours(http) == original


def test_published_hours_breaks_and_exceptions_are_used_by_availability(operations):
    http, db, headers, start, _ = operations
    payload = hours(http)
    payload["horarios"].reverse()  # La publicación debe mantener lunes a domingo.
    day = next(day for day in payload["horarios"] if day["dia"] == start.weekday())
    day.update(inicio="08:00", fin="12:00", descanso_inicio="09:00", descanso_fin="10:00")
    assert http.put(HOURS_URL, headers=headers[4], json=payload).status_code == 200
    public = http.get("/publico/institucional").json()
    assert [day["dia"] for day in public["horarios"]] == list(range(7))
    assert public["horarios"][6]["cerrado"]
    query = {"servicio_id": 1, "fecha": start.date().isoformat()}
    slots = http.get("/portal/disponibilidad", params=query).json()
    assert slots
    for slot in slots:
        initial = dt.datetime.fromisoformat(slot["fecha_hora"]).astimezone(ZONE)
        final = initial + dt.timedelta(minutes=30)
        assert dt.time(8) <= initial.time() and final.time() <= dt.time(12)
        assert final.time() <= dt.time(9) or initial.time() >= dt.time(10)
    payload["excepciones"] = [{"dia": 0, "fecha": start.date().isoformat(), "motivo": "Feriado local", "cerrado": True}]
    assert http.put(HOURS_URL, headers=headers[4], json=payload).status_code == 200
    assert http.get("/publico/institucional").json()["excepciones"][0]["dia"] == start.weekday()
    assert http.get("/portal/disponibilidad", params=query).json() == []
    booking = {"mascota_id": 1, "servicio_id": 1, "veterinario_id": 2, "fecha_hora_programada": slots[0]["fecha_hora"]}
    assert http.post("/portal/citas", headers=headers[1], json=booking).status_code == 422
    assert db.get(Cita, 1) is not None  # No se borran citas al cerrar un día.
    payload["excepciones"][0].update(cerrado=False, inicio="14:00", fin="16:00", descanso_inicio=None, descanso_fin=None)
    assert http.put(HOURS_URL, headers=headers[4], json=payload).status_code == 200
    slots = http.get("/portal/disponibilidad", params=query).json()
    assert slots
    assert all(dt.time(14) <= dt.datetime.fromisoformat(slot["fecha_hora"]).astimezone(ZONE).time() < dt.time(16) for slot in slots)


def test_admin_professional_hours_are_scoped_persistent_and_affect_reservations(operations):
    http, db, headers, start, _ = operations
    url = "/admin/operaciones/horarios/2"
    rows = http.get(url, headers=headers[4]).json()
    schedule = {"dia_semana": start.weekday(), "hora_inicio": "08:00", "hora_fin": "09:00", "activo": True}
    assert http.post(url, headers=headers[4], json=schedule).status_code == 409
    changed = http.put(f"{url}/{rows[0]['id']}", headers=headers[4], json=schedule)
    assert changed.status_code == 200, changed.text
    assert db.get(HorarioVeterinario, rows[0]["id"]).hora_fin == dt.time(9)
    query = {"servicio_id": 1, "fecha": start.date().isoformat()}
    own = [slot for slot in http.get("/portal/disponibilidad", params=query).json() if slot["veterinario_id"] == 2]
    assert own and all(dt.datetime.fromisoformat(slot["fecha_hora"]).astimezone(ZONE).hour == 8 for slot in own)
    schedule["activo"] = False
    assert http.put(f"{url}/{rows[0]['id']}", headers=headers[4], json=schedule).status_code == 200
    assert all(slot["veterinario_id"] != 2 for slot in http.get("/portal/disponibilidad", params=query).json())
    other = http.get("/admin/operaciones/horarios/3", headers=headers[4]).json()[0]
    assert http.put(f"{url}/{other['id']}", headers=headers[4], json=schedule).status_code == 404
    db.add(Sucursal(id=2, nombre="Otra sede"))
    db.get(Usuario, 3).sucursal_id = 2
    db.commit()
    assert http.get("/admin/operaciones/horarios/3", headers=headers[4]).status_code == 404
    db.get(Usuario, 2).activo = False
    db.commit()
    assert http.get(url, headers=headers[4]).status_code == 404
