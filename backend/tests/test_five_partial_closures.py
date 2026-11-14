"""Cierre HU-082/085/088/115/117: HTTP con JWT y SQLite aislada."""
import datetime as dt
from decimal import Decimal

import pytest
from sqlalchemy import select

from test_admin_clinical_flows import clinic
from test_priority_stories import operations, create_order
from test_eleven_partial_stories import date_range, receive
from app.models.clinic import Notificacion, Producto
from app.models.operations import EventoAuditoria, Sucursal
from app.models.user import PermisoRol, TipoUsuario, Usuario


def test_dashboard_empty_range_keeps_current_pending_and_stock_metrics(operations):
    http, db, headers, _, product = operations
    create_order(http, headers[5], product)
    assert http.patch(f"/admin/productos/{product}", headers=headers[4], json={"stock_minimo": 10}).status_code == 200
    data = http.get("/admin/operaciones/dashboard", headers=headers[4], params={"desde": "2000-01-01", "hasta": "2000-01-02"}).json()
    assert Decimal(data["ventas"]) == 0 and data["cantidad_ventas"] == 0
    assert data["citas_por_estado"] and all(count == 0 for count in data["citas_por_estado"].values())
    assert data["ordenes_pendientes"] == 1 and Decimal(data["saldo_pendiente"]) == 40
    assert [row["id"] for row in data["stock_bajo"]] == [product]


def test_dashboard_and_audit_are_isolated_by_selected_branch(operations):
    http, db, headers, start, product = operations
    db.add(Sucursal(id=2, nombre="Segunda sede")); db.commit()
    create_order(http, headers[5], product)
    http.patch(f"/admin/productos/{product}", headers=headers[4], json={"stock_minimo": 10})
    other = {**headers[4], "X-Sucursal-ID": "2"}
    data = http.get("/admin/operaciones/dashboard", headers=other, params=date_range(start)).json()
    assert data["sucursal_id"] == 2 and data["ordenes_pendientes"] == 0
    assert data["stock_bajo"] == [] and all(count == 0 for count in data["citas_por_estado"].values())
    assert http.get("/admin/operaciones/auditoria", headers=other).json() == []
    assert http.get("/admin/operaciones/lotes", headers=other).json() == []
    assert http.get("/admin/operaciones/auditoria", headers=headers[4]).json()


@pytest.mark.parametrize("params", [{"desde": "2026-11-02", "hasta": "2026-11-01"}, {"desde": "2020-01-01", "hasta": "2026-11-01"}])
def test_dashboard_rejects_invalid_ranges(operations, params):
    http, _, headers, *_ = operations
    assert http.get("/admin/operaciones/dashboard", headers=headers[4], params=params).status_code == 422


def test_stock_threshold_rearms_when_minimum_changes_and_notifies_active_admins(operations):
    http, db, headers, _, product = operations
    db.add(Usuario(id=8, nombre="Admin inactivo", correo="inactive@example.com", contrasena="hash", tipo=TipoUsuario.ADMINISTRADOR, activo=False, sucursal_id=1)); db.commit()
    for minimum in (10, 10, 5, 10):
        assert http.patch(f"/admin/productos/{product}", headers=headers[4], json={"stock_minimo": minimum}).status_code == 200
    notices = db.scalars(select(Notificacion).where(Notificacion.tipo == "stock_bajo")).all()
    assert len(notices) == 2 and {notice.usuario_id for notice in notices} == {4}
    assert all("Medicina" in notice.mensaje and "mínimo" in notice.mensaje for notice in notices)


def test_audit_captures_real_primary_keys_before_after_and_excludes_passwords(operations):
    http, db, headers, _, product = operations
    assert http.patch(f"/admin/productos/{product}", headers=headers[4], json={"nombre": "Nombre nuevo"}).status_code == 200
    unit = {"codigo": "litro", "nombre": "Litro", "dimension": "volumen", "factor_base": 1000, "fraccionable": True}
    assert http.post("/admin/operaciones/unidades", headers=headers[4], json=unit).status_code == 201
    events = http.get("/admin/operaciones/auditoria", headers=headers[4], params={"entidad": "unidades_medida", "usuario_id": 4}).json()
    assert events[0]["registro_id"] == "litro" and events[0]["fecha"] and events[0]["autor"] == "Administración"
    event = next(row for row in http.get("/admin/operaciones/auditoria", headers=headers[4], params={"entidad": "productos"}).json() if row["accion"] == "editar" and "nombre" in row["cambios"])
    assert event["cambios"]["nombre"] == {"antes": "Medicina", "despues": "Nombre nuevo"}
    user = db.get(Usuario, 4)
    user.contrasena = "PRIVATE_PASSWORD_HASH"; user.nombre = "Nombre administrativo"; db.commit()
    stored = db.scalars(select(EventoAuditoria).where(EventoAuditoria.entidad == "usuarios")).all()
    assert stored and all("contrasena" not in event.cambios for event in stored)
    assert "PRIVATE_PASSWORD_HASH" not in http.get("/admin/operaciones/auditoria", headers=headers[4]).text


