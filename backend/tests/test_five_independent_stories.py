"""HU-040/041/059/079/119: aceptación HTTP/JWT sin proveedores externos."""
import datetime as dt
from decimal import Decimal
from io import BytesIO

from pypdf import PdfReader
import pytest
from sqlalchemy import select

from test_admin_clinical_flows import clinic
from test_priority_stories import operations, create_order
from app.models.clinic import AplicacionPreventiva, Caja, Cita, EstadoCita, Mascota, Producto, ProcesoAtencion
from app.models.operations import EventoCita, Sucursal
from app.models.user import Cajero, Cliente, PermisoRol, TipoUsuario, Usuario


def test_history_records_actual_changes_authors_and_cancellation_without_duplicates(operations):
    http, db, headers, start, _ = operations
    url = "/admin/operaciones/citas/1/historial"
    original = http.get(url, headers=headers[4]).json()
    for hour in (0.5, 1):
        response = http.patch("/admin/citas/1", headers=headers[4], json={"estado": "reprogramada", "fecha_hora_programada": (start + dt.timedelta(hours=hour)).isoformat(), "nota_coordinacion": f"Cambio {hour}"})
        assert response.status_code == 200, response.text
    assert http.patch("/admin/citas/1", headers=headers[4], json={"estado": "cancelada", "nota_coordinacion": "Solicitud del propietario"}).status_code == 200
    data = http.get(url, headers=headers[4]).json()
    assert data["reprogramaciones"] == 2 and data["cancelaciones"] == 1
    assert data["cantidad"] == original["cantidad"] + 3
    assert all(row["autor"] == "Administración" and row["usuario_id"] == 4 for row in data["eventos"][-3:])
    assert data["eventos"][-1]["motivo"] == "Solicitud del propietario"
    assert data["eventos"][-3]["anterior"]["fecha_hora_programada"]
    assert http.patch("/admin/citas/1", headers=headers[4], json={"estado": "cancelada", "nota_coordinacion": "Repetido"}).status_code == 409
    assert http.get(url, headers=headers[4]).json() == data


def test_same_instant_and_reassignment_do_not_count_as_rescheduling(operations):
    http, _db, headers, start, _ = operations
    url = "/admin/operaciones/citas/1/historial"
    before = http.get(url, headers=headers[4]).json()
    response = http.patch("/admin/citas/1", headers=headers[4], json={"fecha_hora_programada": start.astimezone(dt.timezone(dt.timedelta(hours=-5))).isoformat()})
    assert response.status_code == 200, response.text
    assert http.get(url, headers=headers[4]).json()["cantidad"] == before["cantidad"]
    changed = http.patch("/admin/citas/1", headers=headers[4], json={"veterinario_id": 3})
    assert changed.status_code == 200, changed.text
    after = http.get(url, headers=headers[4]).json()
    assert after["reprogramaciones"] == 0 and after["eventos"][-1]["accion"] == "reasignada"


@pytest.mark.parametrize("action", ["update", "delete"])
def test_history_cannot_be_modified_by_orm(operations, action):
    _http, db, *_ = operations
    row = db.scalar(select(EventoCita).where(EventoCita.cita_id == 1))
    if action == "update":
        row.motivo = "Alteración"
    else:
        db.delete(row)
    with pytest.raises(ValueError, match="inmutable"):
        db.commit()
    db.rollback()


def test_calendar_range_uses_peru_month_boundaries_and_all_states(operations):
    http, db, headers, *_ = operations
    for id, date, state in [(1, dt.datetime(2026, 12, 1, 4, 59), EstadoCita.CANCELADA), (2, dt.datetime(2026, 12, 1, 5), EstadoCita.CONFIRMADA)]:
        row = db.get(Cita, id); row.fecha_hora_programada = date.replace(tzinfo=dt.timezone.utc); row.estado = state
    db.commit()
    response = http.get("/admin/citas", headers=headers[4], params={"fecha_inicial": "2026-11-01", "fecha_final": "2026-11-30"})
    assert response.status_code == 200, response.text
    assert [row["id"] for row in response.json()] == [1]
    assert response.json()[0]["estado"] == "cancelada"
    assert response.json()[0]["veterinario_nombre"] == "Dra. Ana"


