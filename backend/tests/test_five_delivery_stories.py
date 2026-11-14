"""E19: HU-006/009/010/081/084 con JWT real y SQLite aislada."""
import datetime as dt
import json
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from test_admin_clinical_flows import clinic
from test_priority_stories import operations, create_order, proof
from app.models.clinic import Caja, Cita, OrdenCobro, Producto, Servicio
from app.models.operations import AbonoOrden, MovimientoCaja
from app.models.user import PermisoRol, TipoUsuario, Usuario
from app.services.access_service import aware
from app.services.user_service import UserService


def service_data(**changes):
    return {"codigo": "consulta-nueva", "nombre": "Consulta nueva", "descripcion": "Evaluación clínica", "precio_referencial": "75.50", "duracion_estimada_min": 45, "activo": True, "tipo": "medica", "tipo_medico": "consulta_general", **changes}


def test_client_profile_updates_only_owned_data_and_survives_reload(operations):
    http, db, headers, *_ = operations
    old_admin = db.get(Usuario, 4).nombre
    response = http.patch("/auth/me", headers=headers[1], json={"nombre": "  María   Actualizada  ", "telefono": " 999888777 ", "direccion": " Av. Principal 123 "})
    assert response.status_code == 200, response.text
    assert response.json()["nombre"] == "María Actualizada"
    assert response.json()["telefono"] == "999888777"
    assert http.get("/auth/me", headers=headers[1]).json()["direccion"] == "Av. Principal 123"
    assert db.get(Usuario, 4).nombre == old_admin and db.get(Usuario, 1).tipo == TipoUsuario.CLIENTE
    cleared = http.patch("/auth/me", headers=headers[1], json={"nombre": "María Actualizada", "telefono": "", "direccion": "   "})
    assert cleared.status_code == 200 and cleared.json()["telefono"] is None and cleared.json()["direccion"] is None


@pytest.mark.parametrize("change", [{"id": 4}, {"tipo": "administrador"}, {"activo": False}, {"correo": "other@example.com"}, {"nombre": "   "}])
def test_profile_rejects_identity_role_and_invalid_name_changes(operations, change):
    http, db, headers, *_ = operations
    original = db.get(Usuario, 1).nombre
    assert http.patch("/auth/me", headers=headers[1], json={"nombre": "Nombre válido", **change}).status_code == 422
    assert db.get(Usuario, 1).nombre == original


def test_profile_requires_login_and_cannot_edit_another_user(operations):
    http, db, headers, *_ = operations
    assert http.patch("/auth/me", json={"nombre": "Nuevo nombre"}).status_code == 401
    assert http.patch("/usuarios/4", headers=headers[1], json={"nombre": "Nuevo nombre"}).status_code == 403


def test_fifth_failed_login_locks_then_expires_and_success_resets_counter(operations, monkeypatch):
    http, db, headers, *_ = operations
    from app.services import access_service
    user = db.get(Usuario, 1)
    user.contrasena = UserService(db)._hash_password("ClaveValida123"); db.commit()
    login = {"identifier": " OWNER@EXAMPLE.COM ", "password": "Incorrecta123"}
    for index in range(4):
        assert http.post("/auth/login", json=login).status_code == 401
        assert user.intentos_fallidos == index + 1 and user.bloqueado_hasta is None
    assert http.post("/auth/login", json=login).status_code == 423
    until = aware(user.bloqueado_hasta)
    assert until is not None and user.intentos_fallidos == 5
    assert http.post("/auth/login", json={**login, "password": "ClaveValida123"}).status_code == 423
    assert aware(user.bloqueado_hasta) == until  # Un reintento no prolonga el bloqueo.
    monkeypatch.setattr(access_service, "now", lambda: until + dt.timedelta(seconds=1))
    response = http.post("/auth/login", json={**login, "password": "ClaveValida123"})
    assert response.status_code == 200 and response.json()["access_token"]
    assert user.intentos_fallidos == 0 and user.bloqueado_hasta is None


