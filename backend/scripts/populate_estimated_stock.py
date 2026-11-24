"""Carga solicitada de existencias estimadas, identificadas como demostración.

No registra compras ni costos inventados. Conserva lotes y movimientos del kardex.
Por defecto muestra el plan; --apply lo registra una sola vez por producto.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import sys

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.config import get_settings
import app.models
from app.models.clinic import Producto
from app.models.operations import LoteInventario
from app.services.inventory_service import InventoryService

REFERENCE = 'STOCK-ESTIMADO-20261124'
MARKER = 'carga_stock_estimada_20261124'


def stock_plan(product, today):
    group, number = product.sku.removeprefix('VET-').split('-')
    index = int(number)
    if group == 'MED':
        low, high, minimum = (10, 18, 4) if 5 <= index <= 9 else (6, 12, 3)
    elif group == 'ANT':
        low, high, minimum = 8, 15, 3
    elif group == 'HIG':
        low, high, minimum = (15, 24, 5) if index >= 3 else (10, 16, 4)
    elif group == 'ACC':
        low, high, minimum = 10, 18, 4
    elif group in ('PER', 'GAT'):
        dry = (group == 'PER' and index in (3, 4, 5)) or (group == 'GAT' and index in (1, 2, 3, 7, 8))
        low, high, minimum = (12, 20, 5) if dry else (18, 30, 6)
    else:
        raise ValueError(f'Grupo no contemplado: {product.sku}')
    quantity = low + (index * 2 + product.id) % (high - low + 1)
    expiry = today + dt.timedelta(days=365 + index * 9) if product.requiere_vencimiento else None
    return quantity, minimum, expiry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    url = get_settings().database_url
    engine = create_engine(url, echo=False, pool_pre_ping=True,
                           connect_args={'connect_timeout': 10, 'keepalives': 1, 'keepalives_idle': 20,
                                         'keepalives_interval': 10, 'keepalives_count': 3} if url.startswith('postgresql') else {})
    today = dt.date.today()
    try:
        with Session(engine) as db, db.begin():
            db.info['sucursal_id'] = 1
            if engine.dialect.name == 'postgresql':
                db.execute(text("SET LOCAL lock_timeout = '10s'"))
                db.execute(text("SET LOCAL statement_timeout = '30s'"))
            products = db.scalars(select(Producto).where(Producto.activo, Producto.sucursal_id == 1)
                                 .order_by(Producto.id).with_for_update()).all()
            if len(products) != 47 or any(not p.sku.startswith('VET-') for p in products):
                raise ValueError('El catálogo activo ya no coincide con los 47 productos revisados.')
            pending = [p for p in products if not (p.catalogo_origen or {}).get(MARKER)]
            if any(p.stock_actual != 0 for p in pending):
                raise ValueError('Hay existencias previas; revisa el inventario antes de agregar cantidades estimadas.')
            report = []
            service = InventoryService(db)
            for product in pending:
                quantity, minimum, expiry = stock_plan(product, today)
                record = {
                    'sku': product.sku, 'nombre': product.nombre, 'stock_anterior': 0,
                    'stock_nuevo': quantity, 'stock_minimo': minimum,
                    'unidad': product.unidad_medida, 'lote': f'DEMO-20261124-{product.sku}',
                    'vencimiento_ejemplo': expiry.isoformat() if expiry else None,
                    'cantidades_estimadas': True, 'vencimiento_ficticio': expiry is not None,
                    'referencia': REFERENCE,
                }
                report.append(record)
                if args.apply:
                    product.stock_minimo = minimum
                    product.es_demostracion = True
                    product.catalogo_origen = {**(product.catalogo_origen or {}), MARKER: record}
                    service.increase(product, quantity,
                        'Existencias estimadas por solicitud del usuario; lote y vencimiento de ejemplo, sin compra real',
                        kind='ingreso', lot_code=record['lote'], expiry=expiry, reference=REFERENCE)
                    print(f'{product.sku}: {quantity} unidades preparadas', flush=True)
            if args.apply:
                db.flush()
                for product in products:
                    lots = db.scalar(select(func.coalesce(func.sum(LoteInventario.cantidad), 0))
                                     .where(LoteInventario.producto_id == product.id))
                    sellable = db.scalar(select(func.coalesce(func.sum(LoteInventario.cantidad), 0)).where(
                        LoteInventario.producto_id == product.id,
                        LoteInventario.vencimiento >= today if product.requiere_vencimiento
                        else (LoteInventario.vencimiento.is_(None) | (LoteInventario.vencimiento >= today))))
                    if lots != product.stock_actual or sellable != product.stock_actual or product.stock_actual <= product.stock_minimo:
                        raise ValueError(f'Stock y lotes inconsistentes: {product.sku}')
                if report:
                    (ROOT / 'data' / 'stock_estimado_20261124.json').write_text(
                        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            print(json.dumps({'aplicado': args.apply, 'productos_cargados': len(report),
                              'unidades_cargadas': sum(row['stock_nuevo'] for row in report),
                              'productos': report}, ensure_ascii=True), flush=True)
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
