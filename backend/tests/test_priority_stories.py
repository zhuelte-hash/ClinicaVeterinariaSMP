"""Aceptación de las diez historias parciales prioritarias con autenticación real."""
import datetime as dt
import json
from decimal import Decimal
from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile
import xml.etree.ElementTree as ET

import pytest
from PIL import Image
from sqlalchemy import select

from test_admin_clinical_flows import clinic
from app.main import app
from app.models.clinic import Caja, CategoriaProducto, Cita, EstadoCita, OrdenCobro, Producto, Proveedor
from app.models.operations import AbonoOrden, EventoAuditoria, MovimientoCaja, OrdenPendiente
from app.models.user import Cajero, PermisoRol, TipoUsuario, Usuario
from app.security import create_access_token, get_current_active_user
from app.services.cashier_service import CashierService
from app.services.user_service import UserService


@pytest.fixture
def operations(clinic):
    http, db, start, vet = clinic
    cashier = Usuario(id=5, nombre="Caja", correo="cashier@example.com", tipo=TipoUsuario.CAJERO, contrasena="hash")
    db.add(cashier); db.flush(); db.add(Cajero(usuario_id=5)); db.flush()
    db.add(Caja(cajero_id=5, fondo_inicial=100, estado_caja="abierta"))
    db.add_all([CategoriaProducto(id=1, nombre="Medicamentos"), Proveedor(id=1, razon_social="Proveedor")]); db.commit()
    # Todas las peticiones de esta suite pasan por JWT, rol, permisos y sucursal.
    app.dependency_overrides.pop(get_current_active_user, None)
    headers = {id: {"Authorization": f"Bearer {create_access_token(id)}"} for id in (1, 2, 3, 4, 5)}
    response = http.post("/admin/productos", headers=headers[4], json={"categoria_id": 1, "proveedor_id": 1, "sku": "MED-1", "nombre": "Medicina", "precio_venta": "20.00", "stock_actual": 10})
    assert response.status_code == 201, response.text
    yield http, db, headers, start, response.json()["id"]


def create_order(http, headers, product, **changes):
    data = {"cliente_id": 1, "detalles": [{"producto_id": product, "cantidad": 2}], "clave_idempotencia": str(uuid4()), **changes}
    response = http.post("/operaciones/ordenes", headers=headers, json=data)
    assert response.status_code == 201, response.text
    return response.json(), data


def proof():
    output = BytesIO(); Image.new("RGB", (12, 12), "green").save(output, format="PNG")
    return output.getvalue()


@pytest.mark.parametrize("role,module,path", [(1, "mascotas", "/portal/mascotas"), (2, "citas", "/portal/veterinario/solicitudes"), (5, "ventas", "/caja/resumen"), (4, "ventas", "/api/admin/ventas")])
def test_matrix_applies_to_every_portal_and_direct_api_calls(operations, role, module, path):
    http, db, headers, *_ = operations
    assert http.get(path, headers=headers[role]).status_code == 200
    update = http.put(f"/admin/permisos/{db.get(Usuario, role).tipo.value}/{module}", headers=headers[4], json={"puede_ver": False})
    assert update.status_code == 200, update.text
    assert http.get(path, headers=headers[role]).status_code == 403
    if role != 4:
        assert http.get("/admin/productos", headers=headers[role]).status_code == 403


def test_sales_approval_and_void_permissions_cannot_be_bypassed(operations):
    http, db, headers, *_ = operations
    db.add(PermisoRol(rol=TipoUsuario.CAJERO, modulo="ventas", puede_ver=True, puede_crear=True, puede_aprobar=False, puede_eliminar=False)); db.commit()
    assert http.post("/operaciones/pagos/999/validar", headers=headers[5]).status_code == 403
    assert http.post("/operaciones/ventas/999/anular", headers=headers[5], json={"motivo": "Venta equivocada"}).status_code == 403


