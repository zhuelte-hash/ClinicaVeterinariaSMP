"""Asistente local de Twilio: conserva el resto de .env y no imprime el Auth Token."""
import argparse
from getpass import getpass
from pathlib import Path
from types import SimpleNamespace
import sys

from dotenv import dotenv_values, set_key

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.whatsapp_config_service import twilio_missing, twilio_urls

FIELDS = ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_WHATSAPP_FROM", "TWILIO_PUBLIC_URL")


def save_values(path, values):
    if not path.is_file():
        raise ValueError("Falta el archivo backend/.env existente; configura primero la conexión y SECRET_KEY.")
    for name, value in values.items():
        set_key(str(path), name, value, quote_mode="always", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare", action="store_true", help="Selecciona Twilio y agrega solo las claves que falten, sin pedir ni inventar credenciales.")
    mode.add_argument("--public-url", help="Actualiza únicamente el origen HTTPS cuando cambia el túnel.")
    args = parser.parse_args()
    path = BACKEND / ".env"
    if not path.is_file():
        parser.error("Falta backend/.env; no se creará ni reemplazará la configuración de la base de datos.")
    current = dotenv_values(path, encoding="utf-8")
    values = {"WHATSAPP_PROVIDER": "twilio"}
    if args.prepare:
        values.update({name: "" for name in FIELDS if name not in current})
        if not current.get("TWILIO_WHATSAPP_FROM"):
            values["TWILIO_WHATSAPP_FROM"] = "whatsapp:+14155238886"
    elif args.public_url:
        candidate = SimpleNamespace(twilio_account_sid="", twilio_auth_token="", twilio_whatsapp_from="", twilio_public_url=args.public_url.strip())
        invalid = [item for item in twilio_missing(candidate) if item.startswith("TWILIO_PUBLIC_URL")]
        if invalid:
            parser.error(invalid[0])
        values["TWILIO_PUBLIC_URL"] = args.public_url.strip().rstrip("/")
    else:
        print("Abre https://console.twilio.com/ y prepara tu Sandbox de WhatsApp.")
        print("Introduce las credenciales reales de la cuenta; el Auth Token se escribe oculto.")
        values["TWILIO_ACCOUNT_SID"] = input("Account SID (Enter conserva el existente): ").strip() or current.get("TWILIO_ACCOUNT_SID") or ""
        values["TWILIO_AUTH_TOKEN"] = getpass("Auth Token (oculto; Enter conserva el existente): ").strip() or current.get("TWILIO_AUTH_TOKEN") or ""
        default_from = current.get("TWILIO_WHATSAPP_FROM") or "whatsapp:+14155238886"
        values["TWILIO_WHATSAPP_FROM"] = input(f"Emisor del Sandbox [{default_from}]: ").strip() or default_from
        values["TWILIO_PUBLIC_URL"] = (input("Origen HTTPS del túnel (Enter conserva el existente): ").strip() or current.get("TWILIO_PUBLIC_URL") or "").rstrip("/")
        candidate = SimpleNamespace(**{name.lower(): values[name] for name in FIELDS})
        invalid = twilio_missing(candidate)
        if invalid:
            parser.error("No se guardaron cambios. Completa/corrige: " + ", ".join(invalid))
    save_values(path, values)
    print("Configuración de Twilio guardada en backend/.env; las otras claves se conservaron.")
    configured = {**current, **values}
    if configured.get("TWILIO_PUBLIC_URL"):
        candidate = SimpleNamespace(twilio_public_url=configured["TWILIO_PUBLIC_URL"])
        for label, url in twilio_urls(candidate).items():
            print(f"Webhook {label} (POST): {url}")
    print("Reinicia API y worker. Diagnóstico: .\\.venv\\Scripts\\python.exe scripts/check_communications.py")
    print("Guarda el webhook en Twilio, vincula tu teléfono con join y envía hola antes de la prueba.")


if __name__ == "__main__":
    main()
