"""Prueba transaccional contra una base PostgreSQL de pruebas (nunca Neon)."""
import os
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.clinic import Caja, EstadoPago, OrdenCobro, Producto
from app.models.user import Cajero, TipoUsuario, Usuario
from app.database import get_db
from app.main import app
from app.security import create_access_token
from app.schemas.cashier import VentaCreate
from app.services.cashier_service import CashierService, StockInsuficienteError, VentaDuplicadaError
from app.services.sales_service import SalesService


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Requiere TEST_DATABASE_URL de PostgreSQL local")
def test_sale_retry_stock_failure_and_void_are_atomic():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    with engine.connect() as connection:
        outer = connection.begin()
        try:
            db = Session(bind=connection, join_transaction_mode="create_savepoint")
            product = db.scalar(select(Producto).where(Producto.activo, Producto.stock_actual > 0).order_by(Producto.id))
            if product is None:
                pytest.skip("La base de pruebas necesita un producto activo con stock")
            initial_stock = product.stock_actual
            user = Usuario(nombre="Test caja", correo=f"test-{uuid4().hex}@example.com",
                           contrasena="test", tipo=TipoUsuario.CAJERO)
            db.add(user)
            db.flush()
            db.add(Cajero(usuario_id=user.id))
            db.flush()
            db.add(Caja(cajero_id=user.id, fondo_inicial=Decimal("0"),
                        total_ingresos_validados=Decimal("0"), estado_caja="abierta"))
            db.commit()
            service = CashierService(db)
            data = VentaCreate(medio_pago="efectivo", clave_idempotencia=uuid4().hex,
                               items=[{"producto_id": product.id, "cantidad": 1}])
            receipt = service.create_sale(user, data)
            assert receipt.total == product.precio_venta
            assert len(receipt.detalles) == 1
            assert service.create_sale(user, data).orden_id == receipt.orden_id
            assert db.get(Producto, product.id).stock_actual == initial_stock - 1
            with pytest.raises(VentaDuplicadaError):
                service.create_sale(user, data.model_copy(update={"medio_pago": "yape"}))
            with pytest.raises(StockInsuficienteError):
                service.create_sale(user, VentaCreate(medio_pago="efectivo",
                    items=[{"producto_id": product.id, "cantidad": 100}]))
            assert db.scalar(select(OrdenCobro).where(OrdenCobro.codigo_orden == receipt.codigo_orden)).id == receipt.orden_id
            assert db.get(Producto, product.id).stock_actual == initial_stock - 1
            assert SalesService(db).get(receipt.orden_id)["estado"] == "PAGADA"
            assert SalesService(db).void(receipt.orden_id)["estado"] == "ANULADA"
            assert db.get(Producto, product.id).stock_actual == initial_stock
            assert db.get(OrdenCobro, receipt.orden_id).estado_pago == EstadoPago.ANULADO
            with pytest.raises(ValueError):
                SalesService(db).void(receipt.orden_id)

            admin = Usuario(nombre="Test admin", correo=f"admin-{uuid4().hex}@example.com",
                            contrasena="test", tipo=TipoUsuario.ADMINISTRADOR)
            db.add(admin)
            db.commit()
            app.dependency_overrides[get_db] = lambda: db
            try:
                with TestClient(app) as client:
                    cashier_headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}
                    admin_headers = {"Authorization": f"Bearer {create_access_token(admin.id)}"}
                    body = {"medio_pago": "yape", "cliente_id": None,
                            "clave_idempotencia": uuid4().hex,
                            "items": [{"producto_id": product.id, "cantidad": 1}]}
                    response = client.post("/api/ventas", json=body, headers=cashier_headers)
                    assert response.status_code == 201, response.text
                    sale = response.json()
                    assert client.post("/api/ventas", json=body, headers=cashier_headers).json()["orden_id"] == sale["orden_id"]
                    assert client.get("/api/admin/ventas", headers=cashier_headers).status_code == 403
                    listing = client.get("/api/admin/ventas", headers=admin_headers,
                        params={"numero_venta": sale["codigo_orden"], "estado": "PAGADA", "metodo_pago": "yape"})
                    assert listing.status_code == 200 and listing.json()["total"] == 1
                    assert client.get(f"/api/admin/ventas/{sale['orden_id']}", headers=admin_headers).json()["detalles"][0]["cantidad"] == 1
                    assert client.get("/api/admin/ventas/resumen", headers=admin_headers,
                        params={"numero_venta": sale["codigo_orden"]}).json()["productos_vendidos"] == 1
                    assert client.post(f"/api/admin/ventas/{sale['orden_id']}/anular", headers=admin_headers).json()["estado"] == "ANULADA"
                    assert db.get(Producto, product.id).stock_actual == initial_stock
            finally:
                app.dependency_overrides.pop(get_db, None)
            db.close()
        finally:
            outer.rollback()
    engine.dispose()
