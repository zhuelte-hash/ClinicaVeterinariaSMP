"""Catálogo comercial: datos reales, NULL, seed y flujos HTTP en SQLite aislada."""
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import make_url

from test_admin_clinical_flows import clinic
from test_priority_stories import operations, proof
from test_eleven_partial_stories import receive
from app.config import get_settings
from app.models.clinic import Producto, OrdenCobro
from app.models.operations import CompraProveedor, Egreso, LoteInventario, MovimientoInventario, Sucursal
from app.models.purchase import PedidoWeb
from app.services.veterinary_catalog_data import DATA, PLACEHOLDER, load_catalog, render_sql
from app.services.veterinary_catalog_import import import_catalog, preview_catalog, require_demo_database


def seeded(db):
    report = import_catalog(db, load_catalog())
    db.commit()
    return report, {p.catalogo_origen['codigo'] if p.catalogo_origen else p.sku: p for p in db.scalars(select(Producto)).all()}


def test_catalog_sources_preserve_unknown_and_fictional_values():
    products = load_catalog()
    assert len(products) == 50
    assert {p['sku'] for p in products if p['precio_venta'] is None} == {'VET-MED-003', 'VET-MED-011', 'VET-MED-012', 'VET-MED-013'}
    assert sum(p['imagen_url'] != PLACEHOLDER for p in products) == 4
    assert all(p['catalogo_origen']['stock_demostracion'] for p in products)
    assert next(p for p in products if p['sku'] == 'VET-ACC-003')['marca'] is None
    assert next(p for p in products if p['sku'] == 'VET-MED-002')['catalogo_origen']['especie'] is None
    assert next(p for p in products if p['sku'] == 'VET-PER-003')['unidad_medida'] == 'unidad'
    assert next(p for p in products if p['sku'] == 'VET-PER-006')['categoria_nombre'] == 'Alimento medicado'


def test_seed_preserves_existing_products_and_creates_no_physical_stock(clinic):
    _, db, *_ = clinic
    report, products = seeded(db)
    assert len(report['insertados']) == 50
    product = products['MED-001']
    product.precio_venta = Decimal('99.25'); product.activo = False
    db.commit()
    again, products = seeded(db)
    assert not again['insertados'] and len(again['conservados']) == 50
    assert product.precio_venta == Decimal('99.25') and not product.activo
    assert all(p.stock_actual == p.costo_unitario == 0 and p.proveedor_id is None for p in products.values())
    assert all(not p.es_demostracion for p in products.values())
    for model in (LoteInventario, MovimientoInventario, CompraProveedor, Egreso, OrdenCobro):
        assert db.scalar(select(func.count()).select_from(model)) == 0


def test_preview_performs_no_inserts_and_cross_branch_sku_is_rejected(clinic):
    _, db, *_ = clinic
    report = preview_catalog(db, load_catalog())
    assert len(report['por_insertar']) == 50 and not db.new
    seeded(db)
    db.add(Sucursal(id=2, nombre='Otra sede')); db.commit()
    with pytest.raises(ValueError, match='otra sede'):
        import_catalog(db, load_catalog(), branch=2)
    db.rollback()
    assert db.scalar(select(func.count()).select_from(Producto)) == 50


def test_null_price_is_returned_without_becoming_zero_and_filters_exclude_unknown_species(operations):
    http, db, headers, *_ = operations
    _, products = seeded(db)
    unknown = products['MED-003']
    row = http.get(f'/catalogo/productos/{unknown.id}').json()
    assert row['precio_venta'] is None and row['proveedor_id'] is None
    assert row['marca'] == 'Cardial' and row['presentacion'] == '5 mg; cantidad no publicada'
    assert row['imagen_url'] == PLACEHOLDER
    assert unknown.id not in {p['id'] for p in http.get('/catalogo/productos', params={'precio_min': 0}).json()}
    assert products['MED-002'].id not in {p['id'] for p in http.get('/catalogo/productos', params={'especie': 'Perro'}).json()}
    assert unknown.id not in {p['id'] for p in http.get('/caja/productos', headers=headers[5]).json()}
    assert unknown.id not in {p['id'] for p in http.get('/operaciones/catalogo', headers=headers[5]).json()['productos']}


def test_null_price_cannot_be_sold_or_quoted_even_via_direct_api(operations):
    http, db, headers, *_ = operations
    _, products = seeded(db)
    product = products['MED-003']
    product.stock_actual = 3  # Aunque un cliente eluda la interfaz y haya stock.
    db.commit()
    sale = http.post('/api/ventas', headers=headers[5], json={'medio_pago': 'efectivo', 'items': [{'producto_id': product.id, 'cantidad': 1}], 'clave_idempotencia': str(uuid4())})
    assert sale.status_code in (409, 422), sale.text
    order = http.post('/operaciones/ordenes', headers=headers[5], json={'cliente_id': 1, 'detalles': [{'producto_id': product.id, 'cantidad': 1}], 'clave_idempotencia': str(uuid4())})
    assert order.status_code == 422 and 'precio' in order.json()['detail']
    assert db.scalar(select(func.count()).select_from(OrdenCobro)) == 0
    assert db.get(Producto, product.id).stock_actual == 3


