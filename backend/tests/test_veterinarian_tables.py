import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.clinic import AplicacionPreventiva, Cita, EstadoCita, Mascota, OrdenExamen, ProcesoAtencion, ProcesoAtencionMedica, Servicio
from app.models.user import Cliente, TipoUsuario, Usuario, Veterinario
from app.security import get_current_active_user


@pytest.fixture
def clinical_directory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def attach_schema(connection, _record):
        connection.execute("ATTACH DATABASE ':memory:' AS clinica_veterinaria")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        owner = Usuario(id=1, nombre="Propietaria", correo="owner@example.test", contrasena="hash-prueba", tipo=TipoUsuario.CLIENTE)
        vet = Usuario(id=2, nombre="Veterinaria", correo="vet@example.test", contrasena="hash-prueba", tipo=TipoUsuario.VETERINARIO)
        other = Usuario(id=3, nombre="Otro profesional", correo="other@example.test", contrasena="hash-prueba", tipo=TipoUsuario.VETERINARIO)
        db.add_all([owner, vet, other])
        db.flush()
        db.add_all([Cliente(usuario_id=1, telefono="999888777", direccion="Ayacucho"), Veterinario(usuario_id=2, colegiatura="TEST-2"), Veterinario(usuario_id=3, colegiatura="TEST-3")])
        db.add_all([Mascota(id=1, cliente_id=1, nombre="Luna", especie="Perro"), Mascota(id=2, cliente_id=1, nombre="Sin citas", especie="Gato"), Mascota(id=3, cliente_id=1, nombre="Ficha inicial", especie="Ave")])
        db.add(Servicio(id=1, codigo="CONS-TEST", nombre="Consulta", precio_referencial=50, duracion_estimada_min=30))
        db.flush()
        start = datetime.datetime(2026, 11, 1, 10, tzinfo=datetime.timezone.utc)
        for appointment_id, veterinarian_id, state in [(10, 2, EstadoCita.CONFIRMADA), (11, 2, EstadoCita.ATENDIDA), (12, 3, EstadoCita.ATENDIDA)]:
            date = start + datetime.timedelta(days=appointment_id)
            db.add(Cita(id=appointment_id, mascota_id=1, servicio_id=1, veterinario_id=veterinarian_id, fecha_hora_programada=date, fecha_hora_fin_programada=date + datetime.timedelta(minutes=30), estado=state))
        db.flush()
        for process_id, appointment_id, pet_id, veterinarian_id in [(1, 11, 1, 2), (2, None, 3, 2), (3, 12, 1, 3)]:
            db.add(ProcesoAtencion(id=process_id, cita_id=appointment_id, mascota_id=pet_id, tipo="medica", estado="cerrada", fecha_inicio=start))
            db.flush()
            db.add(ProcesoAtencionMedica(proceso_id=process_id, veterinario_id=veterinarian_id, diagnostico=f"Evaluación {process_id}"))
        db.add(OrdenExamen(id=1, proceso_id=1, veterinario_id=2, tipo="Hemograma", prioridad="rutina", estado="resultado_disponible", resultado="Valores registrados", interpretacion="Control clínico", fecha_solicitud=start))
        db.add(AplicacionPreventiva(id=1, proceso_id=1, veterinario_id=2, tipo="vacuna", producto="Vacuna de prueba", lote="LOTE-TEST", fecha_aplicacion=start.date()))
        db.commit()
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_active_user] = lambda: vet
        try:
            yield TestClient(app), db, owner
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(get_current_active_user, None)
    engine.dispose()


def test_patient_table_includes_patients_without_appointments_and_initial_records(clinical_directory):
    http, _db, _owner = clinical_directory
    response = http.get("/portal/veterinario/mascotas")
    assert response.status_code == 200, response.text
    patients = {pet["id"]: pet for pet in response.json()}
    assert set(patients) == {1, 2, 3}
    assert patients[2]["citas"] == patients[2]["atenciones"] == 0
    assert patients[3]["citas"] == 0 and patients[3]["atenciones"] == 1
    assert patients[1]["citas"] == 2 and patients[1]["atenciones"] == 1
    assert patients[1]["cliente_nombre"] == "Propietaria"
    assert patients[1]["telefono_contacto"] == "999888777"
    assert http.get("/portal/veterinario/mascotas/2").json()["nombre"] == "Sin citas"
    assert http.get("/portal/veterinario/mascotas/999").status_code == 404


def test_clinical_table_includes_initial_records_and_respects_veterinarian_scope(clinical_directory):
    http, _db, _owner = clinical_directory
    response = http.get("/portal/veterinario/atenciones")
    assert response.status_code == 200, response.text
    records = {record["id"]: record for record in response.json()}
    assert set(records) == {1, 2}
    assert records[2]["cita_id"] is None
    assert records[2]["servicio_nombre"] == "Ficha inicial"
    assert records[2]["mascota"]["nombre"] == "Ficha inicial"
    assert records[1]["diagnostico"] == "Evaluación 1"
    assert records[1]["cliente_correo"] == "owner@example.test"
    assert records[1]["ordenes_examen"][0]["resultado"] == "Valores registrados"
    assert records[1]["aplicaciones_preventivas"][0]["lote"] == "LOTE-TEST"


def test_veterinarian_directory_does_not_silently_cut_off_clients_after_200(clinical_directory):
    http, db, _owner = clinical_directory
    db.add_all(Usuario(id=100 + i, nombre=f"Cliente {i:03}", correo=f"client-{i}@example.test", contrasena="hash-prueba", tipo=TipoUsuario.CLIENTE) for i in range(205))
    db.commit()
    response = http.get("/portal/veterinario/clientes")
    assert response.status_code == 200, response.text
    assert len(response.json()) == 206
    assert any(client["correo"] == "client-204@example.test" for client in response.json())


def test_client_cannot_read_veterinarian_tables(clinical_directory):
    http, _db, owner = clinical_directory
    app.dependency_overrides[get_current_active_user] = lambda: owner
    for path in ("/portal/veterinario/mascotas", "/portal/veterinario/mascotas/1", "/portal/veterinario/atenciones"):
        assert http.get(path).status_code == 403