def test_staff_deactivation_preserves_history_invalidates_tokens_and_hides_availability(operations):
    http, db, headers, start, _ = operations
    vet = db.get(Usuario, 2); vet.contrasena = UserService(db)._hash_password("Veterinaria123"); db.commit()
    assert http.get("/portal/veterinario/solicitudes", headers=headers[2]).status_code == 200
    assert http.patch("/usuarios/2/estado", headers=headers[4], json={"activo": False}).status_code == 200
    assert db.get(Cita, 1).veterinario_id == 2
    assert http.get("/portal/veterinario/solicitudes", headers=headers[2]).status_code == 401
    assert http.post("/auth/login", json={"identifier": vet.correo, "password": "Veterinaria123"}).status_code == 403
    slots = http.get("/portal/disponibilidad", params={"servicio_id": 1, "fecha": start.date().isoformat()}).json()
    assert all(slot["veterinario_id"] != 2 for slot in slots)
    assert http.patch("/usuarios/4/estado", headers=headers[4], json={"activo": False}).status_code == 409
    assert http.patch("/usuarios/1/estado", headers=headers[4], json={"activo": False}).status_code == 422
    assert http.patch("/usuarios/2/estado", headers=headers[4], json={"activo": True}).status_code == 200
    assert http.get("/portal/veterinario/solicitudes", headers=headers[2]).status_code == 401
    assert http.post("/auth/login", json={"identifier": vet.correo, "password": "Veterinaria123"}).status_code == 200
    assert any(row.cambios.get("activo", {}).get("despues") is False and row.usuario_id == 4 for row in db.scalars(select(EventoAuditoria).where(EventoAuditoria.entidad == "usuarios")).all())


def test_pending_order_is_before_payment_idempotent_and_not_a_sale(operations):
    http, db, headers, _, product = operations
    order, payload = create_order(http, headers[5], product)
    assert order["estado"] == "pendiente" and order["saldo"] == 40 and order["venta_id"] is None
    assert db.get(Producto, product).stock_actual == 10
    assert db.scalars(select(OrdenCobro)).all() == []
    assert http.post("/operaciones/ordenes", headers=headers[5], json=payload).json()["id"] == order["id"]
    assert http.post("/operaciones/ordenes", headers=headers[5], json={**payload, "detalles": [{"producto_id": product, "cantidad": 1}]}).status_code == 409
    assert [row["id"] for row in http.get("/operaciones/ordenes", headers=headers[5], params={"sin_comprobante": True}).json()] == [order["id"]]


def test_clinical_closure_generates_one_order_for_service_and_prescription(operations):
    http, db, headers, _, product = operations
    db.get(Cita, 1).estado = EstadoCita.CONFIRMADA; db.commit()
    response = http.post("/portal/veterinario/solicitudes/1/atencion/iniciar", headers=headers[2])
    assert response.status_code == 201, response.text
    process_id = response.json()["id"]
    prescription = {"indicaciones_generales": "Completar tratamiento", "detalles": [{"medicamento": "Medicina", "dosis": "1", "unidad": "tableta", "via": "oral", "frecuencia": "cada 12 horas", "duracion": "2 días", "producto_id": product, "cantidad_producto": 2}]}
    saved = http.put(f"/portal/veterinario/atenciones/{process_id}/receta", headers=headers[2], json=prescription)
    assert saved.status_code == 200, saved.text
    response = http.patch(f"/portal/veterinario/atenciones/{process_id}/estado", headers=headers[2], json={"estado": "cerrada"})
    assert response.status_code == 200, response.text
    order = db.scalar(select(OrdenPendiente).where(OrdenPendiente.proceso_id == process_id))
    assert order.total == Decimal("90.00") and len(order.detalles) == 2
    assert db.get(Producto, product).stock_actual == 10
    direct = http.post("/api/ventas", headers=headers[5], json={"cliente_id": 1, "proceso_atencion_id": process_id, "medio_pago": "efectivo", "items": [{"servicio_id": 1, "cantidad": 1}]})
    assert direct.status_code == 422 and "orden" in direct.json()["detail"]
    duplicate = http.post("/operaciones/ordenes", headers=headers[5], json={"cliente_id": 1, "proceso_id": process_id, "detalles": [{"servicio_id": 1, "cantidad": 1}], "clave_idempotencia": str(uuid4())})
    assert duplicate.status_code == 409


