"""Flujos HTTP con datos aislados para los paneles administrativo y clínico."""

import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import BigInteger, create_engine, event, select
from sqlalchemy.ext.compiler import compiles, deregister
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.clinic import (
    BloqueoHorario, CategoriaProducto, Cita, EstadoCita, HorarioVeterinario,
    Mascota, Notificacion, Producto, Proveedor, Servicio, ServicioMedico,
)
from app.models.user import Cliente, TipoUsuario, Usuario, Veterinario
from app.models.operations import Sucursal, UnidadMedida
from app.security import get_current_active_user


@pytest.fixture
def clinic():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def attach_schema(connection, _record):
        connection.execute("ATTACH DATABASE ':memory:' AS clinica_veterinaria")
        connection.execute("PRAGMA foreign_keys=ON")

    # SQLite solo autogenera claves con INTEGER; la aplicación usa IDENTITY en PostgreSQL.
    compiles(BigInteger, "sqlite")(lambda _type, _compiler, **_kw: "INTEGER")
    try:
        Base.metadata.create_all(engine)
    finally:
        deregister(BigInteger)

    with Session(engine) as db:
        db.add(Sucursal(id=1, nombre="Sede de pruebas"))
        db.add_all([UnidadMedida(codigo=code, nombre=name, dimension=dimension, factor_base=factor, fraccionable=fractional) for code, name, dimension, factor, fractional in [("unidad", "Unidad", "conteo", 1, False), ("kg", "Kilogramo", "masa", 1000, True), ("g", "Gramo", "masa", 1, True), ("ml", "Mililitro", "volumen", 1, True)]])
        db.commit()
        owner = Usuario(id=1, nombre="María Pérez", correo="owner@example.com", contrasena="hash", tipo=TipoUsuario.CLIENTE)
        vet = Usuario(id=2, nombre="Dra. Ana", correo="vet@example.com", contrasena="hash", tipo=TipoUsuario.VETERINARIO)
        other_vet = Usuario(id=3, nombre="Dr. Luis", correo="other@example.com", contrasena="hash", tipo=TipoUsuario.VETERINARIO)
        admin = Usuario(id=4, nombre="Administración", correo="admin@example.com", contrasena="hash", tipo=TipoUsuario.ADMINISTRADOR)
        db.add_all([owner, vet, other_vet, admin])
        db.flush()
        db.add_all([Cliente(usuario_id=1, telefono="999888777"), Veterinario(usuario_id=2, colegiatura="TEST-2"), Veterinario(usuario_id=3, colegiatura="TEST-3")])
        db.flush()
        db.add(Mascota(id=1, cliente_id=1, nombre="Luna", especie="Perro"))
        db.add(Servicio(id=1, codigo="consulta-test", nombre="Consulta", precio_referencial=50, duracion_estimada_min=30))
        db.flush()
        db.add(ServicioMedico(servicio_id=1, tipo_atencion_medica="consulta_general"))
        start = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=8)).replace(hour=15, minute=0, second=0, microsecond=0)
        while start.weekday() == 6:
            start += datetime.timedelta(days=1)
        for vet_id in (2, 3):
            db.add(HorarioVeterinario(veterinario_id=vet_id, dia_semana=start.weekday(), hora_inicio=datetime.time(8), hora_fin=datetime.time(20), activo=True))
        db.add_all([
            Cita(id=1, mascota_id=1, servicio_id=1, veterinario_id=2, fecha_hora_programada=start, fecha_hora_fin_programada=start + datetime.timedelta(minutes=30), estado=EstadoCita.PENDIENTE_CONTACTO),
            Cita(id=2, mascota_id=1, servicio_id=1, veterinario_id=3, fecha_hora_programada=start + datetime.timedelta(hours=1), fecha_hora_fin_programada=start + datetime.timedelta(hours=1, minutes=30), estado=EstadoCita.CONFIRMADA),
        ])
        db.commit()
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_active_user] = lambda: admin
        try:
            yield TestClient(app), db, start, vet
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(get_current_active_user, None)
    engine.dispose()


