"""Descarga candidatas para revisión visual; no las declara verificadas ni toca BD."""
import argparse
from io import BytesIO
from pathlib import Path
import sys
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.veterinary_catalog_data import load_catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verified-only', action='store_true', help='Descargar solo las fotos revisadas en el manifiesto')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for product in load_catalog(check_photo_files=False):
        if args.verified_only and not product['catalogo_origen']['fotografia_verificada']:
            continue
        url = product['catalogo_origen']['url_fotografia']
        if not url:
            continue
        if urlsplit(url).scheme != 'https' or urlsplit(url).hostname != 'cdnx.jumpseller.com':
            raise ValueError('Origen de fotografía no permitido')
        try:
            request = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urlopen(request, timeout=25) as response:
                if urlsplit(response.url).hostname != 'cdnx.jumpseller.com':
                    raise ValueError('Redirección de fotografía no permitida')
                content = response.read(5 * 1024 * 1024 + 1)
                if len(content) > 5 * 1024 * 1024:
                    raise ValueError('Imagen demasiado grande')
            with Image.open(BytesIO(content)) as image:
                image = ImageOps.exif_transpose(image).convert('RGB')
                image.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
                image.save(args.output / f'{product["catalogo_origen"]["codigo"].lower()}.webp', 'WEBP', quality=86)
            print(f'{product["sku"]}: candidata descargada; requiere revisión visual')
        except Exception as error:
            print(f'{product["sku"]}: no descargada ({type(error).__name__}); usar reemplazo local')


if __name__ == '__main__':
    main()
