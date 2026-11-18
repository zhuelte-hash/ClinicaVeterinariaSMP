"""Preparación local de las comunicaciones; no acredita entrega externa."""
import re

from sqlalchemy import func, select

from app.config import get_settings
from app.models.clinic import ConfiguracionClinica
from app.models.operations import MensajeSalida
from app.services.messaging_service import MessagingService


PRIORITY_EVENTS = ("verificar", "recuperar", "cita_confirmada", "cita_reprogramada", "cita_cancelada", "receta", "veterinario_reprogramacion", "veterinario_cancelacion", "recordatorio_24h", "recordatorio_2h", "orden_creada", "orden_recordatorio", "pago_validado")


def communication_status(db):
    settings = get_settings()
    email_missing = [name.upper() for name in ("smtp_host", "mail_from") if not getattr(settings, name)]
    if settings.smtp_ssl and settings.smtp_starttls:
        email_missing.append("Elegir solo SMTP_SSL o SMTP_STARTTLS")
    if bool(settings.smtp_username) != bool(settings.smtp_password):
        email_missing.append("Configurar juntos SMTP_USERNAME y SMTP_PASSWORD")
    whatsapp_missing = [name.upper() for name in ("whatsapp_phone_number_id", "whatsapp_access_token") if not getattr(settings, name)]
    webhook_missing = [name.upper() for name in ("whatsapp_app_secret", "whatsapp_verify_token") if not getattr(settings, name)]
    clinic = db.scalar(select(ConfiguracionClinica).order_by(ConfiguracionClinica.id))
    phone = re.sub(r"\D", "", clinic.telefono if clinic else "")
    phone_valid = len(phone) == 9 or 10 <= len(phone) <= 15
    templates = MessagingService(db).templates()
    counts = db.execute(select(MensajeSalida.evento, MensajeSalida.estado, func.count()).where(MensajeSalida.evento.in_(PRIORITY_EVENTS)).group_by(MensajeSalida.evento, MensajeSalida.estado)).all()
    return {
        "correo": {"configurado": not email_missing, "faltantes": email_missing},
        "whatsapp": {"configurado": not whatsapp_missing, "faltantes": whatsapp_missing},
        "webhook": {"configurado": not webhook_missing, "faltantes": webhook_missing},
        "telefono_clinica_valido": phone_valid,
        "plantillas": templates,
        "resumen": [{"evento": event, "estado": state, "cantidad": count} for event, state, count in counts],
        "alcance": "Configuración local, sin conectar a proveedores. No acredita recepción externa ni que el worker esté ejecutándose. El teléfono público debe corresponder al Business receptor del webhook.",
    }
