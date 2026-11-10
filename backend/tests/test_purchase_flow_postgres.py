"""Integración real y concurrencia. Usar solamente una BD local aislada de pruebas."""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from io import BytesIO
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models.clinic import Caja, CategoriaProducto, ComprobanteVenta, DetalleOrdenCobro, OrdenCobro, Producto, Proveedor
from app.models.purchase import PedidoWeb
from app.models.user import Cajero, Cliente, PermisoRol, TipoUsuario, Usuario
from app.schemas.purchase import PedidoCreate, RevisionPedido
from app.security import create_access_token
from app.services.cashier_service import CashierService
from app.services.purchase_service import PurchaseService, validate_proof


def png():
    stream = BytesIO()
    Image.new("RGB", (12, 12), "green").save(stream, format="PNG")
    return stream.getvalue()


@pytest.fixture
def setup(monkeypatch):
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Requiere TEST_DATABASE_URL de PostgreSQL local")
    parsed = make_url(url)
    assert parsed.host in ("database", "localhost", "127.0.0.1"), "No ejecutar en Neon"
    assert parsed.database.startswith("test_"), "Usar una BD aislada test_*"
    engine = create_engine(url)
    settings = get_settings()
    for field in ("purchase_yape_holder", "purchase_yape_phone", "purchase_yape_qr_url"):
        monkeypatch.setattr(settings, field, "SOLO-PRUEBAS")
    with Session(engine) as db:
        users = [Usuario(nombre="Prueba web", correo=f"web-{uuid4().hex}@example.com", contrasena="test", tipo=role)
                 for role in (TipoUsuario.CLIENTE, TipoUsuario.CLIENTE, TipoUsuario.CAJERO, TipoUsuario.CAJERO, TipoUsuario.ADMINISTRADOR, TipoUsuario.VETERINARIO)]
        db.add_all(users); db.flush()
        db.add_all([Cliente(usuario_id=u.id) for u in users[:2]])
        db.add_all([Cajero(usuario_id=u.id) for u in users[2:4]])
        category = CategoriaProducto(nombre=f"Test {uuid4().hex}")
        supplier = Proveedor(razon_social="Test web")
        db.add_all([category, supplier]); db.flush()
        product = Producto(categoria_id=category.id, proveedor_id=supplier.id, sku=uuid4().hex,
                           nombre="Producto web", precio_venta=Decimal("25.50"), stock_actual=5, stock_minimo=0, activo=True, imagen_url="/logo.png")
        db.add(product)
        db.add_all([Caja(cajero_id=u.id, fondo_inicial=0, total_ingresos_validados=0, estado_caja="abierta") for u in users[2:4]])
        db.commit()
        ids = [u.id for u in users]
        product_id, category_id, supplier_id = product.id, category.id, supplier.id

    def override():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = override
    headers = [{"Authorization": f"Bearer {create_access_token(id)}"} for id in ids]
    data = {"clave_idempotencia": str(uuid4()), "cliente": {"nombreCompleto": "Cliente Web", "celular": "999999999", "tipoEntrega": "Recojo en clínica", "dni": "12345678"},
            "items": [{"producto_id": product_id, "cantidad": 2}], "metodo_pago": "yape", "numero_operacion": "123456", "total_esperado": "51.00"}
    try:
        with TestClient(app) as client:
            yield client, engine, ids, headers, data, product_id
    finally:
        app.dependency_overrides.pop(get_db, None)
        with Session(engine) as db:
            db.execute(delete(PedidoWeb).where(PedidoWeb.cliente_id.in_(ids)))
            sales = select(OrdenCobro.id).where(OrdenCobro.cajero_id.in_(ids))
            db.execute(delete(ComprobanteVenta).where(ComprobanteVenta.orden_cobro_id.in_(sales)))
            db.execute(delete(DetalleOrdenCobro).where(DetalleOrdenCobro.orden_cobro_id.in_(sales)))
            db.execute(delete(OrdenCobro).where(OrdenCobro.cajero_id.in_(ids)))
            db.execute(delete(Caja).where(Caja.cajero_id.in_(ids)))
            db.execute(delete(Producto).where(Producto.id == product_id))
            db.execute(delete(CategoriaProducto).where(CategoriaProducto.id == category_id))
            db.execute(delete(Proveedor).where(Proveedor.id == supplier_id))
            db.execute(delete(Usuario).where(Usuario.id.in_(ids)))
            db.commit()
        engine.dispose()


