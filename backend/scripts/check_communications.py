"""Diagnóstico de HU-002/004/036/050/098, sin enviar mensajes ni mostrar secretos."""
import argparse
from pathlib import Path
import smtplib
import ssl
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-smtp", action="store_true", help="Comprueba conexión, TLS y autenticación SMTP, sin enviar correo.")
    args = parser.parse_args()
    settings = get_settings()
    required = {
        "Correo (HU-002/HU-004)": ("smtp_host", "mail_from"),
        "WhatsApp (HU-036/HU-050/HU-098)": ("whatsapp_phone_number_id", "whatsapp_access_token"),
        "Webhook de entrega": ("whatsapp_app_secret", "whatsapp_verify_token"),
    }
    ready = True
    for label, fields in required.items():
        missing = [field.upper() for field in fields if not getattr(settings, field)]
        print(f"{label}: " + ("faltan " + ", ".join(missing) if missing else "variables presentes"))
        ready = ready and not missing
    if settings.smtp_ssl and settings.smtp_starttls:
        print("SMTP: elige SSL implícito o STARTTLS; establece solo uno en true.")
        ready = False
    if bool(settings.smtp_username) != bool(settings.smtp_password):
        print("SMTP: configura juntos SMTP_USERNAME y SMTP_PASSWORD.")
        ready = False
    if args.check_smtp:
        if not settings.smtp_host or not settings.mail_from:
            print("SMTP: no se puede comprobar la conexión sin host y remitente.")
            ready = False
        else:
            cls = smtplib.SMTP_SSL if settings.smtp_ssl else smtplib.SMTP
            try:
                with cls(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
                    smtp.ehlo()
                    if settings.smtp_starttls and not settings.smtp_ssl:
                        smtp.starttls(context=ssl.create_default_context())
                        smtp.ehlo()
                    if settings.smtp_username:
                        smtp.login(settings.smtp_username, settings.smtp_password)
                print("SMTP: conexión y autenticación correctas; no se envió correo.")
            except (smtplib.SMTPException, OSError):
                print("SMTP: falló la conexión o autenticación; revisa los datos del proveedor.")
                ready = False
    print("Verifica las plantillas aprobadas y ejecuta el worker. La recepción externa se acredita por separado.")
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