def test_whatsapp_proof_is_private_reviewed_and_settles_exactly_once(operations):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    payment = {"monto": "40.00", "medio": "transferencia", "canal": "whatsapp", "codigo_operacion": "OP-123", "clave_idempotencia": str(uuid4())}
    url = f"/operaciones/ordenes/{order['id']}/comprobantes"
    bad = http.post(url, headers=headers[5], data={"datos": json.dumps(payment)}, files={"archivo": ("fake.png", b"fake", "image/png")})
    assert bad.status_code == 422
    result = http.post(url, headers=headers[5], data={"datos": json.dumps(payment)}, files={"archivo": ("pago.png", proof(), "image/png")})
    assert result.status_code == 201, result.text
    abono = result.json()["abonos"][0]
    assert abono["estado"] == "enviado" and result.json()["saldo"] == 40
    assert http.get(f"/operaciones/pagos/{abono['id']}/comprobante").status_code == 401
    assert http.get(f"/operaciones/pagos/{abono['id']}/comprobante", headers=headers[1]).content == proof()
    assert http.post(f"/operaciones/pagos/{abono['id']}/validar", headers=headers[1]).status_code == 403
    # Cambiar la tarifa no altera el importe ya comunicado en la orden.
    db.get(Producto, product).precio_venta = Decimal("25.00"); db.commit()
    response = http.post(f"/operaciones/pagos/{abono['id']}/validar", headers=headers[5])
    assert response.status_code == 200, response.text
    paid = response.json()
    assert paid["estado"] == "pagada" and paid["saldo"] == 0
    assert http.post(f"/operaciones/pagos/{abono['id']}/validar", headers=headers[5]).json()["venta_id"] == paid["venta_id"]
    assert db.get(Producto, product).stock_actual == 8
    assert len(db.scalars(select(MovimientoCaja)).all()) == 1
    assert CashierService(db)._payment_totals(db.get(AbonoOrden, abono["id"]).caja_id) == (Decimal(0), Decimal(40))
    assert http.get(f"/operaciones/ventas/{paid['venta_id']}/boleta", headers=headers[1]).content.startswith(b"%PDF")
    assert http.get("/operaciones/ordenes", headers=headers[5], params={"sin_comprobante": True}).json() == []


def test_rejected_proof_returns_order_to_follow_up_and_failure_rolls_back(operations):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    data = {"monto": 40, "medio": "yape", "canal": "whatsapp", "clave_idempotencia": str(uuid4())}
    response = http.post(f"/operaciones/ordenes/{order['id']}/comprobantes", headers=headers[5], data={"datos": json.dumps(data)}, files={"archivo": ("pago.png", proof(), "image/png")})
    id = response.json()["abonos"][0]["id"]
    db.get(Producto, product).activo = False; db.commit()
    assert http.post(f"/operaciones/pagos/{id}/validar", headers=headers[5]).status_code == 409
    assert db.get(AbonoOrden, id).estado == "enviado" and not db.scalars(select(MovimientoCaja)).all()
    assert http.post(f"/operaciones/pagos/{id}/rechazar", headers=headers[5], json={"motivo": "Operación no encontrada"}).status_code == 200
    assert http.get("/operaciones/ordenes", headers=headers[5], params={"sin_comprobante": True}).json()[0]["id"] == order["id"]


