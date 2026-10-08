"""Completa los servicios publicados en la web para que puedan reservarse.

Ejecutar desde backend: python scripts/seed_booking_services.py
Solo inserta codigos ausentes; no modifica precios ni servicios existentes.
"""

import sys
from datetime import time
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.database import SessionLocal
from app.models.clinic import HorarioVeterinario, Servicio


# Codigo, nombre publicado, duracion orientativa en minutos.
SERVICES = (
    ("consultas-veterinarias", "Consultas veterinarias", 30),
    ("tratamientos", "Tratamientos", 60),
    ("desparasitacion", "Desparasitación", 30),
    ("vacunacion", "Vacunación", 30),
    ("internamientos", "Internamientos", 60),
    ("profilaxis-dental", "Profilaxis dental", 60),
    ("cirugia-general", "Cirugía general", 90),
    ("cirugia-dental", "Cirugía dental", 90),
    ("laboratorio-clinico", "Laboratorio clínico", 45),
    ("farmacia-veterinaria", "Farmacia veterinaria", 30),
    ("ecografia", "Ecografía", 45),
    ("rayos-x", "Rayos X", 45),
    ("servicio-a-domicilio", "Servicio a domicilio", 60),
    ("hospedaje", "Hospedaje", 60),
    ("microchips", "Microchips", 30),
    ("traumatologia", "Traumatología", 60),
    ("urgencias-24-horas", "Urgencias 24 horas", 30),
    ("bano-medicado", "Baños medicados", 60),
    ("bano-simple", "Baño estético", 60),
    ("cepillado", "Cepillado", 30),
    ("limpieza-de-oidos", "Limpieza de oídos", 30),
    ("limpieza-de-glandulas-anales", "Limpieza de glándulas anales", 30),
    ("aplicacion-de-antipulgas", "Aplicación de antipulgas", 30),
    ("cortes-esteticos", "Cortes estéticos", 90),
    ("corte-y-estilizado", "Corte y estilizado", 90),
    ("corte-de-pelo", "Corte de pelo", 60),
    ("corte-de-unas", "Corte de uñas", 30),
)


def main() -> None:
    with SessionLocal() as db:
        existing_services = {service.codigo: service for service in db.scalars(select(Servicio)).all()}
        existing = set(existing_services)
        # Corregir únicamente las etiquetas antiguas sin sobrescribir nombres personalizados.
        corrections = {
            "bano-simple": ("Bano estetico", "Baño estético"),
            "bano-medicado": ("Bano medicado", "Baño medicado"),
        }
        for code, (old_name, new_name) in corrections.items():
            service = existing_services.get(code)
            if service is not None and service.nombre == old_name:
                service.nombre = new_name
        for code, name, duration in SERVICES:
            if code not in existing:
                db.add(Servicio(codigo=code, nombre=name, duracion_estimada_min=duration,
                               precio_referencial=Decimal("0.00")))
        # Extender únicamente los horarios predeterminados de 08:00 a 19:00.
        schedules = db.scalars(select(HorarioVeterinario).where(
            HorarioVeterinario.hora_inicio == time(8),
            HorarioVeterinario.hora_fin == time(19),
        )).all()
        for schedule in schedules:
            schedule.hora_fin = time(20)
        db.commit()
        print(f"Servicios agregados: {len(SERVICES) - len(existing.intersection(code for code, _, _ in SERVICES))}; horarios ampliados: {len(schedules)}")


if __name__ == "__main__":
    main()