def create(client, headers, data, content=None, filename="pago.png"):
    return client.post("/pedidos-web", headers=headers, data={"datos": json.dumps(data)}, files={"comprobante": (filename, png() if content is None else content, "image/png")})


def test_create_review_receipt_ownership_and_single_inventory_movement(setup):
    client, engine, ids, headers, data, product_id = setup
    response = create(client, headers[0], data)
    assert response.status_code == 201, response.text
    order = response.json(); id = order["id"]
    assert order["estado_pedido"] == "PENDIENTE" and order["venta_id"] is None
    assert create(client, headers[0], data).json()["id"] == id
    assert create(client, headers[0], {**data, "numero_operacion": "999999"}).status_code == 409
    assert client.get(f"/pedidos-web/{id}", headers=headers[1]).status_code == 404
    assert client.get(f"/pedidos-web/{id}/comprobante", headers=headers[1]).status_code == 404
    assert client.get("/pedidos-web", headers=headers[1]).json() == []
    assert client.get("/pedidos-web", headers=headers[2], params={"estado": "PENDIENTE", "codigo": order["codigo_pedido"]}).json()[0]["id"] == id
    proof = client.get(f"/pedidos-web/{id}/comprobante", headers=headers[2])
    assert proof.content == png() and proof.headers["content-type"] == "image/png"
    assert "no-store" in proof.headers["cache-control"]
    with Session(engine) as db:
        assert db.get(Producto, product_id).stock_actual == 5
    assert client.post(f"/pedidos-web/{id}/revision", headers=headers[0], json={"accion": "APROBAR"}).status_code == 403
    approval = client.post(f"/pedidos-web/{id}/revision", headers=headers[2], json={"accion": "APROBAR"})
    assert approval.status_code == 200, approval.text
    assert approval.json()["usuario_revisor_id"] == ids[2]
    assert client.get(f"/pedidos-web/{id}", headers=headers[0]).json()["estado_pedido"] == "APROBADO"
    assert client.post(f"/pedidos-web/{id}/revision", headers=headers[3], json={"accion": "APROBAR"}).status_code == 409
    with Session(engine) as db:
        assert db.get(Producto, product_id).stock_actual == 3
        sale = db.get(OrdenCobro, approval.json()["venta_id"])
        assert sale.monto_total == Decimal("51.00") and sale.comprobante_venta
        assert db.scalar(select(func.count()).select_from(OrdenCobro).where(OrdenCobro.clave_idempotencia == f"pedido-web-{id}")) == 1
    assert client.get("/pedidos-web", headers=headers[4]).status_code == 200
    assert client.get("/pedidos-web", headers=headers[5]).status_code == 403


def test_rejection_is_terminal_without_sale_or_stock_change(setup):
    client, engine, ids, headers, data, product_id = setup
    id = create(client, headers[0], data).json()["id"]
    url = f"/pedidos-web/{id}/revision"
    assert client.post(url, headers=headers[2], json={"accion": "RECHAZAR", "motivo": "  "}).status_code == 422
    assert client.post(url, headers=headers[2], json={"accion": "RECHAZAR", "motivo": "Importe incorrecto"}).status_code == 200
    assert client.post(url, headers=headers[2], json={"accion": "APROBAR"}).status_code == 409
    result = client.get(f"/pedidos-web/{id}", headers=headers[0]).json()
    assert result["motivo_rechazo"] == "Importe incorrecto" and result["venta_id"] is None
    with Session(engine) as db:
        assert db.get(Producto, product_id).stock_actual == 5


