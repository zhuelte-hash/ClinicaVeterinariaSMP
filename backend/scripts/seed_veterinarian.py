"""Crea el veterinario de pruebas sin almacenar su contraseña en el repositorio.

Uso desde el directorio backend:
  VETERINARIAN_PASSWORD='una-clave-local' python scripts/seed_veterinarian.py
"""

import os
import sys
from getpass import getpass
from datetime import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.database import SessionLocal
from app.models.clinic import HorarioVeterinario
from app.models.user import TipoUsuario, Usuario, Veterinario
from app.services.user_service import UserService

EMAIL = "veterinario@sanmartindeporres.test"
NAME = "Veterinario de prueba"
COLLEGIATURA = "PRUEBA-SMP-001"


def main() -> None:
    password = os.environ.get("VETERINARIAN_PASSWORD") or getpass(
        "Contraseña temporal del veterinario (no se guardará en archivos): "
    )
    if not password or len(password) < 8 or len(password) > 72:
        raise SystemExit("VETERINARIAN_PASSWORD debe tener entre 8 y 72 caracteres")

    with SessionLocal() as db:
        user = db.scalar(select(Usuario).where(Usuario.correo == EMAIL))
        if user is not None:
            if user.tipo != TipoUsuario.VETERINARIO:
                raise SystemExit("El correo ya existe con otro rol; no se modificó")
            user.contrasena = UserService(db)._hash_password(password)
            veterinarian = user.veterinario
            if veterinarian is None:
                veterinarian = Veterinario(
                    usuario_id=user.id,
                    colegiatura=COLLEGIATURA,
                    especialidad="Medicina general",
                )
                db.add(veterinarian)
        else:
            user = Usuario(
                nombre=NAME,
                correo=EMAIL,
                contrasena=UserService(db)._hash_password(password),
                tipo=TipoUsuario.VETERINARIO,
            )
            user.veterinario = Veterinario(
                colegiatura=COLLEGIATURA,
                especialidad="Medicina general",
            )
            db.add(user)
            db.flush()
            veterinarian = user.veterinario

        db.flush()
        if veterinarian is None:
            raise SystemExit("No se pudo preparar el perfil veterinario")
        existing_days = set(
            db.scalars(
                select(HorarioVeterinario.dia_semana).where(
                    HorarioVeterinario.veterinario_id == user.id
                )
            ).all()
        )
        for weekday in range(6):
            if weekday not in existing_days:
                db.add(
                    HorarioVeterinario(
                        veterinario_id=user.id,
                        dia_semana=weekday,
                        hora_inicio=time(8),
                        hora_fin=time(19),
                    )
                )
        db.commit()
        print(f"Veterinario listo: {EMAIL}")


if __name__ == "__main__":
    main()
