"""Descarga y asocia una foto proporcionada para un SKU existente del catálogo."""
import argparse
import datetime as dt
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from PIL import Image, ImageOps
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.config import get_settings
import app.models
from app.models.clinic import Producto


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sku', nargs='?')
    parser.add_argument('url', nargs='?')
    parser.add_argument('--batch', type=Path, help='JSON con SKU, URL y el indicador aplicar')
    args = parser.parse_args(argv)
    if args.batch:
        rows = json.loads(args.batch.read_text(encoding='utf-8'))
        errors = []
        for row in rows:
            if not row.get('aplicar'):
                continue
            try:
                main([row['sku'], row['url']])
            except Exception as error:
                print(f"{row['sku']}: error {type(error).__name__}", flush=True)
                errors.append(row['sku'])
        if errors:
            raise RuntimeError('No se pudieron cargar: ' + ', '.join(errors))
        return
    if not args.sku or not args.url:
        parser.error('Indica SKU y URL, o un archivo --batch.')
    sku = args.sku.upper()
    if urlsplit(args.url).scheme != 'https':
        parser.error('La imagen debe usar HTTPS.')
    destination = ROOT / 'frontend' / 'public' / 'catalogo' / 'productos'
    if not destination.is_dir():
        parser.error('Falta la carpeta pública de fotos del catálogo.')
    database_url = get_settings().database_url
    connect_args = {'connect_timeout': 10} if database_url.startswith('postgresql') else {}
    engine = create_engine(database_url, echo=False, pool_pre_ping=True, connect_args=connect_args)
    try:
        print(f'{sku}: consultando producto...', flush=True)
        with Session(engine) as db, db.begin():
            if engine.dialect.name == 'postgresql':
                db.execute(text("SET LOCAL lock_timeout = '10s'"))
                db.execute(text("SET LOCAL statement_timeout = '20s'"))
            product = db.scalar(select(Producto).where(Producto.sku == sku).execution_options(skip_branch_filter=True).with_for_update())
            if product is None or not sku.startswith('VET-'):
                parser.error('No existe ese SKU del catálogo veterinario.')
            print(f'{sku}: descargando imagen...', flush=True)
            with urlopen(Request(args.url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30) as response:
                content = response.read(5 * 1024 * 1024 + 1)
            if not content or len(content) > 5 * 1024 * 1024:
                parser.error('La foto debe pesar entre 1 byte y 5 MB.')
            filename = f'{sku.lower()}-{hashlib.sha256(content).hexdigest()[:12]}.webp'
            with Image.open(BytesIO(content)) as image:
                image = ImageOps.exif_transpose(image)
                image.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
                image.convert('RGB').save(destination / filename, 'WEBP', quality=90)
            photo = {
                'codigo': sku.removeprefix('VET-'), 'nombre': product.nombre,
                'archivo': f'/catalogo/productos/{filename}', 'url_origen': args.url,
                'fecha': dt.date.today().isoformat(),
                'comprobacion': 'enlace_directo_proporcionado_por_usuario',
            }
            product.imagen_url = photo['archivo']
            product.catalogo_origen = {**(product.catalogo_origen or {}), 'fotografia_manual': photo}
        manifest = ROOT / 'data' / 'fotografias_manuales.json'
        photos = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {}
        photos[sku] = photo
        manifest.write_text(json.dumps(photos, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'sku': sku, **photo}, ensure_ascii=True))
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
