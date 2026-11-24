"""Comprueba las imágenes públicas del proyecto sin modificar la base de datos."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PLACEHOLDERS = {'', '/logo.png', '/catalogo/producto-sin-foto.svg'}


def get_json(url):
    with urlopen(url, timeout=30) as response:
        return json.load(response)


def check_image(url):
    try:
        with urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=20) as response:
            content = response.read(10 * 1024 * 1024 + 1)
            media = response.headers.get_content_type()
        if len(content) > 10 * 1024 * 1024:
            return {'estado': 'supera_10_mb'}
        if media == 'image/svg+xml' and b'<svg' in content:
            return {'estado': 'ok'}
        with Image.open(BytesIO(content)) as image:
            size = list(image.size)
            image.verify()
        return {'estado': 'ok', 'dimensiones': size}
    except HTTPError as error:
        return {'estado': 'error_http', 'http': error.code}
    except Exception as error:
        return {'estado': 'no_disponible', 'error': type(error).__name__}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api', default='http://localhost:8000')
    parser.add_argument('--frontend', default='http://localhost:4200')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.output.parent.is_dir():
        parser.error('La carpeta de salida debe existir.')
    products = get_json(args.api.rstrip('/') + '/catalogo/productos')
    clinic = get_json(args.api.rstrip('/') + '/publico/institucional')
    references = []

    def add(kind, name, url, **extra):
        path = urlsplit(url).path
        resolved = url if urlsplit(url).scheme else (args.api if path.startswith('/uploads/') else args.frontend).rstrip('/') + '/' + url.lstrip('/')
        references.append({'tipo': kind, 'nombre': name, 'ruta': url, 'url': resolved, **extra})

    for product in products:
        origin = product.get('catalogo_origen') or {}
        add('producto', product['nombre'], product.get('imagen_url') or '',
            sku=product['sku'], id=product['id'],
            sin_foto=(product.get('imagen_url') or '') in PLACEHOLDERS,
            tienda=origin.get('url_tienda'))
    for photo in clinic.get('galeria', []):
        add('instalacion', photo['titulo'], photo['url'])
    # Incluye imágenes literales de inicio, servicios, contacto, blog y paneles.
    for source in sorted((ROOT / 'frontend' / 'src').rglob('*')):
        if source.suffix not in {'.ts', '.html', '.css'}:
            continue
        text = source.read_text(encoding='utf-8')
        urls = set(re.findall(r'https://[^\s\"\'<>`]+', text))
        urls.update(re.findall(r'[\"\'](/[^\"\'<>\s]+\.(?:png|jpg|jpeg|webp|svg))[\"\']', text))
        for url in sorted(urls):
            if re.search(r'\.(?:png|jpe?g|webp|svg)(?:\?|$)|images\.unsplash\.com/', url):
                add('frontend', str(source.relative_to(ROOT)).replace('\\', '/'), url)
    urls = sorted({row['url'] for row in references if row['ruta']})
    with ThreadPoolExecutor(max_workers=8) as executor:
        checks = dict(zip(urls, executor.map(check_image, urls)))
    for row in references:
        row.update(checks.get(row['url'], {'estado': 'sin_ruta'}))
    summary = {
        'productos': len(products),
        'productos_sin_foto': sum(row.get('sin_foto', False) for row in references),
        'fotos_instalaciones': len(clinic.get('galeria', [])),
        'urls_comprobadas': len(urls),
        'urls_con_error': sum(check['estado'] != 'ok' for check in checks.values()),
    }
    report = {'fecha': datetime.now(timezone.utc).isoformat(), 'resumen': summary, 'imagenes': references}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=True))
    for row in references:
        if row.get('sin_foto') or row['estado'] != 'ok':
            print(json.dumps(row, ensure_ascii=True))


if __name__ == '__main__':
    main()
