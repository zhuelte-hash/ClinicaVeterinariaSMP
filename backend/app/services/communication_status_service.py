"""Preparación local de las comunicaciones; no acredita entrega externa."""
import re
from urllib.parse import quote

from sqlalchemy import func, select

from app.config import get_settings
from app.models.operations import MensajeSalida
from app.services.messaging_service import MessagingService
from app.services.whatsapp_config_service import receiver_phone, twilio_missing, twilio_urls


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
    if settings.whatsapp_provider == "twilio":
        whatsapp_missing = twilio_missing(settings)
        webhook_missing = list(whatsapp_missing)
    phone = receiver_phone(db)
    phone_valid = len(phone) == 9 or 10 <= len(phone) <= 15
    manual = settings.whatsapp_provider == "manual"
    if manual:
        phone_valid = bool(re.fullmatch(r"[1-9]\d{9,14}", phone))
        whatsapp_missing = [] if phone_valid else ["Teléfono de la clínica: escribe tu WhatsApp en Información de la clínica y guarda los cambios"]
        webhook_missing = []
    templates = MessagingService(db).templates()
    counts = db.execute(select(MensajeSalida.evento, MensajeSalida.estado, func.count()).where(MensajeSalida.evento.in_(PRIORITY_EVENTS)).group_by(MensajeSalida.evento, MensajeSalida.estado)).all()
    return {
        "proveedor_whatsapp": settings.whatsapp_provider,
        "manual": {"telefono_clinica": phone, "prueba_url": f"https://wa.me/{phone}?text={quote('Hola, estoy probando el WhatsApp de la clínica.')}" if phone_valid else None,
                   "instrucciones": "Usa tu WhatsApp normal. Prepara el mensaje, abre el chat y pulsa Enviar. Descarga los PDF y adjúntalos con el clip. Los comprobantes recibidos se registran y validan manualmente en caja."} if manual else None,
        "twilio": {"modo": "Sandbox / mensajes libres en ventana de 24 h", "numero": settings.twilio_whatsapp_from,
                   "urls": twilio_urls(settings), "instrucciones": "Vincula cada teléfono con join y envía hola después de configurar el webhook. El worker envía texto y PDF solo dentro de las 24 horas siguientes al último mensaje recibido. El Sandbox no admite tus plantillas personalizadas fuera de esa ventana."} if settings.whatsapp_provider == "twilio" else None,
        "correo": {"configurado": not email_missing, "faltantes": email_missing},
        "whatsapp": {"configurado": not whatsapp_missing, "faltantes": whatsapp_missing},
        "webhook": {"configurado": False, "faltantes": [], "requerido": False} if manual else {"configurado": not webhook_missing, "faltantes": webhook_missing},
        "telefono_clinica_valido": phone_valid,
        "plantillas": templates,
        "resumen": [{"evento": event, "estado": state, "cantidad": count} for event, state, count in counts],
        "alcance": ("Modo manual: abrir un enlace no envía el mensaje. gestionado_manual registra la declaración del operador, sin confirmar entrega ni lectura. Los avisos programados requieren el worker para prepararse y una persona para enviarlos."
                    if manual else "Configuración local, sin conectar a proveedores. No acredita recepción externa ni que el worker esté ejecutándose. " + ("Los enlaces de asistencia y comprobantes usan el emisor de Twilio Sandbox." if settings.whatsapp_provider == "twilio" else "El teléfono público debe corresponder al Business receptor del webhook.")),
    }