def test_stock_price_tampering_invalid_files_and_auth(setup):
    client, engine, ids, headers, data, product_id = setup
    assert create(client, {}, data).status_code == 401
    assert create(client, headers[2], data).status_code == 403
    assert create(client, headers[0], {**data, "total_esperado": "0.01"}).status_code == 409
    assert create(client, headers[0], {**data, "items": [{"producto_id": product_id, "cantidad": 100}]}).status_code == 409
    assert create(client, headers[0], data, b"<script>bad</script>", "pago.png").status_code == 422
    assert create(client, headers[0], data, b"x" * (5 * 1024 * 1024 + 1)).status_code == 422
    id = create(client, headers[0], data).json()["id"]
    with Session(engine) as db:
        db.get(Producto, product_id).stock_actual = 0; db.commit()
    assert client.post(f"/pedidos-web/{id}/revision", headers=headers[2], json={"accion": "APROBAR"}).status_code == 409
    with Session(engine) as db:
        assert db.get(PedidoWeb, id).venta_id is None
        db.get(Producto, product_id).stock_actual = 5
        db.get(Producto, product_id).precio_venta = Decimal("26.00"); db.commit()
    response = client.post(f"/pedidos-web/{id}/revision", headers=headers[2], json={"accion": "APROBAR"})
    assert response.status_code == 409 and "precio" in response.text
    with Session(engine) as db:
        assert db.get(Producto, product_id).stock_actual == 5
        assert db.get(PedidoWeb, id).estado_pedido == "PENDIENTE"


def test_failure_after_sale_flush_rolls_back_everything(setup, monkeypatch):
    client, engine, ids, headers, data, product_id = setup
    id = create(client, headers[0], data).json()["id"]
    original = CashierService._create_sale
    def fail(self, *args, **kwargs):
        original(self, *args, **kwargs)
        raise RuntimeError("Falla inyectada después de crear venta y boleta")
    monkeypatch.setattr(CashierService, "_create_sale", fail)
    with Session(engine) as db:
        with pytest.raises(RuntimeError):
            PurchaseService(db).review(db.get(Usuario, ids[2]), id, RevisionPedido(accion="APROBAR"))
    with Session(engine) as db:
        assert db.get(Producto, product_id).stock_actual == 5
        assert db.get(PedidoWeb, id).estado_pedido == "PENDIENTE"
        assert db.scalar(select(OrdenCobro).where(OrdenCobro.clave_idempotencia == f"pedido-web-{id}")) is None
        assert db.scalar(select(Caja).where(Caja.cajero_id == ids[2])).total_ingresos_validados == 0


def test_simultaneous_confirmation_creates_exactly_one_sale(setup):
    client, engine, ids, headers, data, product_id = setup
    id = create(client, headers[0], data).json()["id"]
    barrier = Barrier(2)
    def approve(cashier_id):
        with Session(engine) as db:
            user = db.get(Usuario, cashier_id)
            barrier.wait(timeout=10)
            try:
                PurchaseService(db).review(user, id, RevisionPedido(accion="APROBAR"))
                return 200
            except HTTPException as exc:
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(approve, ids[2:4]))
    assert sorted(results) == [200, 409]
    with Session(engine) as db:
        assert db.get(Producto, product_id).stock_actual == 3
        assert db.scalar(select(func.count()).select_from(OrdenCobro).where(OrdenCobro.clave_idempotencia == f"pedido-web-{id}")) == 1


