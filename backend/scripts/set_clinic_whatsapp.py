"""Actualiza solo el teléfono institucional, conservando las demás preferencias."""
import argparse
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
import app.models
from app.models.clinic import ConfiguracionClinica
from app.services.whatsapp_config_service import normalized_phone


def set_phone(db, phone):
    if not re.fullmatch(r"[1-9]\d{9,14}", normalized_phone(phone)):
        raise ValueError("Indica un teléfono válido, con código de país si no es de Perú.")
    clinic = db.scalar(select(ConfiguracionClinica).order_by(ConfiguracionClinica.id).with_for_update())
    if clinic is None:
        clinic = ConfiguracionClinica(nombre="Clínica Veterinaria SMP", correo="", direccion="", telefono=phone)
        db.add(clinic)
    else:
        clinic.telefono = phone
    db.commit()
    return normalized_phone(phone)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phone")
    args = parser.parse_args()
    phone = args.phone.strip()
    if not re.fullmatch(r"[1-9]\d{9,14}", normalized_phone(phone)):
        parser.error("Teléfono inválido")
    url = get_settings().database_url
    engine = create_engine(url, echo=False, connect_args={"connect_timeout": 10} if url.startswith("postgresql") else {})
    try:
        with Session(engine) as db:
            number = set_phone(db, phone)
        print(f"WhatsApp institucional guardado: {phone}. Enlace: https://wa.me/{number}")
    except SQLAlchemyError:
        print("No se pudo actualizar la base de datos. Comprueba su disponibilidad y vuelve a ejecutar este comando.")
        return 1
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
