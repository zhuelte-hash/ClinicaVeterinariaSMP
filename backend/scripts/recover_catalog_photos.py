"""Recupera fotos por nombre exacto desde las tiendas del catálogo; --apply las asocia.

La coincidencia es con la ficha de la tienda, no una verificación visual del envase.
Conserva las imágenes existentes y no modifica precios ni existencias.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
from html.parser import HTMLParser
from io import BytesIO
import json
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.veterinary_catalog_data import DATA, ROOT, PLACEHOLDER, load_catalog

# Cambios de título comprobados en el listado de la misma tienda.
TITLE_ALIASES = {
    'MED-005': 'Vacuna Canino Vanguard Plus 5L4',
    'MED-006': 'Vacuna Canino Sextuple Vanguard 5L4/CV',
    'MED-007': 'Vacuna Cachorros Novibac Puppy Distemper / Parvovirus (4ta Semana)',
    'MED-009': 'Vacuna Tripel Felino - Vanguard Felocell 3',
    'ACC-003': 'JUGUETE PULPO DE PELUCHE',
}


def normalized(value):
    value = unicodedata.normalize('NFKD', value).casefold()
    return ''.join(c for c in value if c.isalnum() and not unicodedata.combining(c))


class Images(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.images = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'img':
            url = attrs.get('data-src') or attrs.get('src')
            if not url or url.startswith('data:'):
                url = (attrs.get('data-srcset') or attrs.get('srcset') or '').split(',')[0].split(' ')[0]
            if url:
                self.images.append((attrs.get('alt', ''), url))


def fetch_page(url):
    try:
        request = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(request, timeout=25) as response:
            html = response.read(5 * 1024 * 1024).decode('utf-8', errors='replace')
        parser = Images()
        parser.feed(html)
        # Fluker entrega su catálogo en el estado SSR, no en etiquetas img.
        if urlsplit(url).hostname in ('www.petshopfluker.com', 'petshopfluker.com'):
            string = r'("(?:[^"\\]|\\.)*")'
            pattern = r'slug:' + string + r',nombre:' + string + r'(?:(?!slug:).)*?imagen:' + string
            for match in re.finditer(pattern, html, re.S):
                _, title, image_url = (json.loads(value) for value in match.groups())
                if image_url.startswith('https://'):
                    parser.images.append((title, image_url))
        return url, parser.images, None
    except Exception as error:
        return url, [], type(error).__name__


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--allow-remote', action='store_true')
    args = parser.parse_args()
    products = load_catalog()
    sources = sorted({p['catalogo_origen']['url_tienda'] for p in products})
    sources.append('https://www.openvet.pe/sistema-de-identificacion/microchips')
    with ThreadPoolExecutor(max_workers=6) as executor:
        pages = {url: (images, error) for url, images, error in executor.map(fetch_page, sources)}
    destination = ROOT / 'frontend' / 'public' / 'catalogo' / 'productos'
    if not destination.is_dir():
        raise ValueError('No existe el directorio público del catálogo')
    report = {'fecha': dt.date.today().isoformat(), 'fotos': {}, 'pendientes': [], 'fuentes_no_disponibles': {url: error for url, (_, error) in pages.items() if error}}
    for product in products:
        source = product['catalogo_origen']
        code = source['codigo']
        if source['fotografia_verificada']:
            continue
        page = source['url_tienda']
        if 'foto descartada' in (source.get('observaciones') or '').casefold():
            report['pendientes'].append({'codigo': code, 'nombre': product['nombre'], 'tienda': page, 'motivo': source['observaciones']})
            continue
        titles = {normalized(product['nombre']), normalized(TITLE_ALIASES.get(code, product['nombre']))}
        candidates = [(source_page, urljoin(source_page, url)) for source_page, (images, _) in pages.items()
                      if urlsplit(source_page).hostname == urlsplit(page).hostname
                      for alt, url in images if normalized(alt) in titles]
        if candidates:
            page, candidate_url = candidates[0]
        else:
            candidate_url = None
        # Los enlaces directos entregados por el propietario también son una fuente.
        image_url = source['url_fotografia'] or candidate_url
        if not image_url:
            report['pendientes'].append({'codigo': code, 'nombre': product['nombre'], 'tienda': page})
            continue
        try:
            if urlsplit(image_url).scheme != 'https':
                raise ValueError('La foto debe usar HTTPS')
            request = Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urlopen(request, timeout=25) as response:
                content = response.read(5 * 1024 * 1024 + 1)
            if len(content) > 5 * 1024 * 1024:
                raise ValueError('La foto supera 5 MB')
            filename = f'{code.lower()}-tienda.webp'
            with Image.open(BytesIO(content)) as image:
                image = ImageOps.exif_transpose(image).convert('RGB')
                image.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
                image.save(destination / filename, 'WEBP', quality=86)
            report['fotos'][product['sku']] = {'codigo': code, 'nombre': product['nombre'], 'archivo': f'/catalogo/productos/{filename}', 'url_origen': image_url, 'pagina_origen': page, 'comprobacion': 'enlace_directo_del_archivo' if source['url_fotografia'] else 'nombre_exacto_en_alt_de_la_tienda', 'presentacion_verificada_visualmente': False}
            print(f'{code}: recuperada')
        except Exception as error:
            report['pendientes'].append({'codigo': code, 'nombre': product['nombre'], 'tienda': page, 'error': type(error).__name__})
    (DATA / 'fotografias_recuperadas.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if args.apply:
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session
        from app.config import get_settings
        import app.models
        from app.models.clinic import Producto
        engine = create_engine(get_settings().database_url, echo=False, pool_pre_ping=True)
        if engine.url.host not in ('localhost', '127.0.0.1', 'database') and not args.allow_remote:
            raise ValueError('La base remota requiere --allow-remote')
        updated = []
        preserved = []
        with Session(engine) as db, db.begin():
            for sku, photo in report['fotos'].items():
                product = db.scalar(select(Producto).where(Producto.sku == sku).execution_options(skip_branch_filter=True).with_for_update())
                if product is None:
                    raise ValueError(f'No existe {sku}')
                if product.imagen_url not in (None, '', PLACEHOLDER, photo['archivo']):
                    preserved.append(sku)
                    continue
                product.imagen_url = photo['archivo']
                product.catalogo_origen = {**(product.catalogo_origen or {}), 'fotografia_recuperada': photo}
                updated.append(sku)
        engine.dispose()
        print(json.dumps({'asociadas': updated, 'imagenes_existentes_conservadas': preserved}))
    print(json.dumps({'recuperadas': len(report['fotos']), 'pendientes': len(report['pendientes']), 'fuentes_no_disponibles': report['fuentes_no_disponibles']}, ensure_ascii=True))


if __name__ == '__main__':
    main()
