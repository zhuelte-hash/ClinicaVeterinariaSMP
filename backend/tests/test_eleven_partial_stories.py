"""Aceptación HTTP de las once historias cerradas en la versión 2.2.

JWT real y base SQLite aislada. No usa la base operativa ni envía WhatsApp.
"""
import datetime as dt
import json
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from test_priority_stories import operations, create_order, proof
from test_admin_clinical_flows import clinic
from app.models.clinic import Cita, ConfiguracionClinica, EstadoCita, Notificacion, Producto
from app.models.operations import Egreso, EventoAuditoria, LoteInventario, MovimientoInventario, SolicitudReprogramacion, Sucursal
from app.models.user import PermisoRol, TipoUsuario, Usuario
from app.services.access_service import aware


def date_range(start):
    today = dt.datetime.now(dt.timezone.utc).date()
    return {"desde": (today - dt.timedelta(days=1)).isoformat(), "hasta": (start.date() + dt.timedelta(days=1)).isoformat()}


def receive(http, headers, product, document="FACT-001", **changes):
    line = {"producto_id": product, "cantidad": 2, "costo_unitario": 3, "lote": document, "vencimiento": (dt.date.today() + dt.timedelta(days=90)).isoformat(), **changes}
    return http.post("/admin/operaciones/compras", headers=headers, json={"proveedor_id": 1, "documento": document, "detalles": [line]})


def test_public_hours_match_bookings_and_closed_exception(operations):
    http, db, headers, start, _ = operations
    policy = http.get("/publico/institucional").json()
    assert len(policy["horarios"]) == 7
    assert next(day for day in policy["horarios"] if day["dia"] == 6)["cerrado"]
    query = {"servicio_id": 1, "fecha": start.date().isoformat()}
    assert http.get("/portal/disponibilidad", params=query).json()
    policy["excepciones"] = [{"dia": start.weekday(), "fecha": start.date().isoformat(), "motivo": "Feriado de prueba", "cerrado": True}]
    assert http.put("/admin/operaciones/configuracion", headers=headers[4], json=policy).status_code == 200
    assert http.get("/publico/institucional").json()["excepciones"][0]["motivo"] == "Feriado de prueba"
    assert http.get("/portal/disponibilidad", params=query).json() == []
    assert db.get(Cita, 1) is not None  # Los cambios no eliminan citas existentes.


def test_hours_validate_break_and_admin_configures_vet_agenda(operations):
    http, db, headers, start, _ = operations
    policy = http.get("/publico/institucional").json()
    policy["horarios"][0].update(inicio="09:00", fin="11:00", descanso_inicio="12:00", descanso_fin="13:00")
    assert http.put("/admin/operaciones/configuracion", headers=headers[4], json=policy).status_code == 422
    path = "/admin/operaciones/horarios/2"
    rows = http.get(path, headers=headers[4]).json()
    payload = {"dia_semana": start.weekday(), "hora_inicio": "09:00", "hora_fin": "10:00", "activo": True}
    assert http.post(path, headers=headers[4], json=payload).status_code == 409
    payload["activo"] = False
    assert http.put(f"{path}/{rows[0]['id']}", headers=headers[4], json=payload).status_code == 200
    slots = http.get("/portal/disponibilidad", params={"servicio_id": 1, "fecha": start.date().isoformat()}).json()
    assert all(slot["veterinario_id"] != 2 for slot in slots)
    payload["activo"] = True
    assert http.post(path, headers=headers[4], json=payload).status_code == 409
    payload["hora_inicio"], payload["hora_fin"] = "13:00", "14:00"
    assert http.post(path, headers=headers[4], json=payload).status_code == 201
    assert http.post(path, headers=headers[5], json=payload).status_code == 403


def configure_phone(db):
    db.add(ConfiguracionClinica(nombre="Clínica de prueba", correo="", telefono="965939522", direccion="")); db.commit()