def test_discount_requires_admin_approval_matching_client_and_single_use(operations):
    http, db, headers, _, product = operations
    request = http.post("/operaciones/descuentos", headers=headers[5], json={"cliente_id": 1, "monto": 5, "motivo": "Campaña autorizada"})
    id = request.json()["id"]
    payload = {"cliente_id": 1, "medio_pago": "efectivo", "descuento": 5, "autorizacion_descuento_id": id, "items": [{"producto_id": product, "cantidad": 1}]}
    assert http.post("/api/ventas", headers=headers[5], json=payload).status_code in (409, 422)
    assert http.post(f"/operaciones/descuentos/{id}/aprobar", headers=headers[5]).status_code == 403
    assert http.post(f"/operaciones/descuentos/{id}/aprobar", headers=headers[4]).status_code == 200
    assert http.post("/api/ventas", headers=headers[5], json=payload).status_code == 201
    assert http.post("/api/ventas", headers=headers[5], json=payload).status_code in (409, 422)
    records = http.get("/operaciones/descuentos", headers=headers[5]).json()
    assert records[0]["aprobador_nombre"] and records[0]["usada"]


def test_authorized_discount_on_pending_order_is_preserved_at_settlement(operations):
    http, db, headers, _, product = operations
    request = http.post("/operaciones/descuentos", headers=headers[5], json={"cliente_id": 1, "monto": 5, "motivo": "Convenio del cliente"}).json()
    assert http.post(f"/operaciones/descuentos/{request['id']}/aprobar", headers=headers[4]).status_code == 200
    order, _ = create_order(http, headers[5], product, autorizacion_id=request["id"])
    assert order["total"] == 35
    response = http.post(f"/operaciones/ordenes/{order['id']}/abonos", headers=headers[5], json={"monto": "35.00", "medio": "efectivo", "canal": "caja", "clave_idempotencia": str(uuid4())})
    assert response.status_code == 201, response.text
    assert response.json()["estado"] == "pagada" and response.json()["saldo"] == 0
    sale = db.get(OrdenCobro, response.json()["venta_id"])
    assert sale.descuento == 5 and sale.monto_total == 35
    assert CashierService(db)._payment_totals(sale.caja_id) == (Decimal(35), Decimal(0))


def test_cashier_can_void_own_sale_with_reason_and_reverse_stock_and_cash_once(operations):
    http, db, headers, _, product = operations
    sale = http.post("/api/ventas", headers=headers[5], json={"cliente_id": 1, "medio_pago": "efectivo", "items": [{"producto_id": product, "cantidad": 1}]}).json()
    url = f"/operaciones/ventas/{sale['orden_id']}/anular"
    assert http.post(url, headers=headers[5], json={"motivo": " "}).status_code == 422
    assert http.post(url, headers=headers[2], json={"motivo": "Venta equivocada"}).status_code == 403
    assert http.post(url, headers=headers[5], json={"motivo": "Venta equivocada"}).status_code == 200
    assert db.get(Producto, product).stock_actual == 10
    assert db.get(OrdenCobro, sale["orden_id"]).anulado_por == 5
    assert http.post(url, headers=headers[5], json={"motivo": "Reintento"}).status_code == 409
    assert db.get(Producto, product).stock_actual == 10
    assert CashierService(db)._payment_totals(db.get(OrdenCobro, sale["orden_id"]).caja_id) == (Decimal(0), Decimal(0))


def test_order_cancellation_has_author_history_and_inclusive_local_date_filters(operations):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    row = db.get(OrdenPendiente, order["id"])
    row.fecha = dt.datetime(2026, 11, 11, 4, 59, tzinfo=dt.timezone.utc); db.commit()
    params = {"fecha_inicial": "2026-11-10", "fecha_final": "2026-11-10", "estado": "pendiente"}
    assert http.get("/operaciones/ordenes", headers=headers[4], params=params).json()[0]["id"] == row.id
    assert http.get("/operaciones/ordenes", headers=headers[4], params={**params, "fecha_inicial": "2026-11-11", "fecha_final": "2026-11-11"}).json() == []
    assert http.post(f"/operaciones/ordenes/{row.id}/anular", headers=headers[5], json={"motivo": "Solicitud duplicada"}).status_code == 200
    detail = http.get(f"/operaciones/ordenes/{row.id}", headers=headers[4]).json()
    assert detail["motivo_anulacion"] == "Solicitud duplicada" and any(event["usuario_id"] == 5 and "motivo_anulacion" in event["cambios"] for event in detail["historial"])
    assert http.get("/operaciones/ordenes", headers=headers[4], params={"estado": "inventado"}).status_code == 422
    assert http.get("/operaciones/ordenes", headers=headers[4], params={"fecha_inicial": "2026-11-11", "fecha_final": "2026-11-10"}).status_code == 422


