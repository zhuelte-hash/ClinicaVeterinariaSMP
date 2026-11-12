"""Aceptación HTTP de las historias cerradas en la actualización del informe."""

import datetime
from decimal import Decimal
from io import BytesIO

import pytest
from PIL import Image
from sqlalchemy import select

from test_admin_clinical_flows import clinic
from app.config import get_settings
from app.main import app
from app.models.clinic import AjusteInventario, Caja, CategoriaProducto, Cita, EstadoCita, Mascota, Producto, Proveedor
from app.models.user import Cajero, TipoUsuario, Usuario
from app.routers import appointments
from app.security import get_current_active_user
from app.services.cashier_service import CashierService


def product(http, db, **changes):
    db.add_all([CategoriaProducto(id=1, nombre="Alimentos"), Proveedor(id=1, razon_social="Proveedor inicial")])
    db.commit()
    response = http.post("/admin/productos", json={
        "categoria_id": 1, "proveedor_id": 1, "sku": "TEST-HU-15", "nombre": "Alimento adulto",
        "precio_venta": "42.90", "stock_actual": 10, "descripcion": "Alimento completo para adultos.",
        "especies": [" perro ", "Perro"], **changes,
    })
    assert response.status_code == 201, response.text
    return response.json()


def test_product_detail_description_species_and_price_filters_are_persisted(clinic):
    http, db, _start, _vet = clinic
    item = product(http, db)
    detail = http.get(f"/catalogo/productos/{item['id']}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["descripcion"] == "Alimento completo para adultos."
    assert detail.json()["especies"] == ["Perro"]
    assert detail.json()["stock_actual"] == 10
    assert len(http.get("/catalogo/productos", params={"especie": "perro", "precio_min": 40, "precio_max": 43}).json()) == 1
    assert http.get("/catalogo/productos", params={"especie": "Gato"}).json() == []
    assert http.get("/catalogo/productos", params={"precio_min": 43}).json() == []
    assert http.get("/catalogo/productos", params={"precio_min": 50, "precio_max": 40}).status_code == 422
    assert http.get("/catalogo/productos", params={"precio_min": -1}).status_code == 422
    assert http.delete(f"/admin/productos/{item['id']}").status_code == 204
    assert http.get(f"/catalogo/productos/{item['id']}").status_code == 404


def test_service_details_use_the_booking_catalog(clinic):
    http, _db, _start, _vet = clinic
    item = http.get("/portal/servicios").json()[0]
    assert item["precio_referencial"] == "50.00"
    assert item["duracion_estimada_min"] == 30
    assert item["codigo"] == "consulta-test"


def test_suppliers_can_be_created_edited_and_associated_to_existing_products(clinic):
    http, db, _start, _vet = clinic
    item = product(http, db)
    created = http.post("/admin/proveedores", json={"razon_social": "  Distribuidora clínica  "})
    assert created.status_code == 201, created.text
    supplier_id = created.json()["id"]
    assert http.post("/admin/proveedores", json={"razon_social": "distribuidora clínica"}).status_code == 409
    assert http.post("/admin/proveedores", json={"razon_social": "  "}).status_code == 422
    assert http.patch(f"/admin/proveedores/{supplier_id}", json={"razon_social": "Distribuidora actualizada"}).status_code == 200
    assert http.patch(f"/admin/productos/{item['id']}", json={"proveedor_id": supplier_id}).status_code == 200
    rows = http.get("/admin/proveedores").json()
    assert next(row for row in rows if row["id"] == supplier_id)["productos"] == 1
    assert next(row for row in rows if row["id"] == 1)["productos"] == 0


def test_stock_adjustment_requires_reason_records_actor_and_rejects_stale_values(clinic):
    http, db, _start, _vet = clinic
    item = product(http, db)
    url = f"/admin/inventario/{item['id']}"
    assert http.patch(url, json={"stock_actual": 8}).status_code == 422
    assert http.patch(url, json={"stock_actual": 8, "stock_anterior": 10, "motivo": "  "}).status_code == 422
    changed = http.patch(url, json={"stock_actual": 8, "stock_anterior": 10, "motivo": "Merma por rotura"})
    assert changed.status_code == 200, changed.text
    row = http.get("/admin/ajustes-inventario").json()[0]
    assert (row["cantidad_anterior"], row["cantidad_nueva"], row["usuario_id"]) == (10, 8, 4)
    assert row["motivo"] == "Merma por rotura" and row["fecha"]
    assert http.patch(url, json={"stock_actual": 9, "stock_anterior": 10, "motivo": "Conteo anterior"}).status_code == 409
    assert http.patch(url, json={"stock_actual": -1, "stock_anterior": 8, "motivo": "Cantidad inválida"}).status_code == 422
    assert db.get(Producto, item["id"]).stock_actual == 8
    assert len(db.scalars(select(AjusteInventario)).all()) == 1


def test_urgent_requests_are_exposed_prioritized_and_reported_by_date_and_state(clinic):
    http, db, start, _vet = clinic
    db.get(Cita, 1).es_urgente = True
    db.commit()
    assert http.get("/admin/citas").json()[0]["id"] == 1
    assert [row["id"] for row in http.get("/admin/citas", params={"solo_urgentes": True}).json()] == [1]
    dates = {"fecha_inicial": start.date().isoformat(), "fecha_final": start.date().isoformat()}
    report = http.get("/admin/citas/reporte", params=dates)
    assert report.status_code == 200, report.text
    data = report.json()
    assert data["total"] == 2 and data["urgentes"] == 1
    assert data["por_estado"]["confirmada"] == 1 and data["por_estado"]["pendiente_contacto"] == 1
    assert sum(data["por_estado"].values()) == data["total"]
    empty_dates = {"fecha_inicial": (start.date() + datetime.timedelta(days=1)).isoformat(), "fecha_final": (start.date() + datetime.timedelta(days=1)).isoformat()}
    assert http.get("/admin/citas", params=empty_dates).json() == []
    assert http.get("/admin/citas/reporte", params=empty_dates).json()["total"] == 0
    assert http.get("/admin/citas/reporte", params={"fecha_inicial": "2030-01-02", "fecha_final": "2030-01-01"}).status_code == 422


def test_weekly_agenda_is_filtered_by_range_status_and_professional(clinic):
    http, _db, start, vet = clinic
    app.dependency_overrides[get_current_active_user] = lambda: vet
    dates = {"fecha_inicial": (start.date() - datetime.timedelta(days=2)).isoformat(), "fecha_final": (start.date() + datetime.timedelta(days=4)).isoformat(), "incluir_finalizadas": True}
    response = http.get("/portal/veterinario/solicitudes", params=dates)
    assert response.status_code == 200, response.text
    assert [row["id"] for row in response.json()] == [1]
    assert http.get("/portal/veterinario/solicitudes", params={**dates, "estado": "confirmada"}).json() == []
    assert http.get("/portal/veterinario/solicitudes", params={"fecha_inicial": (start.date() + datetime.timedelta(days=1)).isoformat()}).json() == []


@pytest.mark.parametrize("scenario", ["too_early", "arrival", "other_vet", "in_progress", "success"])
def test_manual_no_show_enforces_tolerance_ownership_and_clinical_state(clinic, scenario):
    http, db, start, vet = clinic
    appointment = db.get(Cita, 1)
    appointment.estado = EstadoCita.CONFIRMADA
    if scenario != "too_early":
        appointment.fecha_hora_programada = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=get_settings().appointment_tolerance_minutes + 1)
        appointment.fecha_hora_fin_programada = appointment.fecha_hora_programada + datetime.timedelta(minutes=30)
    if scenario == "arrival":
        appointment.fecha_hora_llegada = datetime.datetime.now(datetime.timezone.utc)
    if scenario == "other_vet":
        appointment.veterinario_id = 3
    db.commit()
    app.dependency_overrides[get_current_active_user] = lambda: vet
    if scenario == "in_progress":
        assert http.post("/portal/veterinario/solicitudes/1/atencion/iniciar").status_code == 201
    response = http.post("/portal/veterinario/solicitudes/1/inasistencia", json={"motivo": "No llegó durante la tolerancia"})
    assert response.status_code == (200 if scenario == "success" else 404 if scenario == "other_vet" else 409), response.text
    if scenario == "success":
        assert response.json()["estado"] == "no_asistio"
        assert appointment.estado_actualizado_por == vet.id
        assert appointment.nota_coordinacion == "No llegó durante la tolerancia"
        assert http.post("/portal/veterinario/solicitudes/1/inasistencia", json={"motivo": "Reintento de la solicitud"}).status_code == 200