def test_web_order_rejects_unknown_price_before_creating_payment(operations, monkeypatch):
    http, db, headers, *_ = operations
    _, products = seeded(db)
    settings = get_settings()
    for field in ('purchase_yape_holder', 'purchase_yape_phone', 'purchase_yape_qr_url'):
        monkeypatch.setattr(settings, field, 'SOLO-PRUEBAS')
    product = products['MED-003']
    data = {'clave_idempotencia': str(uuid4()), 'cliente': {'nombreCompleto': 'Cliente prueba', 'celular': '999999999', 'tipoEntrega': 'Recojo en clínica', 'dni': '12345678'},
            'items': [{'producto_id': product.id, 'cantidad': 1}], 'metodo_pago': 'yape', 'numero_operacion': 'OP-TEST', 'total_esperado': '1.00'}
    response = http.post('/pedidos-web', headers=headers[1], data={'datos': json.dumps(data)}, files={'comprobante': ('test.png', proof(), 'image/png')})
    assert response.status_code == 409 and 'precio' in response.json()['detail'], response.text
    assert db.scalar(select(func.count()).select_from(PedidoWeb)) == 0


def test_commercial_fields_can_be_completed_and_unknown_values_remain_null(operations):
    http, db, headers, *_ = operations
    _, products = seeded(db)
    product = products['ACC-003']
    response = http.patch(f'/admin/productos/{product.id}', headers=headers[4], json={'marca': ' ', 'presentacion': '1 unidad', 'proveedor_id': None, 'precio_venta': None})
    assert response.status_code == 200, response.text
    assert response.json()['marca'] is None and response.json()['precio_venta'] is None
    assert http.patch(f'/admin/productos/{product.id}', headers=headers[4], json={'precio_venta': '12.50', 'proveedor_id': 1}).status_code == 200
    assert db.get(Producto, product.id).precio_venta == Decimal('12.50')


def test_seeded_medicine_requires_real_receipt_and_sale_tracks_lot_and_return(operations):
    http, db, headers, *_ = operations
    _, products = seeded(db)
    product = products['MED-001']
    assert receive(http, headers[4], product.id, document='SIN-FECHA', vencimiento=None).status_code == 422
    received = receive(http, headers[4], product.id, document='REAL-TEST')
    assert received.status_code == 201, received.text
    assert product.stock_actual == 2 and product.costo_unitario == 3
    assert receive(http, headers[4], product.id, document='REAL-TEST').status_code == 409
    response = http.post('/api/ventas', headers=headers[5], json={'medio_pago': 'efectivo', 'items': [{'producto_id': product.id, 'cantidad': 1}], 'clave_idempotencia': str(uuid4())})
    assert response.status_code == 201, response.text
    assert product.stock_actual == 1
    sale = response.json()
    returned = http.post(f'/operaciones/ventas/{sale["orden_id"]}/anular', headers=headers[4], json={'motivo': 'Devolución de prueba'})
    assert returned.status_code == 200, returned.text
    assert product.stock_actual == 2
    movements = http.get(f'/admin/operaciones/kardex/{product.id}', headers=headers[4]).json()
    assert {row['tipo'] for row in movements} == {'compra', 'venta', 'devolucion'}
    assert sum(Decimal(str(row['cantidad'])) for row in movements) == 2
    assert product.catalogo_origen['precio_compra'] == '49.0'  # No sustituye el costo real 3.


@pytest.mark.parametrize('url', ['postgresql://user:secret@demo.neon.tech/test_clinica', 'postgresql://user:secret@localhost/clinica', 'sqlite://'])
def test_demo_stock_is_blocked_outside_isolated_local_postgres(url):
    with pytest.raises(ValueError, match='local test_'):
        require_demo_database(make_url(url))


def test_sql_export_is_reproducible_and_does_not_recreate_tables():
    sql = render_sql(load_catalog())
    assert (DATA / 'importar_productos_neon.sql').read_text(encoding='utf-8') == sql
    assert 'CREATE TABLE' not in sql and 'DROP TABLE' not in sql and 'DELETE FROM' not in sql
    assert 'LOCK TABLE' in sql and 'RAISE EXCEPTION' in sql


@pytest.mark.parametrize('sku', ['PER-007', 'VET-PER-007', 'NO-EXISTE'])
def test_cli_single_product_cannot_export_or_import_the_whole_catalog_by_mistake(tmp_path, sku):
    backend = Path(__file__).resolve().parents[1]
    output = tmp_path / 'single-product.sql'
    result = subprocess.run([sys.executable, str(backend / 'scripts' / 'seed_veterinary_products.py'),
                             '--sku', sku, '--export-sql', str(output)], cwd=backend,
                            env={**os.environ, 'DATABASE_URL': 'invalid-url-offline-validation'}, capture_output=True, text=True)
    if sku == 'NO-EXISTE':
        assert result.returncode == 1 and not output.exists()
    else:
        assert result.returncode == 0, result.stderr
        sql = output.read_text(encoding='utf-8')
        assert sql.count('"sku":') == 1 and 'VET-PER-007' in sql
        assert 'VET-PER-008' not in sql
