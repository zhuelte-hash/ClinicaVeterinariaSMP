"""Flujo HTTP real de citas en PostgreSQL de pruebas (nunca en Neon)."""

import datetime
import os
import uuid
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models.clinic import Cita, HorarioVeterinario, Mascota, Servicio
from app.models.user import Cliente, PermisoRol, TipoUsuario, Usuario, Veterinario
from app.security import create_access_token
from app.services.whatsapp_service import WhatsAppService


@pytest.mark.skipif(
    not os.environ.get("TEST_APPOINTMENT_DATABASE_URL")
    or os.environ.get("DATABASE_URL") != os.environ.get("TEST_APPOINTMENT_DATABASE_URL"),
    reason="Se requiere una base PostgreSQL aislada indicada explícitamente",
)
def test_booking_shared_by_client_veterinarian_and_read_only_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    database = urlparse(os.environ["TEST_APPOINTMENT_DATABASE_URL"])
    assert database.hostname in {"localhost", "127.0.0.1", "clinica-citas-test-db"} and "test" in database.path, "Usa solo una base local aislada de pruebas"
    monkeypatch.setattr(WhatsAppService, "send_once", lambda *args, **kwargs: None)
    marker = uuid.uuid4().hex[:12]
    with SessionLocal() as db:
        owner = Usuario(nombre="Cliente prueba", correo=f"owner-{marker}@example.test", contrasena="test", tipo=TipoUsuario.CLIENTE)
        other = Usuario(nombre="Otro cliente", correo=f"other-{marker}@example.test", contrasena="test", tipo=TipoUsuario.CLIENTE)
        vet = Usuario(nombre="Veterinaria prueba", correo=f"vet-{marker}@example.test", contrasena="test", tipo=TipoUsuario.VETERINARIO)
        admin = Usuario(nombre="Admin prueba", correo=f"admin-{marker}@example.test", contrasena="test", tipo=TipoUsuario.ADMINISTRADOR)
        db.add_all([owner, other, vet, admin])
        db.flush()
        db.add_all([Cliente(usuario_id=owner.id, telefono="999888777"), Cliente(usuario_id=other.id), Veterinario(usuario_id=vet.id, colegiatura=f"TEST-{marker}")])
        permission = db.scalar(select(PermisoRol).where(PermisoRol.rol == TipoUsuario.VETERINARIO, PermisoRol.modulo == "citas"))
        if permission is None:
            db.add(PermisoRol(rol=TipoUsuario.VETERINARIO, modulo="citas", puede_ver=True))
        service = Servicio(codigo=f"test-{marker}", nombre=f"Consulta prueba {marker}", duracion_estimada_min=30, precio_referencial=0)
        db.add(service)
        db.flush()
        pet = Mascota(cliente_id=owner.id, nombre="Mascota prueba", especie="Perro")
        db.add(pet)
        local_date = datetime.datetime.now(ZoneInfo("America/Lima")).date() + datetime.timedelta(days=8)
        while local_date.weekday() == 6:
            local_date += datetime.timedelta(days=1)
        db.add(HorarioVeterinario(veterinario_id=vet.id, dia_semana=local_date.weekday(), hora_inicio=datetime.time(8), hora_fin=datetime.time(20), activo=True))
        db.commit()
        ids = {"owner": owner.id, "other": other.id, "vet": vet.id, "admin": admin.id, "pet": pet.id, "service": service.id}

    def headers(role: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_access_token(ids[role])}"}

    with TestClient(app) as http:
        slots = http.get("/portal/disponibilidad", params={"servicio_id": ids["service"], "fecha": local_date.isoformat()})
        assert slots.status_code == 200, slots.text
        def slot_at(hour: int) -> dict:
            return next(slot for slot in slots.json() if slot["veterinario_id"] == ids["vet"] and datetime.datetime.fromisoformat(slot["fecha_hora"]).astimezone(ZoneInfo("America/Lima")).hour == hour)

        chosen = slot_at(10)
        data = {"mascota_id": ids["pet"], "servicio_id": ids["service"], "veterinario_id": ids["vet"], "fecha_hora_programada": chosen["fecha_hora"], "motivo": "Revisión preventiva", "preferencia_contacto": "llamada"}
        created = http.post("/portal/citas", headers=headers("owner"), json=data)
        assert created.status_code == 201, created.text
        booking = created.json()
        assert booking["estado"] == "pendiente_contacto"
        appointment_id = booking["id"]

        assert any(item["id"] == appointment_id for item in http.get("/portal/citas", headers=headers("owner")).json())
        assert all(item["id"] != appointment_id for item in http.get("/portal/citas", headers=headers("other")).json())
        assert http.post("/portal/citas", headers=headers("other"), json=data).status_code == 404
        assert http.get("/admin/citas", headers=headers("vet")).status_code == 403
        assert http.get("/portal/veterinario/solicitudes", headers=headers("owner")).status_code == 403
        vet_list = http.get("/portal/veterinario/solicitudes", headers=headers("vet"), params={"busqueda": marker})
        assert vet_list.status_code == 200, vet_list.text
        assert any(item["id"] == appointment_id and item["motivo"] == data["motivo"] and item["telefono_contacto"] == "999888777" for item in vet_list.json())

        def admin_list(**params: str):
            result = http.get("/admin/citas", headers=headers("admin"), params=params)
            assert result.status_code == 200, result.text
            return result.json()

        assert any(item["id"] == appointment_id for item in admin_list())
        assert any(item["id"] == appointment_id for item in admin_list(fecha=local_date.isoformat(), estado="pendiente_contacto"))
        assert all(item["id"] != appointment_id for item in admin_list(estado="confirmada"))
        assert all(item["id"] != appointment_id for item in admin_list(fecha=(local_date + datetime.timedelta(days=1)).isoformat()))
        assert http.patch(f"/admin/citas/{appointment_id}", headers=headers("admin"), json={"estado": "confirmada"}).status_code in (404, 405)

        followed = http.patch(f"/portal/veterinario/solicitudes/{appointment_id}", headers=headers("vet"), json={"estado": "contactando_cliente", "nota_coordinacion": "Llamada realizada"})
        assert followed.status_code == 200, followed.text
        confirmed = http.patch(f"/portal/veterinario/solicitudes/{appointment_id}", headers=headers("vet"), json={"estado": "confirmada"})
        assert confirmed.status_code == 200, confirmed.text
        assert confirmed.json()["nota_coordinacion"] == "Llamada realizada"
        assert any(item["id"] == appointment_id and item["estado"] == "confirmada" for item in admin_list(estado="confirmada"))
        with SessionLocal() as db:
            assert db.scalars(select(Cita).where(Cita.id == appointment_id)).one().estado.value == "confirmada"
            assert len(db.scalars(select(Cita).where(Cita.mascota_id == ids["pet"])).all()) == 1
        assert http.post("/portal/citas", headers=headers("owner"), json=data).status_code == 409

        another = http.post("/portal/citas", headers=headers("owner"), json={**data, "fecha_hora_programada": slot_at(11)["fecha_hora"]})
        assert another.status_code == 201, another.text
        another_id = another.json()["id"]
        propose_url = f"/portal/veterinario/solicitudes/{another_id}"
        assert http.patch(propose_url, headers=headers("vet"), json={"estado": "requiere_otro_horario", "fecha_hora_propuesta": slot_at(10)["fecha_hora"]}).status_code == 409
        proposal = http.patch(propose_url, headers=headers("vet"), json={"estado": "requiere_otro_horario", "fecha_hora_propuesta": slot_at(14)["fecha_hora"], "nota_coordinacion": "Horario alternativo"})
        assert proposal.status_code == 200, proposal.text
        assert any(item["id"] == another_id for item in admin_list(estado="requiere_otro_horario"))
        accepted = http.patch(f"/portal/citas/{another_id}/aceptar-horario", headers=headers("owner"))
        assert accepted.status_code == 200, accepted.text
        assert any(item["id"] == another_id for item in admin_list(estado="reprogramada"))

        rejected = http.post("/portal/citas", headers=headers("owner"), json={**data, "fecha_hora_programada": slot_at(15)["fecha_hora"]})
        assert rejected.status_code == 201, rejected.text
        reject_url = f"/portal/veterinario/solicitudes/{rejected.json()['id']}"
        assert http.patch(reject_url, headers=headers("vet"), json={"estado": "cancelada", "nota_coordinacion": "  "}).status_code == 422
        rejection = http.patch(reject_url, headers=headers("vet"), json={"estado": "cancelada", "nota_coordinacion": "Cliente solicitó cancelar"})
        assert rejection.status_code == 200, rejection.text
        assert any(item["id"] == rejected.json()["id"] for item in admin_list(estado="cancelada"))