def test_patient_master_edit_and_clinical_saves_keep_current_background_and_weight(clinic):
    http, db, _start, vet = clinic
    app.dependency_overrides[get_current_active_user] = lambda: vet
    changed = http.patch("/portal/veterinario/mascotas/1", json={"nombre": "Luna actualizada", "fecha_nacimiento": "2024-01-03", "peso_actual": "5.10", "alergias": "Penicilina", "condiciones_especiales": "Enfermedad renal"})
    assert changed.status_code == 200, changed.text
    appointment = db.get(Cita, 1)
    appointment.estado = EstadoCita.CONFIRMADA
    db.commit()
    saved = http.patch("/portal/veterinario/solicitudes/1/atencion", json={"estado": "en_atencion", "peso": "5.25", "historial_alergias": "Látex"})
    assert saved.status_code == 200, saved.text
    patient = http.get("/portal/veterinario/mascotas/1").json()
    assert patient["peso_actual"] == "5.25" and "Penicilina" in patient["alergias"] and "Látex" in patient["alergias"]
    assert patient["condiciones_especiales"] == "Enfermedad renal"
    assert http.patch("/portal/veterinario/solicitudes/1/atencion", json={"estado": "en_atencion", "historial_alergias": ""}).status_code == 200
    assert "Penicilina" in db.get(Mascota, 1).alergias
    assert http.patch("/portal/mascotas/1", json={"nombre": "  "}).status_code == 422
    assert http.patch("/portal/mascotas/1", json={"fecha_nacimiento": "2099-01-01"}).status_code == 422


