"""Configuración del proveedor y teléfono receptor de los enlaces de WhatsApp."""
import re
from urllib.parse import urlsplit

from sqlalchemy import select

from app.config import get_settings
from app.models.clinic import ConfiguracionClinica

DEFAULT_CLINIC_PHONE = "938304590"


def normalized_phone(value):
    digits = "".join(filter(str.isdigit, value or ""))
    return "51" + digits if len(digits) == 9 else digits


def public_url_valid(value):
    try:
        url = urlsplit(value)
        return bool(url.scheme == "https" and url.hostname and url.hostname not in {"localhost", "127.0.0.1", "::1"}
                    and not url.username and not url.password and not url.query and not url.fragment
                    and url.path in {"", "/"} and url.port in {None, 443})
    except ValueError:
        return False


def twilio_missing(settings=None):
    settings = settings or get_settings()
    fields = ("twilio_account_sid", "twilio_auth_token", "twilio_whatsapp_from", "twilio_public_url")
    missing = [field.upper() for field in fields if not getattr(settings, field)]
    if settings.twilio_account_sid and not re.fullmatch(r"AC[0-9a-fA-F]{32}", settings.twilio_account_sid):
        missing.append("TWILIO_ACCOUNT_SID: debe ser AC seguido de 32 caracteres hexadecimales")
    if settings.twilio_whatsapp_from and not re.fullmatch(r"whatsapp:\+[1-9]\d{9,14}", settings.twilio_whatsapp_from):
        missing.append("TWILIO_WHATSAPP_FROM: usa whatsapp:+ y el número internacional")
    if settings.twilio_public_url and not public_url_valid(settings.twilio_public_url):
        missing.append("TWILIO_PUBLIC_URL: usa el origen HTTPS público, sin rutas ni parámetros")
    return missing


def twilio_urls(settings=None):
    settings = settings or get_settings()
    base = settings.twilio_public_url.rstrip("/")
    return {"entrada": f"{base}/whatsapp/twilio/incoming", "estados": f"{base}/whatsapp/twilio/status"} if public_url_valid(base) else {}


def receiver_phone(db):
    settings = get_settings()
    if settings.whatsapp_provider == "twilio":
        value = settings.twilio_whatsapp_from
        return normalized_phone(value) if re.fullmatch(r"whatsapp:\+[1-9]\d{9,14}", value) else ""
    clinic = db.scalar(select(ConfiguracionClinica).order_by(ConfiguracionClinica.id))
    return normalized_phone(clinic.telefono if clinic else "")


def public_contact(db):
    clinic = db.scalar(select(ConfiguracionClinica).order_by(ConfiguracionClinica.id))
    phone = (clinic.telefono or "").strip() if clinic else ""
    phone = phone or DEFAULT_CLINIC_PHONE
    international = normalized_phone(phone)
    valid = bool(re.fullmatch(r"[1-9]\d{9,14}", international))
    display = " ".join(phone[i:i + 3] for i in range(0, 9, 3)) if re.fullmatch(r"\d{9}", phone) else phone
    return {"telefono": phone, "telefono_mostrado": display, "internacional": international if valid else "", "whatsapp": international if valid else "", "modo_whatsapp": get_settings().whatsapp_provider}