@pytest.mark.parametrize("path", ["/admin/operaciones/citas/1/historial", "/admin/citas", "/admin/operaciones/cierres?desde=2026-01-01&hasta=2026-01-31", "/admin/operaciones/valorizacion"])
def test_admin_reports_deny_client_and_guest(operations, path):
    http, _db, headers, *_ = operations
    assert http.get(path).status_code == 401
    assert http.get(path, headers=headers[1]).status_code == 403


def test_appointment_history_is_scoped_and_not_editable_via_http(operations):
    http, db, headers, *_ = operations
    db.add(Sucursal(id=2, nombre="Segunda")); db.commit()
    url = "/admin/operaciones/citas/1/historial"
    assert http.get(url, headers={**headers[4], "X-Sucursal-ID": "2"}).status_code == 404
    assert http.get("/admin/operaciones/citas/999/historial", headers=headers[4]).status_code == 404
    assert http.put(url, headers=headers[4], json={}).status_code == 405
    assert http.delete(url, headers=headers[4]).status_code == 405


def test_vaccination_pdf_is_specific_private_and_contains_attending_vet(operations):
    http, db, headers, *_ = operations
    process = ProcesoAtencion(mascota_id=1, tipo="medica", estado="cerrada", notas_privadas="NO PUBLICAR NOTA")
    db.add(process); db.flush()
    for kind, name in [("vacuna", "Rabia anual"), ("desparasitacion", "ANTIPARASITARIO EXCLUIDO")]:
        db.add(AplicacionPreventiva(proceso_id=process.id, veterinario_id=2, tipo=kind, producto=name, lote="LOTE-123", fecha_aplicacion=dt.date(2026, 11, 1), proxima_fecha=dt.date(2027, 11, 1)))
    db.commit()
    response = http.get("/portal/mascotas/1/carnet", headers=headers[1])
    assert response.status_code == 200 and response.headers["content-type"] == "application/pdf"
    assert response.headers["cache-control"] == "private, no-store"
    assert 'filename="carnet-1.pdf"' in response.headers["content-disposition"]
    text = "".join(page.extract_text() for page in PdfReader(BytesIO(response.content)).pages)
    assert all(word in text for word in ["Luna", "Rabia anual", "LOTE-123", "2027-11-01", "Dra. Ana", "María Pérez"])
    assert "ANTIPARASITARIO EXCLUIDO" not in text and "NO PUBLICAR NOTA" not in text


def test_vaccination_pdf_empty_ownership_and_permissions(operations):
    http, db, headers, *_ = operations
    response = http.get("/portal/mascotas/1/carnet", headers=headers[1])
    assert "Sin vacunas registradas" in PdfReader(BytesIO(response.content)).pages[0].extract_text()
    db.add(Cliente(usuario_id=3)); db.add(Mascota(id=2, cliente_id=3, nombre="Ajena", especie="Gato")); db.commit()
    assert http.get("/portal/mascotas/2/carnet", headers=headers[1]).status_code == 404
    assert http.get("/portal/mascotas/999/carnet", headers=headers[1]).status_code == 404
    assert http.get("/portal/mascotas/1/carnet", headers=headers[2]).status_code == 403
    db.add(PermisoRol(rol=TipoUsuario.CLIENTE, modulo="mascotas", puede_ver=False)); db.commit()
    assert http.get("/portal/mascotas/1/carnet", headers=headers[1]).status_code == 403


def test_closures_consolidate_all_cashiers_peru_days_and_detail_without_double_payment(operations):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    response = http.post(f"/operaciones/ordenes/{order['id']}/abonos", headers=headers[5], json={"monto": "40", "medio": "efectivo", "canal": "caja", "clave_idempotencia": "closure-cash"})
    assert response.status_code == 201, response.text
    register = db.scalar(select(Caja).where(Caja.cajero_id == 5))
    register.estado_caja = "cerrada"; register.fecha_cierre = dt.datetime(2026, 11, 2, 4, 59, tzinfo=dt.timezone.utc)
    register.efectivo_contado = 138; register.diferencia = -2
    db.add(Usuario(id=6, nombre="Segunda caja", correo="cashier2@example.test", contrasena="hash", tipo=TipoUsuario.CAJERO)); db.flush(); db.add(Cajero(usuario_id=6)); db.flush()
    db.add(Caja(cajero_id=6, fondo_inicial=50, estado_caja="cerrada", fecha_cierre=dt.datetime(2026, 11, 1, 18, tzinfo=dt.timezone.utc), efectivo_contado=51, diferencia=1))
    db.commit()
    response = http.get("/admin/operaciones/cierres", headers=headers[4], params={"desde": "2026-11-01", "hasta": "2026-11-01"})
    assert response.status_code == 200, response.text
    data = response.json(); assert data["cantidad"] == 2 and len(data["por_dia"]) == 1
    assert Decimal(str(data["totales"]["ingresos_efectivo"])) == 40
    assert Decimal(str(data["totales"]["efectivo_esperado"])) == 190
    assert Decimal(str(data["diferencia_total"])) == -1
    assert data["por_dia"][0]["fecha"] == "2026-11-01"
    detail = http.get(f"/admin/operaciones/cierres/{register.id}", headers=headers[4]).json()
    assert len(detail["movimientos"]) == 1 and Decimal(str(detail["movimientos"][0]["monto"])) == 40
    filtered = http.get("/admin/operaciones/cierres", headers=headers[4], params={"desde": "2026-11-01", "hasta": "2026-11-01", "cajero_id": 6}).json()
    assert filtered["cantidad"] == 1 and filtered["cierres"][0]["cajero"] == "Segunda caja"