def test_admin_confirms_reassigns_and_notifies_without_creating_a_second_appointment(clinic):
    http, db, start, _vet = clinic
    assert {item["id"] for item in http.get("/admin/citas/veterinarios").json()} == {2, 3}
    confirmed = http.patch("/admin/citas/1", json={"estado": "confirmada"})
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["estado"] == "confirmada"
    changed = http.patch("/admin/citas/1", json={
        "estado": "reprogramada", "veterinario_id": 3,
        "fecha_hora_programada": (start + datetime.timedelta(hours=4)).isoformat(),
        "nota_coordinacion": "Coordinado con la propietaria",
    })
    assert changed.status_code == 200, changed.text
    data = changed.json()
    assert data["veterinario_id"] == 3 and data["veterinario_nombre"] == "Dr. Luis"
    assert datetime.datetime.fromisoformat(data["fecha_hora_fin_programada"]) - datetime.datetime.fromisoformat(data["fecha_hora_programada"]) == datetime.timedelta(minutes=30)
    assert len(db.scalars(select(Cita)).all()) == 2
    assert {item.usuario_id for item in db.scalars(select(Notificacion)).all()} == {1, 2, 3}


def test_admin_cannot_overlap_a_booking_or_use_a_blocked_time(clinic):
    http, db, start, _vet = clinic
    response = http.patch("/admin/citas/1", json={"veterinario_id": 3, "fecha_hora_programada": (start + datetime.timedelta(hours=1, minutes=15)).isoformat()})
    assert response.status_code == 409, response.text
    assert db.get(Cita, 1).veterinario_id == 2
    db.add(BloqueoHorario(veterinario_id=2, fecha_hora_inicio=start + datetime.timedelta(hours=3), fecha_hora_fin=start + datetime.timedelta(hours=4), motivo="Bloqueado"))
    db.commit()
    response = http.patch("/admin/citas/1", json={"fecha_hora_programada": (start + datetime.timedelta(hours=3)).isoformat()})
    assert response.status_code == 422, response.text


@pytest.mark.parametrize("payload", [
    {"estado": None}, {"fecha_hora_programada": None}, {"estado": "inventado"},
    {"fecha_hora_programada": "2030-01-01T10:00:00"}, {"estado": "atendida"},
    {"estado": "confirmada", "veterinario_id": None}, {"veterinario_id": 999},
    {"estado": "cancelada", "nota_coordinacion": "  "}, {"estado": "no_asistio"},
])
def test_admin_rejects_invalid_appointment_updates(clinic, payload):
    http, _db, _start, _vet = clinic
    response = http.patch("/admin/citas/1", json=payload)
    assert response.status_code == 422, response.text


def test_categories_persist_and_cannot_be_removed_while_in_use(clinic):
    http, db, _start, _vet = clinic
    created = http.post("/admin/categorias", json={"nombre": "  Alimentos  "})
    assert created.status_code == 201, created.text
    category_id = created.json()["id"]
    assert created.json()["nombre"] == "Alimentos"
    assert http.post("/admin/categorias", json={"nombre": "Alimentos"}).status_code == 409
    assert http.post("/admin/categorias", json={"nombre": "  "}).status_code == 422
    assert http.patch(f"/admin/categorias/{category_id}", json={"nombre": "Nutrición"}).status_code == 200
    db.add(Proveedor(id=1, razon_social="Proveedor de prueba"))
    db.flush()
    db.add(Producto(id=1, categoria_id=category_id, proveedor_id=1, sku="TEST-1", nombre="Alimento", precio_venta=10, stock_actual=4))
    db.commit()
    assert http.get("/admin/categorias").json()[0]["productos"] == 1
    assert http.delete(f"/admin/categorias/{category_id}").status_code == 409
    empty = http.post("/admin/categorias", json={"nombre": "Vacía"}).json()["id"]
    assert http.delete(f"/admin/categorias/{empty}").status_code == 204


