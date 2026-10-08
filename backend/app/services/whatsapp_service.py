import datetime
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.clinic import Cita, WhatsAppMessage

logger = logging.getLogger(__name__)


class WhatsAppService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def send_once(self, appointment: Cita, event: str, message: str, template_name: str | None = None, parameters: list[str] | None = None) -> WhatsAppMessage:
        existing = self.db.scalar(select(WhatsAppMessage).where(WhatsAppMessage.cita_id == appointment.id, WhatsAppMessage.evento == event))
        if existing is not None:
            return existing
        phone = appointment.telefono_contacto or appointment.mascota.cliente.usuario.telefono
        record = WhatsAppMessage(cita_id=appointment.id, evento=event, telefono=phone or "", mensaje=message, estado="pendiente_configuracion")
        self.db.add(record)
        self.db.flush()
        if not phone:
            record.detalle_error = "La cita no tiene teléfono de contacto."
        elif not self.settings.whatsapp_phone_number_id or not self.settings.whatsapp_access_token or not template_name:
            logger.warning("WhatsApp no configurado; no se envió el evento %s de la cita %s", event, appointment.id)
            record.detalle_error = "Configura WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_ACCESS_TOKEN y una plantilla aprobada."
        else:
            try:
                response = httpx.post(
                    f"{self.settings.whatsapp_api_url}/{self.settings.whatsapp_phone_number_id}/messages",
                    headers={"Authorization": f"Bearer {self.settings.whatsapp_access_token}"},
                    json={"messaging_product": "whatsapp", "to": phone, "type": "template", "template": {"name": template_name, "language": {"code": "es_PE"}, "components": [{"type": "body", "parameters": [{"type": "text", "text": value} for value in (parameters or [])]}]}},
                    timeout=15,
                )
                response.raise_for_status()
                record.estado = "enviado"
                record.proveedor_id = response.json().get("messages", [{}])[0].get("id")
                record.fecha_envio = datetime.datetime.now(datetime.timezone.utc)
            except (httpx.HTTPError, ValueError) as exc:
                record.estado = "error"
                record.detalle_error = str(exc)[:500]
                logger.exception("No se pudo enviar WhatsApp para la cita %s", appointment.id)
        return record