def test_client_requests_whatsapp_reschedule_and_admin_accepts_once(operations):
    http, db, headers, start, _ = operations
    configure_phone(db)
    payload = {"fecha_propuesta": (start + dt.timedelta(hours=4)).isoformat(), "motivo": "No puedo asistir por trabajo", "canal": "whatsapp"}
    response = http.post("/portal/citas/1/reprogramacion", headers=headers[1], json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["whatsapp_url"].startswith("https://wa.me/51965939522?text=")
    assert db.get(Cita, 1).fecha_hora_programada.replace(tzinfo=dt.timezone.utc) == start
    assert http.post("/portal/citas/1/reprogramacion", headers=headers[1], json=payload).status_code == 409
    assert http.get("/portal/reprogramaciones", headers=headers[1]).json()[0]["id"] == data["id"]
    url = f"/admin/operaciones/reprogramaciones/{data['id']}/resolver"
    assert http.post(url, headers=headers[1], json={"aceptar": True, "motivo": "Confirmado con cliente"}).status_code == 403
    accepted = http.post(url, headers=headers[4], json={"aceptar": True, "motivo": "Confirmado con cliente"})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["estado"] == "aceptada"
    assert aware(db.get(Cita, 1).fecha_hora_programada) == start + dt.timedelta(hours=4)
    assert http.post(url, headers=headers[4], json={"aceptar": True, "motivo": "Reintento"}).status_code == 409


@pytest.mark.parametrize("hours,expected", [(3.99, 409), (4, 201)])
def test_reschedule_requires_at_least_four_hours_even_if_policy_is_lower(operations, monkeypatch, hours, expected):
    http, db, headers, start, _ = operations
    from app.routers import clinical_operations
    monkeypatch.setattr(clinical_operations, "now", lambda: start - dt.timedelta(hours=hours))
    policy = http.get("/publico/institucional").json(); policy["horas_reprogramacion"] = 0
    http.put("/admin/operaciones/configuracion", headers=headers[4], json=policy)
    payload = {"fecha_propuesta": (start + dt.timedelta(hours=4)).isoformat(), "motivo": "Cambiar por trabajo", "canal": "web"}
    response = http.post("/portal/citas/1/reprogramacion", headers=headers[1], json=payload)
    assert response.status_code == expected, response.text


def test_reschedule_revalidates_slot_and_rejection_allows_new_request(operations):
    http, db, headers, start, _ = operations
    payload = {"fecha_propuesta": (start + dt.timedelta(hours=4)).isoformat(), "motivo": "Cambiar por trabajo", "canal": "web"}
    created = http.post("/portal/citas/1/reprogramacion", headers=headers[1], json=payload).json()
    from app.models.clinic import BloqueoHorario
    db.add(BloqueoHorario(veterinario_id=2, fecha_hora_inicio=start + dt.timedelta(hours=4), fecha_hora_fin=start + dt.timedelta(hours=5), motivo="Ocupado")); db.commit()
    url = f"/admin/operaciones/reprogramaciones/{created['id']}/resolver"
    assert http.post(url, headers=headers[4], json={"aceptar": True, "motivo": "Aceptar propuesta"}).status_code == 409
    assert db.get(SolicitudReprogramacion, created["id"]).estado == "pendiente"
    assert http.post(url, headers=headers[4], json={"aceptar": False, "motivo": "Franja ocupada; coordinar otra"}).json()["estado"] == "rechazada"


def test_dashboard_rankings_use_sales_and_attended_services_not_stock(operations):
    http, db, headers, start, product = operations
    db.get(Cita, 1).estado = EstadoCita.ATENDIDA; db.commit()
    sale = http.post("/api/ventas", headers=headers[5], json={"cliente_id": 1, "medio_pago": "efectivo", "items": [{"producto_id": product, "cantidad": 2}]}).json()
    data = http.get("/admin/operaciones/dashboard", headers=headers[4], params=date_range(start)).json()
    assert Decimal(data["ventas"]) == 40 and data["cantidad_ventas"] == 1
    assert data["citas_por_estado"]["atendida"] == 1
    assert data["productos_mas_vendidos"] == [{"id": product, "nombre": "Medicina", "cantidad": 2}]
    assert data["servicios_mas_atendidos"] == [{"id": 1, "nombre": "Consulta", "cantidad": 1}]
    assert http.post(f"/operaciones/ventas/{sale['orden_id']}/anular", headers=headers[5], json={"motivo": "Venta equivocada"}).status_code == 200
    data = http.get("/admin/operaciones/dashboard", headers=headers[4], params=date_range(start)).json()
    assert data["productos_mas_vendidos"] == [] and Decimal(data["ventas"]) == 0


def test_pending_metrics_and_financial_balance_do_not_double_count_installments(operations):
    http, db, headers, start, product = operations
    order, _ = create_order(http, headers[5], product)
    payment = {"monto": 10, "medio": "efectivo", "canal": "caja", "clave_idempotencia": str(uuid4())}
    assert http.post(f"/operaciones/ordenes/{order['id']}/abonos", headers=headers[5], json=payment).status_code == 201
    sent = {"monto": 5, "medio": "yape", "canal": "whatsapp", "clave_idempotencia": str(uuid4())}
    assert http.post(f"/operaciones/ordenes/{order['id']}/comprobantes", headers=headers[5], data={"datos": json.dumps(sent)}, files={"archivo": ("proof.png", proof(), "image/png")}).status_code == 201
    assert http.post("/api/ventas", headers=headers[5], json={"cliente_id": 1, "medio_pago": "efectivo", "items": [{"producto_id": product, "cantidad": 1}]}).status_code == 201
    expense = {"categoria": "Servicios", "concepto": "Servicio eléctrico", "monto": 7, "fecha": dt.date.today().isoformat()}
    assert http.post("/admin/operaciones/egresos", headers=headers[4], json=expense).status_code == 201
    data = http.get("/admin/operaciones/dashboard", headers=headers[4], params=date_range(start)).json()
    assert data["ordenes_pendientes"] == 1 and Decimal(data["saldo_pendiente"]) == 30 and data["pagos_por_validar"] == 1
    assert Decimal(data["finanzas"]["cobros"]) == 30
    assert Decimal(data["finanzas"]["egresos"]) == 7 and Decimal(data["finanzas"]["resultado"]) == 23
    payment["monto"], payment["clave_idempotencia"] = 30, str(uuid4())
    assert http.post(f"/operaciones/ordenes/{order['id']}/abonos", headers=headers[5], json=payment).status_code == 201
    data = http.get("/admin/operaciones/dashboard", headers=headers[4], params=date_range(start)).json()
    assert Decimal(data["finanzas"]["cobros"]) == 60  # 40 de orden + 20 de venta directa, no 100.
    assert data["ordenes_pendientes"] == 0


def test_stock_threshold_notifies_once_rearms_and_uses_branch(operations):
    http, db, headers, _, product = operations
    db.add(Sucursal(id=2, nombre="Otra sede")); db.flush()
    db.add(Usuario(id=8, nombre="Admin otra sede", correo="branch@example.com", contrasena="hash", tipo=TipoUsuario.ADMINISTRADOR, sucursal_id=2)); db.commit()
    assert http.patch(f"/admin/productos/{product}", headers=headers[4], json={"stock_minimo": 9}).status_code == 200
    sale = {"cliente_id": 1, "medio_pago": "efectivo", "items": [{"producto_id": product, "cantidad": 1}]}
    assert http.post("/api/ventas", headers=headers[5], json=sale).status_code == 201
    assert http.post("/api/ventas", headers=headers[5], json=sale).status_code == 201
    notices = db.scalars(select(Notificacion).where(Notificacion.tipo == "stock_bajo")).all()
    assert len(notices) == 1 and notices[0].usuario_id == 4
    assert receive(http, headers[4], product, cantidad=4).status_code == 201
    assert not db.get(Producto, product).alerta_stock_activa
    sale["items"][0]["cantidad"] = 3
    assert http.post("/api/ventas", headers=headers[5], json=sale).status_code == 201
    assert len(db.scalars(select(Notificacion).where(Notificacion.tipo == "stock_bajo")).all()) == 2


def test_stock_notifications_can_be_disabled_then_enabled(operations):
    http, db, headers, _, product = operations
    settings = {"nombre": "Pruebas", "correo": "clinic@example.com", "telefono": "", "direccion": "", "umbral_stock_bajo": 5, "recordatorios_citas": False, "alertas_stock": False}
    assert http.patch("/admin/configuracion", headers=headers[4], json=settings).status_code == 200
    http.patch(f"/admin/productos/{product}", headers=headers[4], json={"stock_minimo": 10})
    assert not db.scalars(select(Notificacion).where(Notificacion.tipo == "stock_bajo")).all()
    settings["alertas_stock"] = True
    assert http.patch("/admin/configuracion", headers=headers[4], json=settings).status_code == 200
    assert http.patch("/admin/configuracion", headers=headers[4], json=settings).status_code == 200
    assert len(db.scalars(select(Notificacion).where(Notificacion.tipo == "stock_bajo")).all()) == 1


def test_receiving_lots_updates_stock_cost_expense_and_prevents_duplicates(operations):
    http, db, headers, start, product = operations
    assert receive(http, headers[4], product).status_code == 201
    assert db.get(Producto, product).stock_actual == 12
    rows = http.get("/admin/operaciones/lotes", headers=headers[4]).json()
    lot = next(row for row in rows if row["codigo"] == "FACT-001")
    assert Decimal(lot["cantidad"]) == 2 and lot["vencimiento"]
    assert db.scalar(select(Egreso).where(Egreso.compra_id.is_not(None))).monto == 6
    assert receive(http, headers[4], product).status_code == 409
    assert db.get(Producto, product).stock_actual == 12
    assert receive(http, headers[4], product, document="FACT-OLD", vencimiento="2000-01-01").status_code == 422


def test_medicine_requires_expiry_and_fefo_does_not_sell_expired_lots(operations):
    http, db, headers, _, _ = operations
    payload = {"categoria_id": 1, "proveedor_id": 1, "sku": "VAC-01", "nombre": "Vacuna", "precio_venta": 20, "stock_actual": 1, "requiere_vencimiento": True}
    assert http.post("/admin/productos", headers=headers[4], json=payload).status_code == 422
    payload["stock_actual"] = 0
    product = http.post("/admin/productos", headers=headers[4], json=payload).json()["id"]
    assert receive(http, headers[4], product, vencimiento=None).status_code == 422
    assert receive(http, headers[4], product, document="LATE", vencimiento=(dt.date.today() + dt.timedelta(days=90)).isoformat()).status_code == 201
    assert receive(http, headers[4], product, document="EARLY", vencimiento=(dt.date.today() + dt.timedelta(days=10)).isoformat()).status_code == 201
    sale = {"cliente_id": 1, "medio_pago": "efectivo", "items": [{"producto_id": product, "cantidad": 1}]}
    assert http.post("/api/ventas", headers=headers[5], json=sale).status_code == 201
    early = db.scalar(select(LoteInventario).where(LoteInventario.producto_id == product, LoteInventario.codigo == "EARLY"))
    assert early.cantidad == 1
    early.vencimiento = dt.date(2000, 1, 1); db.commit()
    sale["items"][0]["cantidad"] = 3
    assert http.post("/api/ventas", headers=headers[5], json=sale).status_code == 409
    assert db.get(Producto, product).stock_actual == 3


def test_unit_conversion_fractional_sale_and_incompatible_units(operations):
    http, db, headers, _, _ = operations
    unit = {"codigo": "litro", "nombre": "Litro", "dimension": "volumen", "factor_base": 1000, "fraccionable": True}
    assert http.post("/admin/operaciones/unidades", headers=headers[4], json=unit).status_code == 201
    assert http.post("/admin/operaciones/unidades", headers=headers[4], json=unit).status_code == 409
    product_data = {"categoria_id": 1, "proveedor_id": 1, "sku": "KG-01", "nombre": "Alimento al peso", "precio_venta": 20, "stock_actual": 0, "unidad_medida": "kg", "fraccionable": True}
    response = http.post("/admin/productos", headers=headers[4], json=product_data)
    assert response.status_code == 201, response.text
    product = response.json()["id"]
    assert receive(http, headers[4], product, unidad="g", cantidad=500, costo_unitario="0.01").status_code == 201
    assert db.get(Producto, product).stock_actual == Decimal("0.500")
    assert receive(http, headers[4], product, document="WRONG", unidad="ml").status_code == 422
    sale = http.post("/api/ventas", headers=headers[5], json={"cliente_id": 1, "medio_pago": "efectivo", "items": [{"producto_id": product, "cantidad": "0.250"}]})
    assert sale.status_code == 201, sale.text
    assert db.get(Producto, product).stock_actual == Decimal("0.250")
    renamed = http.patch(f"/admin/productos/{product}", headers=headers[4], json={"nombre": "Alimento al peso actualizado"})
    assert renamed.status_code == 200 and renamed.json()["unidad_medida"] == "kg"
    assert http.patch(f"/admin/productos/{product}", headers=headers[4], json={"unidad_medida": "g"}).status_code == 409


def test_medicine_cannot_bypass_lots_with_manual_stock_increase(operations):
    http, db, headers, _, product = operations
    assert http.patch(f"/admin/productos/{product}", headers=headers[4], json={"requiere_vencimiento": True}).status_code == 200
    result = http.patch(f"/admin/inventario/{product}", headers=headers[4], json={"stock_actual": 12, "stock_anterior": 10, "motivo": "Ingreso manual"})
    assert result.status_code == 409 and db.get(Producto, product).stock_actual == 10
    sale = http.post("/api/ventas", headers=headers[5], json={"cliente_id": 1, "medio_pago": "efectivo", "items": [{"producto_id": product, "cantidad": 1}]})
    assert sale.status_code == 409  # El lote histórico sin fecha queda fuera de venta.


def test_receipt_rolls_back_all_lines_on_error(operations):
    http, db, headers, _, product = operations
    lines = [{"producto_id": product, "cantidad": 1, "costo_unitario": 2, "lote": "GOOD"}, {"producto_id": product, "cantidad": 1, "costo_unitario": 2, "lote": "BAD", "vencimiento": "2000-01-01"}]
    response = http.post("/admin/operaciones/compras", headers=headers[4], json={"proveedor_id": 1, "documento": "MULTI", "detalles": lines})
    assert response.status_code == 422
    assert db.get(Producto, product).stock_actual == 10
    assert not db.scalar(select(LoteInventario.id).where(LoteInventario.codigo == "GOOD"))


def test_audit_records_author_changes_filters_secrets_and_permissions(operations):
    http, db, headers, start, product = operations
    assert http.patch(f"/admin/productos/{product}", headers=headers[4], json={"nombre": "Medicina actualizada"}).status_code == 200
    params = {**date_range(start), "entidad": "productos", "usuario_id": 4}
    events = http.get("/admin/operaciones/auditoria", headers=headers[4], params=params).json()
    assert any(event["autor"] == "Administración" and event["cambios"].get("nombre", {}).get("despues") == "Medicina actualizada" for event in events)
    assert all("contrasena" not in event["cambios"] for event in events)
    assert http.get("/admin/operaciones/auditoria", headers=headers[1], params=params).status_code == 403
    assert http.get("/admin/operaciones/auditoria", headers=headers[4], params={"desde": "2026-01-01"}).status_code == 422
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="usuarios", puede_ver=False)); db.commit()
    assert http.get("/admin/operaciones/auditoria", headers=headers[4], params=params).status_code == 403
