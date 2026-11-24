"""Integraciones nativas del seed y SQL, exclusivamente en PostgreSQL local test_*."""
import os
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import String, create_engine, delete, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.models.clinic import CategoriaProducto, Producto
from app.models.operations import Egreso, EventoAuditoria, LoteInventario, MovimientoInventario
from app.services.veterinary_catalog_data import load_catalog, render_sql
from app.services.veterinary_catalog_import import import_catalog, preview_catalog, require_demo_database


@pytest.fixture
def catalog_pg():
    url = os.getenv('TEST_DATABASE_URL')
    if not url:
        pytest.skip('Requiere PostgreSQL local test_*')
    require_demo_database(make_url(url))
    engine = create_engine(url, echo=False)
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode='create_savepoint') as db:
            yield db, engine
        transaction.rollback()
    engine.dispose()


def test_native_seed_nulls_idempotency_and_rollback(catalog_pg):
    db, _ = catalog_pg
    first = import_catalog(db, load_catalog())
    db.commit()
    assert len(first['insertados']) == 50
    product = db.scalar(select(Producto).where(Producto.sku == 'VET-MED-003'))
    assert product.precio_venta is product.proveedor_id is None
    assert product.catalogo_origen['precio_compra'] is None
    assert product.stock_actual == 0
    assert not import_catalog(db, load_catalog())['insertados']
    assert db.scalar(select(func.count()).select_from(LoteInventario).where(LoteInventario.producto_id == product.id)) == 0
    assert db.scalar(select(func.count()).select_from(Egreso)) == 0


def test_native_demo_lots_are_traceable_and_not_repeated(catalog_pg):
    db, _ = catalog_pg
    import_catalog(db, load_catalog(), demo=True)
    db.commit()
    rows = db.scalars(select(Producto).where(Producto.es_demostracion)).all()
    assert len(rows) == 50
    for product in rows:
        lot = db.scalar(select(LoteInventario).where(LoteInventario.producto_id == product.id))
        assert lot.cantidad == product.stock_actual == product.catalogo_origen['stock_inicial']
        assert lot.codigo == f'DEMO-20261123-{product.sku}'
        movement = db.scalar(select(MovimientoInventario).where(MovimientoInventario.producto_id == product.id))
        assert movement.saldo_anterior == 0 and movement.saldo_nuevo == lot.cantidad
    assert not import_catalog(db, load_catalog(), demo=True)['insertados']
    assert db.scalar(select(func.count()).select_from(MovimientoInventario).where(MovimientoInventario.producto_id.in_(select(Producto.id).where(Producto.es_demostracion)))) == 50
    assert db.scalar(select(func.count()).select_from(Egreso)) == 0


def test_exported_sql_matches_python_normalization_and_is_repeatable(catalog_pg):
    db, _ = catalog_pg
    # Ejecutar el SQL íntegro bajo savepoint, sin su BEGIN/COMMIT exterior.
    sql = render_sql(load_catalog()).replace('BEGIN;\nSET LOCAL', 'SET LOCAL', 1).removesuffix('COMMIT;\n')
    db.execute(text(sql))
    db.expire_all()
    for record in load_catalog():
        product = db.scalar(select(Producto).where(Producto.sku == record['sku']))
        assert product.nombre == record['nombre']
        assert product.precio_venta == record['precio_venta']
        assert product.marca == record['marca']
        assert product.especies == record['especies']
        assert product.catalogo_origen == record['catalogo_origen']
        assert product.stock_actual == product.costo_unitario == 0
    db.execute(text(sql))
    assert db.scalar(select(func.count()).select_from(Producto).where(Producto.sku.like('VET-%'))) == 50
    assert db.scalar(select(func.count()).select_from(EventoAuditoria).where(EventoAuditoria.entidad == 'productos', EventoAuditoria.registro_id.in_(select(Producto.id.cast(String)).where(Producto.sku.like('VET-%'))))) == 50


def test_dry_run_in_read_only_transaction_changes_nothing(catalog_pg):
    _, engine = catalog_pg
    with Session(engine) as db:
        db.execute(text('SET TRANSACTION READ ONLY'))
        report = preview_catalog(db, load_catalog())
        assert len(report['por_insertar']) == 50
        assert db.scalar(select(func.count()).select_from(Producto).where(Producto.sku.like('VET-%'))) == 0
        db.rollback()


def test_two_concurrent_seeds_preserve_one_product_and_one_category(catalog_pg):
    _, engine = catalog_pg
    record = deepcopy(load_catalog()[0])
    record['sku'] = f'TEST-CAT-{uuid4().hex[:16]}'
    record['categoria_nombre'] = f'Test categoría {uuid4().hex[:16]}'
    sku = record['sku']

    def run():
        with Session(engine) as db:
            report = import_catalog(db, [record])
            db.commit()
            return len(report['insertados'])

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(lambda _: run(), range(2))) == [0, 1]
        with Session(engine) as db:
            assert db.scalar(select(func.count()).select_from(Producto).where(Producto.sku == sku)) == 1
            assert db.scalar(select(func.count()).select_from(CategoriaProducto).where(CategoriaProducto.nombre == record['categoria_nombre'])) == 1
    finally:
        with Session(engine) as db:
            product = db.scalar(select(Producto).where(Producto.sku == sku))
            if product:
                db.execute(delete(EventoAuditoria).where(EventoAuditoria.entidad == 'productos', EventoAuditoria.registro_id == str(product.id)))
                db.execute(delete(Producto).where(Producto.id == product.id))
                db.execute(delete(CategoriaProducto).where(CategoriaProducto.id == product.categoria_id))
                db.commit()
