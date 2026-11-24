"""Valida el catálogo sin conexión. --dry-run simula; --apply importa expresamente."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.veterinary_catalog_data import DATA, load_catalog, render_sql


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--apply', action='store_true')
    parser.add_argument('--allow-remote', action='store_true', help='Permitir escritura remota solo con autorización del propietario')
    parser.add_argument('--demo', action='store_true', help='Stock ficticio: solo base PostgreSQL local test_*')
    parser.add_argument('--sucursal-id', type=int, default=1)
    parser.add_argument('--sku', help='Importar solo este código original o SKU VET-, por ejemplo PER-007')
    parser.add_argument('--export-sql', type=Path)
    args = parser.parse_args()
    try:
        if args.sucursal_id < 1:
            raise ValueError('La sede debe ser positiva')
        products = load_catalog()
        print(f'Catálogo válido: {len(products)} productos, {sum(p["precio_venta"] is None for p in products)} precios pendientes; stock de origen ficticio.')
        if args.sku:
            code = args.sku.strip().upper()
            products = [product for product in products if code in (product['sku'], product['catalogo_origen']['codigo'])]
            if len(products) != 1:
                raise ValueError('El código solicitado no identifica un único producto del catálogo')
            print(f'Seleccionado únicamente: {products[0]["sku"]}')
        if args.export_sql:
            if args.demo:
                raise ValueError('El SQL exportado solo admite catálogo sin existencias')
            args.export_sql.write_text(render_sql(products, args.sucursal_id), encoding='utf-8')
            print('SQL generado; no ejecutado.')
        if not (args.apply or args.dry_run):
            print('Validación sin conexión terminada. No se abrió una conexión a la base de datos.')
            return 0
        # Importaciones diferidas: validar/exportar no lee .env ni crea el engine.
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import Session
        from app.config import get_settings
        import app.models
        from app.services import audit_service
        from app.services.veterinary_catalog_import import import_catalog, preview_catalog, require_demo_database
        engine = create_engine(get_settings().database_url, echo=False, pool_pre_ping=True)
        local = engine.url.host in ('localhost', '127.0.0.1', 'database')
        if args.apply and not local and not args.allow_remote:
            raise ValueError('Escritura remota bloqueada: requiere --allow-remote y autorización previa')
        if args.demo:
            require_demo_database(engine.url)
        with Session(engine) as db:
            try:
                if args.apply:
                    report = import_catalog(db, products, args.sucursal_id, demo=args.demo)
                    db.commit()
                else:
                    db.execute(text('SET TRANSACTION READ ONLY'))
                    report = preview_catalog(db, products, args.sucursal_id)
                    db.rollback()
                print(json.dumps({**report, 'aplicado': args.apply}, ensure_ascii=True))
            except Exception:
                db.rollback()
                raise
        engine.dispose()
        return 0
    except (ValueError, KeyError) as error:
        print(f'Validación rechazada ({type(error).__name__}). Revisa archivos, sede y opciones; stock demo exige PostgreSQL local test_*.', file=sys.stderr)
        return 1
    except Exception as error:
        # No incluir URL, parámetros SQL ni credenciales en errores del proveedor.
        print(f'Importación detenida ({type(error).__name__}). Revisa conectividad y migraciones; transacción revertida.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
