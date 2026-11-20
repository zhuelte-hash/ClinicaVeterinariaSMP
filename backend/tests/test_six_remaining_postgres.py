"""Aceptación nativa, en transacción revertida, de ocupación, derivación y encuesta."""
import datetime as dt
from uuid import uuid4

from sqlalchemy import select

from test_independent_stories_postgres import native
from app.models.clinic import ProcesoAtencion
from app.models.operations import EncuestaConsulta, MensajeSalida
from app.models.user import PermisoRol, TipoUsuario, Usuario, Veterinario
from app.security import create_access_token
from app.services.automation_service import run_automations


def test_native_occupancy_uses_capacity_and_branch(native):
    http, _, headers, appointment, *_, start = native
    response = http.get("/admin/operaciones/ocupacion", headers=headers["administrador"], params={"desde": start.date().isoformat(), "hasta": start.date().isoformat()})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["capacidad_minutos"] == 660 and data["ocupados_minutos"] == 30
    assert data["sucursal_id"] == appointment.sucursal_id


def test_native_referral_acceptance_preserves_case_and_grants_access(native):
    http, db, headers, appointment, pet, *_ = native
    marker = uuid4().hex
    target = Usuario(nombre="Receptor", correo=marker + "@example.test", tipo="veterinario", contrasena="hash", sucursal_id=appointment.sucursal_id)
    db.add(target); db.flush(); db.add(Veterinario(usuario_id=target.id, colegiatura=marker))
    permission = db.scalar(select(PermisoRol).where(PermisoRol.rol == TipoUsuario.VETERINARIO, PermisoRol.modulo == "historias_clinicas"))
    if permission is None:
        permission = PermisoRol(rol=TipoUsuario.VETERINARIO, modulo="historias_clinicas"); db.add(permission)
    permission.puede_ver = permission.puede_crear = True
    process = ProcesoAtencion(mascota_id=pet.id, cita_id=appointment.id, tipo="medica", estado="en_atencion")
    db.add(process); db.commit()
    response = http.post(f"/portal/veterinario/atenciones/{process.id}/derivaciones", headers=headers["veterinario"], json={"receptor_id": target.id, "motivo": "Evaluación nativa"})
    assert response.status_code == 201, response.text
    receiver = {"Authorization": "Bearer " + create_access_token(target.id)}
    assert http.get(f"/portal/veterinario/atenciones/{process.id}/notas-privadas", headers=receiver).status_code == 404
    accepted = http.post(f"/portal/veterinario/derivaciones/{response.json()['id']}/responder", headers=receiver, json={"aceptar": True, "respuesta": "Continuar evaluación"})
    assert accepted.status_code == 200, accepted.text
    db.expire_all()
    assert http.get(f"/portal/veterinario/atenciones/{process.id}/notas-privadas", headers=receiver).status_code == 200


def test_native_survey_generation_is_idempotent_for_walk_in(native):
    _, db, _, _, pet, *_ = native
    process = ProcesoAtencion(mascota_id=pet.id, tipo="medica", estado="cerrada", fecha_cierre=dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=25))
    db.add(process); db.commit()
    run_automations(db); run_automations(db)
    db.expire_all()
    assert len(db.scalars(select(EncuestaConsulta).where(EncuestaConsulta.proceso_id == process.id)).all()) == 1
    assert len(db.scalars(select(MensajeSalida).where(MensajeSalida.clave == f"encuesta:{process.id}")).all()) == 1