def test_lot_expiry_or_cost_conflict_does_not_change_stock(operations):
    http, db, headers, _, product = operations
    assert receive(http, headers[4], product, document="ORIGINAL").status_code == 201
    response = http.post("/admin/operaciones/compras", headers=headers[4], json={"proveedor_id": 1, "documento": "CONFLICT", "detalles": [{"producto_id": product, "cantidad": 2, "costo_unitario": 3, "lote": "ORIGINAL", "vencimiento": (dt.date.today() + dt.timedelta(days=91)).isoformat()}]})
    assert response.status_code == 409
    assert db.get(Producto, product).stock_actual == 12
    assert len([lot for lot in http.get("/admin/operaciones/lotes", headers=headers[4]).json() if lot["codigo"] == "ORIGINAL"]) == 1


def test_catalog_units_and_receiving_suppliers_use_their_own_module_permissions(operations):
    http, db, headers, *_ = operations
    inventory = PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="inventario", puede_ver=False, puede_crear=False)
    db.add(inventory); db.commit()
    assert http.get("/admin/productos/unidades", headers=headers[4]).status_code == 200
    assert http.get("/admin/operaciones/unidades", headers=headers[4]).status_code == 403
    inventory.puede_ver, inventory.puede_crear = True, False
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="productos", puede_ver=False)); db.commit()
    assert http.get("/admin/operaciones/proveedores", headers=headers[4]).json() == [{"id": 1, "razon_social": "Proveedor"}]
    assert http.get("/admin/operaciones/unidades", headers=headers[4]).status_code == 200
    assert http.get("/admin/productos/unidades", headers=headers[4]).status_code == 403
    assert http.post("/admin/operaciones/unidades", headers=headers[4], json={"codigo": "l", "nombre": "Litro", "dimension": "volumen", "factor_base": 1000}).status_code == 403
    assert receive(http, headers[4], 1).status_code == 403


def test_fractional_minimum_and_historical_unit_are_preserved_at_zero_stock(operations):
    http, db, headers, _, _ = operations
    payload = {"categoria_id": 1, "proveedor_id": 1, "sku": "PESO", "nombre": "Alimento", "precio_venta": 20, "stock_actual": 0, "stock_minimo": "0.125", "unidad_medida": "kg", "fraccionable": True}
    response = http.post("/admin/productos", headers=headers[4], json=payload)
    assert response.status_code == 201, response.text
    product = response.json()["id"]
    assert Decimal(response.json()["stock_minimo"]) == Decimal("0.125")
    assert receive(http, headers[4], product, unidad="g", cantidad=250).status_code == 201
    sale = http.post("/api/ventas", headers=headers[5], json={"cliente_id": 1, "medio_pago": "efectivo", "items": [{"producto_id": product, "cantidad": "0.250"}]})
    assert sale.status_code == 201 and db.get(Producto, product).stock_actual == 0
    assert http.patch(f"/admin/productos/{product}", headers=headers[4], json={"unidad_medida": "g"}).status_code == 409
    assert http.post("/admin/productos", headers=headers[4], json={**payload, "sku": "INVALID", "unidad_medida": "unidad", "fraccionable": True}).status_code == 422


def test_conversion_rejects_precision_loss_without_creating_stock(operations):
    http, db, headers, _, _ = operations
    product = http.post("/admin/productos", headers=headers[4], json={"categoria_id": 1, "proveedor_id": 1, "sku": "PRECISE", "nombre": "Alimento", "precio_venta": 20, "stock_actual": 0, "unidad_medida": "kg", "fraccionable": True}).json()["id"]
    assert receive(http, headers[4], product, unidad="g", cantidad="0.001").status_code == 422
    assert db.get(Producto, product).stock_actual == 0
