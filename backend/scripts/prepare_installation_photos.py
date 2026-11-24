"""Optimiza las fotos aportadas en frontend/public; --publish las agrega a la galería."""
import argparse
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


PHOTOS = [
    ('ima9.png', 'equipo-en-la-clinica', 'Nuestro equipo en las instalaciones de la clínica'),
    ('ima8.png', 'tienda-y-alimentos', 'Tienda y alimentos para el bienestar de tu mascota'),
    ('imgen1.png', 'atencion-pastor-aleman', 'Atención cercana para nuestros pacientes'),
    ('ima2.png', 'equipo-san-martin', 'El equipo de San Martín de Porres'),
    ('ima3.png', 'cuidado-en-consultorio', 'Cuidado y compañía en el consultorio'),
    ('ima4.png', 'grooming-pastor-aleman', 'Un momento después del cuidado y aseo'),
    ('ima5.png', 'grooming-mascota', 'Nuestros pequeños visitantes después de su aseo'),
    ('ima6.png', 'atencion-con-carino', 'Atención con cariño en cada visita'),
    ('ima7.png', 'cuidado-y-bienestar', 'Cuidado y bienestar para nuestros compañeros'),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    backend = Path(__file__).resolve().parents[1]
    source = backend.parent / 'frontend' / 'public'
    destination = backend / 'assets' / 'instalaciones'
    destination.mkdir(parents=True, exist_ok=True)
    total_before = total_after = 0
    for original, name, title in PHOTOS:
        path = source / original
        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image).convert('RGB')
            # Retira el encabezado de la captura sin cortar al personal ni a la mascota.
            if original == 'ima4.png':
                image = image.crop((3, 28, image.width, image.height))
            image.thumbnail((1400, 1400), Image.Resampling.LANCZOS)
            image = ImageEnhance.Contrast(image).enhance(1.02)
            image = image.filter(ImageFilter.UnsharpMask(radius=1, percent=45, threshold=3))
            output = destination / f'{name}.jpg'
            image.save(output, 'JPEG', quality=88, optimize=True, progressive=True)
        total_before += path.stat().st_size
        total_after += output.stat().st_size
        print(f'{output.name}: {output.stat().st_size // 1024} KB')
        if args.publish:
            subprocess.run([
                sys.executable, str(backend / 'scripts' / 'publish_installation_photo.py'),
                str(output), '--title', title,
            ], cwd=backend, check=True)
    print(f'Total: {total_before // 1024} KB -> {total_after // 1024} KB')


if __name__ == '__main__':
    main()