def test_simultaneous_retries_create_one_order(setup):
    client, engine, ids, headers, data, product_id = setup
    barrier = Barrier(2)
    def submit(_):
        with Session(engine) as db:
            user = db.get(Usuario, ids[0]); barrier.wait(timeout=10)
            return PurchaseService(db).create(user, PedidoCreate.model_validate(data), png())["id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, range(2)))
    assert results[0] == results[1]


def test_two_orders_compete_for_last_stock_without_overselling(setup):
    client, engine, ids, headers, data, product_id = setup
    with Session(engine) as db:
        db.get(Producto, product_id).stock_actual = 2; db.commit()
    order_ids = [create(client, headers[0], {**data, "clave_idempotencia": str(uuid4())}).json()["id"] for _ in range(2)]
    barrier = Barrier(2)
    def approve(pair):
        cashier_id, order_id = pair
        with Session(engine) as db:
            user = db.get(Usuario, cashier_id); barrier.wait(timeout=10)
            try:
                PurchaseService(db).review(user, order_id, RevisionPedido(accion="APROBAR")); return 200
            except HTTPException as exc:
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(approve, zip(ids[2:4], order_ids)))
    assert sorted(results) == [200, 409]
    with Session(engine) as db:
        assert db.get(Producto, product_id).stock_actual == 0
        assert db.scalar(select(func.count()).select_from(PedidoWeb).where(PedidoWeb.id.in_(order_ids), PedidoWeb.estado_pedido == "APROBADO")) == 1


def test_delivery_amount_and_closed_register_are_checked(setup):
    client, engine, ids, headers, data, product_id = setup
    data["cliente"].update(tipoEntrega="Delivery", direccion="Dirección de prueba 123")
    data["total_esperado"] = "61.00"
    response = create(client, headers[0], data)
    assert response.status_code == 201, response.text
    id = response.json()["id"]
    assert response.json()["costo_delivery"] == "10.00"
    with Session(engine) as db:
        register = db.scalar(select(Caja).where(Caja.cajero_id == ids[2]))
        register.estado_caja = "cerrada"; db.commit()
    assert client.post(f"/pedidos-web/{id}/revision", headers=headers[2], json={"accion": "APROBAR"}).status_code == 409
    result = client.post(f"/pedidos-web/{id}/revision", headers=headers[3], json={"accion": "APROBAR"})
    assert result.status_code == 200, result.text
    receipt = client.get(f"/caja/ventas/{result.json()['venta_id']}/boleta", headers=headers[3]).json()
    assert receipt["total"] == "61.00" and receipt["costo_delivery"] == "10.00"
    with Session(engine) as db:
        assert db.get(Producto, product_id).stock_actual == 3


def test_real_pdf_and_jpeg_supported_but_corrupt_content_rejected():
    output = BytesIO(); writer = PdfWriter(); writer.add_blank_page(width=100, height=100); writer.write(output)
    assert validate_proof(output.getvalue())[0] == "application/pdf"
    output = BytesIO(); Image.new("RGB", (12, 12)).save(output, format="JPEG")
    assert validate_proof(output.getvalue())[0] == "image/jpeg"
    for content in (b"%PDF-invalid", b"\x89PNG\r\n\x1a\ninvalid", b""):
        with pytest.raises(HTTPException):
            validate_proof(content)


def test_admin_review_and_permission_matrix(setup):
    client, engine, ids, headers, data, product_id = setup
    id = create(client, headers[0], data).json()["id"]
    result = client.post(f"/pedidos-web/{id}/revision", headers=headers[4], json={"accion": "APROBAR"})
    assert result.status_code == 200, result.text
    assert result.json()["usuario_revisor_id"] == ids[4]
    with Session(engine) as db:
        assert db.get(Producto, product_id).stock_actual == 3
        permission = db.scalar(select(PermisoRol).where(PermisoRol.rol == TipoUsuario.ADMINISTRADOR, PermisoRol.modulo == "ventas"))
        had_permission = permission is not None
        if permission is None:
            permission = PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="ventas")
            db.add(permission)
        old_view, old_approve = permission.puede_ver, permission.puede_aprobar
        permission.puede_ver = True; permission.puede_aprobar = False; db.commit()
        try:
            assert client.get("/pedidos-web", headers=headers[4]).status_code == 200
            assert client.post(f"/pedidos-web/{id}/revision", headers=headers[4], json={"accion": "APROBAR"}).status_code == 403
            permission.puede_ver = False; db.commit()
            assert client.get(f"/pedidos-web/{id}/comprobante", headers=headers[4]).status_code == 403
        finally:
            if had_permission:
                permission.puede_ver, permission.puede_aprobar = old_view, old_approve
            else:
                db.delete(permission)
            db.commit()