def test_success_before_fifth_attempt_resets_and_unknown_email_does_not_change_accounts(operations):
    http, db, _, *_ = operations
    user = db.get(Usuario, 1); user.contrasena = UserService(db)._hash_password("ClaveValida123"); user.intentos_fallidos = 3; db.commit()
    assert http.post("/auth/login", json={"identifier": user.correo, "password": "ClaveValida123"}).status_code == 200
    assert user.intentos_fallidos == 0
    assert http.post("/auth/login", json={"identifier": "unknown@example.com", "password": "Invalid123"}).status_code == 401
    assert user.intentos_fallidos == 0


def test_cashier_deactivation_preserves_register_and_revokes_old_sessions_even_after_reactivation(operations):
    http, db, headers, *_ = operations
    cashier = db.get(Usuario, 5); cashier.contrasena = UserService(db)._hash_password("CajaValida123"); db.commit()
    register = db.scalar(select(Caja).where(Caja.cajero_id == 5))
    version = cashier.version_sesion
    assert http.patch("/usuarios/5/estado", headers=headers[4], json={"activo": False}).status_code == 200
    assert db.get(Caja, register.id) is not None and cashier.version_sesion == version + 1
    assert http.get("/caja/resumen", headers=headers[5]).status_code == 401
    assert http.post("/auth/login", json={"identifier": cashier.correo, "password": "CajaValida123"}).status_code == 403
    assert http.patch("/usuarios/5/estado", headers=headers[4], json={"activo": False}).status_code == 200
    assert cashier.version_sesion == version + 1
    assert http.patch("/usuarios/5/estado", headers=headers[4], json={"activo": True}).status_code == 200
    assert http.get("/caja/resumen", headers=headers[5]).status_code == 401
    token = http.post("/auth/login", json={"identifier": cashier.correo, "password": "CajaValida123"}).json()["access_token"]
    assert http.get("/caja/resumen", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_deactivation_requires_permission_and_rejects_self_and_clients(operations):
    http, db, headers, *_ = operations
    assert http.patch("/usuarios/4/estado", headers=headers[4], json={"activo": False}).status_code == 409
    assert http.patch("/usuarios/1/estado", headers=headers[4], json={"activo": False}).status_code == 422
    assert http.patch("/usuarios/2/estado", headers=headers[1], json={"activo": False}).status_code == 403
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="usuarios", puede_ver=True, puede_editar=False)); db.commit()
    assert http.patch("/usuarios/2/estado", headers=headers[4], json={"activo": False}).status_code == 403
    assert db.get(Usuario, 2).activo


def test_installments_keep_balance_and_stock_then_settle_exactly_once(operations):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    payment = {"monto": "10.00", "medio": "efectivo", "canal": "caja", "clave_idempotencia": str(uuid4())}
    url = f"/operaciones/ordenes/{order['id']}/abonos"
    response = http.post(url, headers=headers[5], json=payment)
    assert response.status_code == 201, response.text
    assert response.json()["estado"] == "parcial" and response.json()["saldo"] == 30
    assert http.post(url, headers=headers[5], json=payment).json()["saldo"] == 30
    assert len(db.scalars(select(MovimientoCaja)).all()) == 1
    assert db.get(Producto, product).stock_actual == 10
    assert db.scalars(select(OrdenCobro)).all() == []
    assert http.post(url, headers=headers[5], json={**payment, "monto": "31.00", "clave_idempotencia": str(uuid4())}).status_code == 422
    final = {**payment, "monto": "30.00", "clave_idempotencia": str(uuid4())}
    paid = http.post(url, headers=headers[5], json=final).json()
    assert paid["estado"] == "pagada" and paid["saldo"] == 0 and paid["venta_id"]
    assert http.post(url, headers=headers[5], json=final).json()["venta_id"] == paid["venta_id"]
    assert db.get(Producto, product).stock_actual == 8
    assert len(db.scalars(select(OrdenCobro)).all()) == 1
    assert sum(row.monto for row in db.scalars(select(MovimientoCaja)).all()) == 40
    assert db.scalar(select(Caja).where(Caja.cajero_id == 5)).total_ingresos_validados == 40