@pytest.mark.parametrize("query", ["desde=2026-12-01&hasta=2026-11-01", "desde=2024-01-01&hasta=2026-01-01", "desde=2026-01-01&hasta=2026-01-31&cajero_id=-1"])
def test_closures_reject_invalid_ranges_and_cashier(operations, query):
    http, _db, headers, *_ = operations
    assert http.get("/admin/operaciones/cierres?" + query, headers=headers[4]).status_code == 422


def test_closures_empty_branch_and_detail_not_open(operations):
    http, db, headers, *_ = operations
    db.add(Sucursal(id=2, nombre="Segunda")); db.commit()
    response = http.get("/admin/operaciones/cierres?desde=2026-01-01&hasta=2026-01-31", headers={**headers[4], "X-Sucursal-ID": "2"})
    assert response.status_code == 200 and response.json()["cantidad"] == 0
    assert response.json()["totales"]["diferencia"] == 0
    assert http.get("/admin/operaciones/cierres/1", headers=headers[4]).status_code == 404


def test_valuation_uses_purchase_average_fractional_inactive_and_missing_cost(operations):
    http, db, headers, _, product = operations
    item = db.get(Producto, product); item.costo_unitario = Decimal("2"); db.commit()
    received = http.post("/admin/operaciones/compras", headers=headers[4], json={"proveedor_id": 1, "documento": "VAL-1", "detalles": [{"producto_id": product, "cantidad": 10, "costo_unitario": 4, "lote": "VAL-LOT"}]})
    assert received.status_code == 201, received.text
    item.activo = False
    db.add(Producto(categoria_id=1, proveedor_id=1, sku="FRAC", nombre="Fracción", precio_venta=100, stock_actual=Decimal("1.125"), costo_unitario=Decimal("2.0044"), unidad_medida="kg", fraccionable=True))
    db.add(Producto(categoria_id=1, proveedor_id=1, sku="ZERO", nombre="Sin costo", precio_venta=1000, stock_actual=2, costo_unitario=0)); db.commit()
    response = http.get("/admin/operaciones/valorizacion", headers=headers[4]); assert response.status_code == 200
    data = response.json(); assert Decimal(str(data["total"])) == Decimal("62.25") and data["sin_costo"] == 1
    row = next(row for row in data["productos"] if row["id"] == product)
    assert Decimal(str(row["costo"])) == 3 and Decimal(str(row["valor"])) == 60 and not row["activo"]
    assert "inactivos" in data["criterio"]
    db.add(Sucursal(id=2, nombre="Segunda")); db.commit()
    assert http.get("/admin/operaciones/valorizacion", headers={**headers[4], "X-Sucursal-ID": "2"}).json()["total"] == 0


@pytest.mark.parametrize("module,path", [("citas", "/admin/operaciones/citas/1/historial"), ("ventas", "/admin/operaciones/cierres?desde=2026-01-01&hasta=2026-01-31"), ("inventario", "/admin/operaciones/valorizacion")])
def test_reports_allow_read_only_but_respect_revoked_view(operations, module, path):
    http, db, headers, *_ = operations
    permission = PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo=module, puede_ver=True, puede_editar=False, puede_crear=False)
    db.add(permission); db.commit()
    assert http.get(path, headers=headers[4]).status_code == 200
    permission.puede_ver = False; db.commit()
    assert http.get(path, headers=headers[4]).status_code == 403
