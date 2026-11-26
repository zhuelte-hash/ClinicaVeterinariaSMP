"""Selecciona WhatsApp por botones conservando las demás variables del entorno."""
import argparse
from pathlib import Path
import sys

from dotenv import dotenv_values, set_key

BACKEND = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Solo comprueba el modo guardado, sin modificarlo.")
    args = parser.parse_args()
    path = BACKEND / ".env"
    if not path.is_file():
        parser.error("Falta backend/.env; configura primero la conexión y SECRET_KEY.")
    if not args.check:
        set_key(str(path), "WHATSAPP_PROVIDER", "manual", quote_mode="always", encoding="utf-8")
    provider = dotenv_values(path, encoding="utf-8").get("WHATSAPP_PROVIDER", "meta")
    if provider != "manual":
        print("El modo guardado aún no es manual. Ejecuta este asistente sin --check.")
        return 1
    print("WHATSAPP_PROVIDER=manual guardado en backend/.env.")
    print("Reinicia API y worker si ya estaban abiertos.")
    print("Comprueba el teléfono institucional en Administración > Configuración.")
    print("El operador abre WhatsApp, pulsa Enviar y adjunta los PDF descargados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