def test_client_payments_include_direct_receipts_and_own_orders_only(operations):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    http.post("/api/ventas", headers=headers[5], json={"cliente_id": 1, "medio_pago": "efectivo", "items": [{"producto_id": product, "cantidad": 1}]})
    data = http.get("/operaciones/mis-pagos", headers=headers[1]).json()
    assert data["ordenes"][0]["id"] == order["id"] and data["ventas"][0]["boleta"] and data["pedidos_web"] == []
    from app.models.user import Cliente
    db.add(Usuario(id=6, nombre="Otro dueño", correo="other-owner@example.com", tipo=TipoUsuario.CLIENTE, contrasena="hash")); db.flush(); db.add(Cliente(usuario_id=6)); db.commit()
    other = {"Authorization": f"Bearer {create_access_token(6)}"}
    assert http.get("/operaciones/mis-pagos", headers=other).json() == {"ordenes": [], "ventas": [], "pedidos_web": []}
    assert http.get(data["ventas"][0]["boleta"], headers=other).status_code == 404
    assert http.get(f"/operaciones/ordenes/{order['id']}", headers=other).status_code == 404


def test_web_payments_link_to_the_clients_sale_receipt(operations):
    from app.models.purchase import PedidoWeb
    http, db, headers, _, product = operations
    sale = http.post("/api/ventas", headers=headers[5], json={"cliente_id": 1, "medio_pago": "yape", "items": [{"producto_id": product, "cantidad": 1}]}).json()
    db.add(PedidoWeb(codigo_pedido="PED-HISTORIAL", cliente_id=1, subtotal=20, total=20, descuento=0, costo_delivery=0, metodo_pago="yape", estado_pedido="APROBADO", estado_pago="VALIDADO", datos_cliente={}, numero_operacion="WEB-123", observaciones="", comprobante_pago="pago.png", comprobante_tipo="image/png", comprobante_contenido=proof(), clave_idempotencia=str(uuid4()), solicitud_hash="a" * 64, venta_id=sale["orden_id"]))
    db.commit()
    data = http.get("/operaciones/mis-pagos", headers=headers[1]).json()
    assert data["pedidos_web"][0]["codigo"] == "PED-HISTORIAL"
    assert data["ventas"][0]["origen"] == "web"
    assert http.get(data["ventas"][0]["boleta"], headers=headers[1]).content.startswith(b"%PDF")


@pytest.mark.parametrize("report", ["ventas", "citas", "inventario"])
def test_excel_exports_complete_filtered_data_and_enforce_permissions(operations, report):
    http, db, headers, start, product = operations
    # Supera la página de 20 filas del listado de ventas.
    if report == "ventas":
        for _ in range(21):
            response = http.post("/api/ventas", headers=headers[5], json={"cliente_id": 1, "medio_pago": "transferencia", "items": [{"servicio_id": 1, "cantidad": 1}]})
            assert response.status_code == 201, response.text
    date = dt.datetime.now(dt.timezone.utc).date()
    params = {"desde": (date - dt.timedelta(days=1)).isoformat(), "hasta": start.date().isoformat()}
    response = http.get(f"/admin/operaciones/exportar/{report}", headers=headers[4], params=params)
    assert response.status_code == 200, response.text
    archive = ZipFile(BytesIO(response.content))
    root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    rows = root.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row")
    assert len(rows) == {"ventas": 22, "citas": 3, "inventario": 2}[report]
    assert http.get(f"/admin/operaciones/exportar/{report}", headers=headers[5], params=params).status_code == 403
    module = {"ventas": "ventas", "citas": "citas", "inventario": "inventario"}[report]
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo=module, puede_ver=False)); db.commit()
    assert http.get(f"/admin/operaciones/exportar/{report}", headers=headers[4], params=params).status_code == 403