def test_digital_partial_proof_requires_validation_before_reducing_balance(operations):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    data = {"monto": "10.00", "medio": "yape", "canal": "web", "clave_idempotencia": str(uuid4())}
    response = http.post(f"/operaciones/ordenes/{order['id']}/comprobantes", headers=headers[1], data={"datos": json.dumps(data)}, files={"archivo": ("proof.png", proof(), "image/png")})
    assert response.status_code == 201 and response.json()["saldo"] == 40
    payment = response.json()["abonos"][0]
    assert http.post(f"/operaciones/pagos/{payment['id']}/validar", headers=headers[1]).status_code == 403
    validated = http.post(f"/operaciones/pagos/{payment['id']}/validar", headers=headers[5])
    assert validated.status_code == 200 and validated.json()["saldo"] == 30
    assert http.post(f"/operaciones/pagos/{payment['id']}/validar", headers=headers[5]).json()["saldo"] == 30
    assert len(db.scalars(select(MovimientoCaja)).all()) == 1 and len(db.scalars(select(AbonoOrden)).all()) == 1


def test_services_create_edit_and_deactivate_share_portal_cashier_and_preserve_history(operations):
    http, db, headers, start, _ = operations
    created = http.post("/admin/operaciones/servicios", headers=headers[4], json=service_data())
    assert created.status_code == 201, created.text
    id = created.json()["id"]
    assert next(row for row in http.get("/portal/servicios").json() if row["id"] == id)["duracion_estimada_min"] == 45
    original_end = db.get(Cita, 1).fecha_hora_fin_programada
    existing = service_data(codigo="consulta-test", nombre="Consulta", precio_referencial="50.00", duracion_estimada_min=30)
    order, _ = create_order(http, headers[5], None, detalles=[{"servicio_id": 1, "cantidad": 1}])
    assert http.put("/admin/operaciones/servicios/1", headers=headers[4], json={**existing, "precio_referencial": "90.00", "duracion_estimada_min": 60}).status_code == 200
    assert db.get(Cita, 1).fecha_hora_fin_programada == original_end
    catalog = http.get("/operaciones/catalogo", headers=headers[5]).json()
    assert Decimal(next(row for row in catalog["servicios"] if row["id"] == 1)["precio"]) == 90
    assert Decimal(http.get(f"/operaciones/ordenes/{order['id']}", headers=headers[5]).json()["total"]) == 50
    assert http.put(f"/admin/operaciones/servicios/{id}", headers=headers[4], json=service_data(activo=False)).status_code == 200
    assert id not in {row["id"] for row in http.get("/portal/servicios").json()}
    assert id not in {row["id"] for row in http.get("/operaciones/catalogo", headers=headers[5]).json()["servicios"]}
    assert http.get("/portal/disponibilidad", params={"servicio_id": id, "fecha": start.date().isoformat()}).status_code == 404
    booking = {"mascota_id": 1, "servicio_id": id, "veterinario_id": 2, "fecha_hora_programada": (start + dt.timedelta(hours=4)).isoformat(), "es_urgente": False}
    assert http.post("/portal/citas", headers=headers[1], json=booking).status_code == 404
    assert db.get(Servicio, id) is not None and db.get(Cita, 1) is not None


def test_service_management_uses_appointments_permission_and_rejects_duplicates(operations):
    http, db, headers, *_ = operations
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="usuarios", puede_ver=False)); db.commit()
    assert http.get("/admin/operaciones/servicios", headers=headers[4]).status_code == 200
    assert http.post("/admin/operaciones/servicios", headers=headers[4], json=service_data()).status_code == 201
    assert http.post("/admin/operaciones/servicios", headers=headers[4], json=service_data()).status_code == 409
    assert http.post("/admin/operaciones/servicios", headers=headers[4], json=service_data(codigo="bad", precio_referencial=-1)).status_code == 422
    assert http.put("/admin/operaciones/servicios/1", headers=headers[4], json=service_data(tipo="estetica")).status_code == 409
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="citas", puede_ver=True, puede_crear=False, puede_editar=False)); db.commit()
    assert http.get("/admin/operaciones/servicios", headers=headers[4]).status_code == 200
    assert http.post("/admin/operaciones/servicios", headers=headers[4], json=service_data(codigo="another")).status_code == 403
    assert http.put("/admin/operaciones/servicios/1", headers=headers[4], json=service_data()).status_code == 403
    assert http.get("/admin/operaciones/servicios", headers=headers[5]).status_code == 403