def test_owner_can_edit_only_their_pets_and_photo_content_is_validated(clinic, monkeypatch, tmp_path):
    http, db, _start, _vet = clinic
    owner = db.get(Usuario, 1)
    app.dependency_overrides[get_current_active_user] = lambda: owner
    assert http.patch("/portal/mascotas/1", json={"peso_actual": "5.30", "alergias": "Polen"}).status_code == 200
    assert http.patch("/portal/mascotas/999", json={"peso_actual": "5.30"}).status_code == 404
    monkeypatch.setattr(appointments, "PET_PHOTOS_DIR", tmp_path)
    assert http.post("/portal/mascotas/1/foto", files={"archivo": ("fake.jpg", b"not an image", "image/jpeg")}).status_code == 422
    buffer = BytesIO()
    Image.new("RGB", (20, 20), "green").save(buffer, "PNG")
    response = http.post("/portal/mascotas/1/foto", files={"archivo": ("luna.png", buffer.getvalue(), "image/png")})
    assert response.status_code == 200, response.text
    assert response.json()["foto_url"].startswith("/uploads/pets/")
    assert len(list(tmp_path.glob("*.jpg"))) == 1
    other_owner = Usuario(id=5, nombre="Otro cliente", correo="other-owner@example.com", tipo=TipoUsuario.CLIENTE, contrasena="hash")
    db.add(other_owner); db.commit()
    app.dependency_overrides[get_current_active_user] = lambda: other_owner
    assert http.patch("/portal/mascotas/1", json={"alergias": "Borrado no autorizado"}).status_code == 404
    assert http.post("/portal/mascotas/1/foto", files={"archivo": ("luna.png", buffer.getvalue(), "image/png")}).status_code == 404


def test_bank_transfer_is_persisted_in_receipt_cash_totals_and_admin_filters(clinic):
    http, db, _start, _vet = clinic
    item = product(http, db)
    cashier = Usuario(id=5, nombre="Caja de prueba", correo="cashier@example.com", tipo=TipoUsuario.CAJERO, contrasena="hash")
    db.add(cashier); db.flush(); db.add(Cajero(usuario_id=5)); db.flush()
    db.add(Caja(cajero_id=5, fondo_inicial=100, estado_caja="abierta")); db.commit()
    app.dependency_overrides[get_current_active_user] = lambda: cashier
    payload = {"medio_pago": "transferencia", "items": [{"producto_id": item["id"], "cantidad": 1}]}
    response = http.post("/api/ventas", json=payload)
    assert response.status_code == 201, response.text
    receipt = response.json()
    assert receipt["medio_pago"] == "transferencia" and receipt["pagos"][0]["medio"] == "transferencia"
    register = CashierService(db).get_open_register(cashier.id)
    assert CashierService(db)._payment_totals(register.id) == (Decimal("0.00"), Decimal("42.90"))
    admin = db.get(Usuario, 4)
    app.dependency_overrides[get_current_active_user] = lambda: admin
    sales = http.get("/api/admin/ventas", params={"metodo_pago": "transferencia"})
    assert sales.status_code == 200 and sales.json()["total"] == 1
    summary = http.get("/api/admin/ventas/resumen", params={"metodo_pago": "transferencia"})
    assert summary.status_code == 200 and Decimal(str(summary.json()["total_ventas"])) == Decimal("42.90")


def test_client_cannot_modify_suppliers_or_inventory(clinic):
    http, db, _start, _vet = clinic
    owner = db.get(Usuario, 1)
    app.dependency_overrides[get_current_active_user] = lambda: owner
    assert http.post("/admin/proveedores", json={"razon_social": "No autorizado"}).status_code == 403
    assert http.patch("/admin/inventario/1", json={"stock_actual": 2, "stock_anterior": 1, "motivo": "No autorizado"}).status_code == 403
    assert http.get("/admin/citas/reporte", params={"fecha_inicial": "2026-01-01", "fecha_final": "2026-12-31"}).status_code == 403