def test_settings_are_validated_and_persist_between_requests(clinic):
    http, _db, _start, _vet = clinic
    initial = http.get("/admin/configuracion")
    assert initial.status_code == 200, initial.text
    settings = {**initial.json(), "nombre": "Clínica de prueba", "correo": "clinica@example.com", "umbral_stock_bajo": 12, "alertas_stock": False}
    saved = http.patch("/admin/configuracion", json=settings)
    assert saved.status_code == 200, saved.text
    assert http.get("/admin/configuracion").json() == saved.json()
    for invalid in ({"umbral_stock_bajo": -1}, {"correo": "no-es-un-correo"}, {"nombre": "  "}):
        assert http.patch("/admin/configuracion", json={**settings, **invalid}).status_code == 422


def test_admin_reads_only_own_notifications_and_returns_the_created_item(clinic):
    http, db, _start, _vet = clinic
    db.add(Notificacion(id=1, usuario_id=1, tipo="cita", titulo="Para cliente", mensaje="Aviso al cliente"))
    db.add(Notificacion(id=2, usuario_id=4, tipo="sistema", titulo="Para admin", mensaje="Aviso administrativo"))
    db.commit()
    assert [item["id"] for item in http.get("/admin/notificaciones").json()] == [2]
    created = http.post("/admin/notificaciones", json={"usuario_id": 1, "tipo": "cita", "titulo": "Nuevo aviso", "mensaje": "Mensaje nuevo"})
    assert created.status_code == 201, created.text
    assert created.json()["titulo"] == "Nuevo aviso" and created.json()["usuario_nombre"] == "María Pérez"
    assert http.post("/admin/notificaciones/marcar-leidas").status_code == 204
    assert db.get(Notificacion, 2).leida is True
    assert db.get(Notificacion, 1).leida is False
    assert http.get("/admin/notificaciones", params={"no_leidas": True}).json() == []


def test_partial_clinical_saves_preserve_data_and_closing_updates_the_appointment(clinic):
    http, db, _start, vet = clinic
    app.dependency_overrides[get_current_active_user] = lambda: vet
    response = http.patch("/portal/veterinario/solicitudes/1/atencion", json={"estado": "en_atencion", "diagnostico": "Control", "peso": "4.50"})
    assert response.status_code == 422  # La cita todavía no está confirmada.
    db.get(Cita, 1).estado = EstadoCita.CONFIRMADA
    db.commit()
    response = http.patch("/portal/veterinario/solicitudes/1/atencion", json={"estado": "en_atencion", "diagnostico": "Control", "peso": "4.50"})
    assert response.status_code == 200, response.text
    record_id = response.json()["id"]
    updated = http.patch("/portal/veterinario/solicitudes/1/atencion", json={"estado": "en_atencion", "tratamiento": "Reposo"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["diagnostico"] == "Control" and updated.json()["peso"] == "4.50"
    cleared = http.patch("/portal/veterinario/solicitudes/1/atencion", json={"estado": "en_atencion", "peso": None})
    assert cleared.json()["peso"] is None and cleared.json()["tratamiento"] == "Reposo"
    closed = http.patch(f"/portal/veterinario/atenciones/{record_id}/estado", json={"estado": "cerrada"})
    assert closed.status_code == 200, closed.text
    assert db.get(Cita, 1).estado == EstadoCita.ATENDIDA
    admin = db.get(Usuario, 4)
    app.dependency_overrides[get_current_active_user] = lambda: admin
    records = http.get("/admin/historial-clinico")
    assert records.status_code == 200, records.text
    assert records.json()[0]["mascota"]["nombre"] == "Luna"
    assert records.json()[0]["cliente_nombre"] == "María Pérez"
    assert records.json()[0]["tratamiento"] == "Reposo"
    assert http.patch("/admin/citas/1", json={"estado": "confirmada"}).status_code == 409


def test_veterinarian_can_register_a_pet_with_blank_optional_date_and_weight(clinic):
    http, _db, _start, vet = clinic
    app.dependency_overrides[get_current_active_user] = lambda: vet
    response = http.post("/portal/veterinario/clientes/1/mascotas", json={"nombre": "Michi", "especie": "Gato", "fecha_nacimiento": "", "peso_actual": ""})
    assert response.status_code == 201, response.text
    assert response.json()["fecha_nacimiento"] is None and response.json()["peso_actual"] is None
    assert http.post("/portal/veterinario/clientes/1/mascotas", json={"nombre": "  ", "especie": "Gato"}).status_code == 422
