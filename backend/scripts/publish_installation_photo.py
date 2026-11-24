"""Publica una fotografía local en la galería del entorno configurado en backend/.env."""
import argparse
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal, engine
import app.models  # Registra las relaciones ORM antes de consultar políticas.
from app.schemas.operations import GalleryPhoto, GalleryWrite
from app.services.policy_service import PolicyService
from app.services.purchase_service import validate_proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('photo', type=Path)
    parser.add_argument('--title', required=True)
    args = parser.parse_args()
    if args.photo.stat().st_size > 5 * 1024 * 1024:
        parser.error('La fotografía no puede superar 5 MB.')
    content = args.photo.read_bytes()
    media, extension = validate_proof(content)
    if media not in ('image/jpeg', 'image/png'):
        parser.error('Selecciona una fotografía JPG o PNG.')
    filename = f'{hashlib.sha256(content).hexdigest()}.{extension}'
    photo = GalleryPhoto(url=f'/uploads/instalaciones/{filename}', titulo=args.title)
    directory = Path(__file__).resolve().parents[1] / 'uploads' / 'instalaciones'
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / filename
    # No imprimir consultas con datos de configuración del entorno.
    engine.echo = False
    with SessionLocal() as db:
        service = PolicyService(db)
        current = service.get()
        photos = list(current.galeria)
        for index, existing in enumerate(photos):
            if existing.url == photo.url:
                photos[index] = photo
                break
        else:
            photos.append(photo)
        data = GalleryWrite(galeria=photos)
        destination.write_bytes(content)
        saved = service.save_fields(data)
    print(f'Fotografía publicada. Galería: {len(saved.galeria)} fotografía(s).')
    print(photo.url)


if __name__ == '__main__':
    main()
