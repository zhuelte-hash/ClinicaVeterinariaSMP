"""Configura y comprueba SMTP localmente; la clave se introduce oculta."""
import argparse
from getpass import getpass
from pathlib import Path
import smtplib
import ssl
import sys

from dotenv import dotenv_values, set_key
from email_validator import validate_email, EmailNotValidError

BACKEND = Path(__file__).resolve().parents[1]


def smtp_values(address, password, host="smtp.gmail.com", port=587):
    email = validate_email(address.strip(), check_deliverability=False).normalized
    if not password:
        raise ValueError("Falta la clave de aplicación del correo")
    if not host.strip() or not 1 <= port <= 65535:
        raise ValueError("Servidor o puerto SMTP inválido")
    if email.lower().endswith("@gmail.com"):
        password = password.replace(" ", "")
    return {"SMTP_HOST": host.strip(), "SMTP_PORT": str(port), "SMTP_USERNAME": email,
            "SMTP_PASSWORD": password, "MAIL_FROM": email,
            "SMTP_SSL": "true" if port == 465 else "false", "SMTP_STARTTLS": "false" if port == 465 else "true"}


def check_connection(values):
    implicit = values["SMTP_SSL"] == "true"
    client = smtplib.SMTP_SSL if implicit else smtplib.SMTP
    with client(values["SMTP_HOST"], int(values["SMTP_PORT"]), timeout=20) as smtp:
        if not implicit:
            smtp.starttls(context=ssl.create_default_context())
        smtp.login(values["SMTP_USERNAME"], values["SMTP_PASSWORD"])


def save(path, values):
    if not path.is_file():
        raise ValueError("Falta el archivo backend/.env existente")
    for field, value in values.items():
        set_key(str(path), field, value, quote_mode="always", encoding="utf-8")


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    path = BACKEND / ".env"
    if not path.is_file():
        print("Falta backend/.env; configura primero la aplicación.")
        return 1
    current = dotenv_values(path)
    print("Configuración del correo de la clínica. La contraseña se introduce oculta y queda solo en backend/.env.")
    print("Para Gmail usa una contraseña de aplicación de Google: https://myaccount.google.com/apppasswords")
    address = input("Correo remitente (Enter conserva el existente): ").strip() or current.get("SMTP_USERNAME") or ""
    password = getpass("Contraseña de aplicación (oculta; Enter conserva la existente): ").strip() or current.get("SMTP_PASSWORD") or ""
    host, port = "smtp.gmail.com", 587
    if not address.lower().endswith("@gmail.com"):
        host = input("Servidor SMTP: ").strip()
        try:
            port = int(input("Puerto SMTP [587]: ").strip() or "587")
        except ValueError:
            print("Puerto inválido; no se guardaron cambios.")
            return 1
    try:
        values = smtp_values(address, password, host, port)
        print("Comprobando conexión y autenticación, sin enviar mensajes…")
        check_connection(values)
        save(path, values)
    except (EmailNotValidError, ValueError):
        print("Revisa el correo, la clave de aplicación, el servidor y el puerto. No se guardaron cambios.")
        return 1
    except (smtplib.SMTPException, OSError):
        print("No se pudo autenticar el correo. Comprueba la contraseña de aplicación y la conexión. No se guardaron cambios.")
        return 1
    print("SMTP conectado y autenticado. Configuración guardada sin mostrar la clave.")
    print("El lanzador compartido reiniciará la API al detectar el cambio. Si usas otro lanzador, reinicia API y worker.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
