"""Desactiva los productos de ejemplo y los SKU confirmados por el usuario."""
import argparse
import json
from pathlib import Path
import sys

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.config import get_settings
import app.models
from app.models.clinic import Producto
from seed_web_products import PRODUCTS

SAMPLE_SKUS = {
    'ALI-001', 'ALI-002', 'ALI-003', 'HIG-001', 'HIG-002', 'HIG-003',
    'ACC-001', 'ACC-002', 'ACC-003', 'FAR-001', 'FAR-002', 'FAR-003',
    *(row[0] for row in PRODUCTS),
}
REQUESTED_SKUS = {'VET-MED-013', 'VET-ACC-001', 'VET-ACC-002', '355'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    url = get_settings().database_url
    engine = create_engine(url, echo=False, pool_pre_ping=True,
                           connect_args={'connect_timeout': 10} if url.startswith('postgresql') else {})
    try:
        with Session(engine) as db, db.begin():
            db.info['sucursal_id'] = 1
            if engine.dialect.name == 'postgresql':
                db.execute(text("SET LOCAL lock_timeout = '10s'"))
                db.execute(text("SET LOCAL statement_timeout = '20s'"))
            products = db.scalars(select(Producto).where(
                Producto.sucursal_id == 1, Producto.activo,
                Producto.sku.in_(SAMPLE_SKUS | REQUESTED_SKUS),
            ).order_by(Producto.id).with_for_update()).all()
            report = [{'id': p.id, 'sku': p.sku, 'nombre': p.nombre,
                       'motivo': 'ejemplo' if p.sku in SAMPLE_SKUS else 'solicitud_usuario'}
                      for p in products]
            print(json.dumps({'aplicar': args.apply, 'total': len(report), 'productos': report}, ensure_ascii=True))
            if args.apply:
                audit = ROOT / 'data' / 'productos_desactivados_20261124.json'
                if report:
                    # Guarda los identificadores antes de modificar el catálogo.
                    previous = json.loads(audit.read_text(encoding='utf-8')) if audit.exists() else []
                    audit.write_text(json.dumps(previous + report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                for product in products:
                    product.activo = False
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
