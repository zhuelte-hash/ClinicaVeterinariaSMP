"""Transporte Sandbox: texto/PDF en ventana de 24 h y medios entrantes privados."""
import datetime as dt
import hashlib
import hmac
import re
from urllib.parse import urlencode, urljoin, urlsplit

import httpx
from fastapi import HTTPException
from sqlalchemy import func, select

from app.config import get_settings
from app.models.operations import MensajeEntrante, MensajeSalida
from app.services.access_service import aware, digest, now
from app.services.whatsapp_config_service import normalized_phone, twilio_missing, twilio_urls

API = "https://api.twilio.com/2010-04-01"
MESSAGE_SID = r"(?:SM|MM)[0-9a-fA-F]{32}"
MEDIA_SID = r"ME[0-9a-fA-F]{32}"
MAX_PROOF = 5 * 1024 * 1024


def twilio_error(code):
    instructions = {
        20003: "Revisa el Account SID y el Auth Token reales de Twilio.",
        21608: "Verifica el teléfono destinatario en la cuenta de prueba de Twilio.",
        63015: "El destinatario debe enviar join con el código de tu Sandbox; vuelve a vincularlo si caducó.",
        63016: "El destinatario debe enviar un nuevo hola al Sandbox para abrir la ventana de 24 horas.",
    }
    suffix = instructions.get(code, "Revisa el registro de Messaging en Twilio y reintenta después de corregir la causa.")
    return f"Twilio informó el código {code}. {suffix}" if code else "Twilio no pudo procesar el envío. " + suffix


class TwilioSendError(Exception):
    def __init__(self, code):
        self.code = code
        self.configuration = code in {20003, 21608, 63015, 63016}
        super().__init__(twilio_error(code))


def has_window(db, phone):
    latest = db.scalar(select(func.max(MensajeEntrante.fecha)).where(
        MensajeEntrante.telefono == normalized_phone(phone), MensajeEntrante.proveedor_id.like("twilio:%")))
    return bool(latest and now() - dt.timedelta(hours=24) < aware(latest) <= now())


def document_signature(item, expires):
    checksum = hashlib.sha256(item.documento).hexdigest()
    return digest(f"twilio-pdf:{item.id}:{expires}:{item.destinatario}:{checksum}")


def document_url(item):
    expires = int((now() + dt.timedelta(minutes=30)).timestamp())
    query = urlencode({"expires": expires, "signature": document_signature(item, expires)})
    return f"{get_settings().twilio_public_url.rstrip('/')}/whatsapp/twilio/documents/{item.id}?{query}"


def document_allowed(item, expires, signature):
    return bool(item and item.canal == "whatsapp" and item.documento
                and item.estado in {"pendiente", "pendiente_configuracion", "error", "enviado", "entregado", "leido"}
                and now().timestamp() < expires <= now().timestamp() + 1800
                and re.fullmatch(r"[a-f0-9]{64}", signature)
                and hmac.compare_digest(signature, document_signature(item, expires)))


class TwilioService:
    def __init__(self, db):
        self.db = db
        self.settings = get_settings()

    def ready(self, item):
        missing = twilio_missing(self.settings)
        reason = "Configura Twilio: " + ", ".join(missing) if missing else ""
        if not reason and not re.fullmatch(r"[1-9]\d{9,14}", item.destinatario):
            reason = "Configura un teléfono internacional válido del destinatario."
        if not reason and not item.documento and len(item.contenido) > 1600:
            reason = "Reduce el texto del evento a un máximo de 1600 caracteres para Twilio."
        if not reason and not has_window(self.db, item.destinatario):
            reason = "Twilio Sandbox: envía hola desde este teléfono al Sandbox y comprueba su llegada al webhook. La ventana dura 24 horas; si no está vinculado, envía primero join con tu código."
        if reason:
            item.estado, item.error = "pendiente_configuracion", reason
            item.proximo_intento = now() + dt.timedelta(minutes=5)
            return False
        # El Sandbox admite un mensaje cada tres segundos, también entre ciclos.
        last = self.db.scalar(select(func.max(MensajeSalida.enviado_en)).where(
            (MensajeSalida.proveedor_id.like("SM%")) | (MensajeSalida.proveedor_id.like("MM%"))))
        if last and aware(last) + dt.timedelta(seconds=3) > now():
            item.estado, item.error = "pendiente", None
            item.proximo_intento = aware(last) + dt.timedelta(seconds=3)
            return False
        return True

    def send(self, item):
        data = {"From": self.settings.twilio_whatsapp_from, "To": f"whatsapp:+{item.destinatario}",
                "StatusCallback": f"{twilio_urls(self.settings)['estados']}?message_id={item.id}", "ValidityPeriod": "600"}
        if item.documento:
            # WhatsApp/Twilio no admite leyenda en documentos: el código va en el PDF.
            data["MediaUrl"] = document_url(item)
        else:
            data["Body"] = item.contenido
        response = httpx.post(f"{API}/Accounts/{self.settings.twilio_account_sid}/Messages.json",
                              auth=(self.settings.twilio_account_sid, self.settings.twilio_auth_token), data=data, timeout=20)
        if response.is_error:
            try:
                code = int(response.json().get("code") or 0)
            except (ValueError, TypeError, AttributeError):
                code = 0
            raise TwilioSendError(code)
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Respuesta de Twilio inválida")
        if payload.get("status") in {"failed", "undelivered"}:
            raise TwilioSendError(int(payload.get("error_code") or 0))
        sid = payload["sid"]
        if not isinstance(sid, str) or not re.fullmatch(MESSAGE_SID, sid):
            raise ValueError("Twilio no devolvió una referencia de mensaje válida")
        return sid


def download_proof(url, message_sid, mime):
    settings = get_settings()
    expected = rf"/2010-04-01/Accounts/{re.escape(settings.twilio_account_sid)}/Messages/{re.escape(message_sid)}/Media/{MEDIA_SID}"
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.netloc != "api.twilio.com" or parsed.query or parsed.fragment
            or not re.fullmatch(expected, parsed.path) or mime not in {"image/jpeg", "image/png", "application/pdf"}):
        raise HTTPException(422, "Medio de Twilio inválido; adjunta JPG, PNG o PDF en el mismo mensaje que la leyenda")
    for _ in range(4):
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in {None, 443}
                or not (parsed.hostname == "api.twilio.com" or (parsed.hostname or "").endswith(".twiliocdn.com"))):
            raise HTTPException(422, "La descarga debe permanecer en los servidores HTTPS de Twilio")
        auth = (settings.twilio_account_sid, settings.twilio_auth_token) if parsed.hostname == "api.twilio.com" else None
        with httpx.stream("GET", url, auth=auth, timeout=20, follow_redirects=False) as response:
            if response.is_redirect:
                url = urljoin(url, response.headers["location"])
                continue
            response.raise_for_status()
            if int(response.headers.get("content-length", "0")) > MAX_PROOF:
                raise HTTPException(422, "El comprobante supera los 5 MB")
            content = bytearray()
            for chunk in response.iter_bytes():
                if len(content) + len(chunk) > MAX_PROOF:
                    raise HTTPException(422, "El comprobante supera los 5 MB")
                content.extend(chunk)
            return bytes(content)
    raise HTTPException(422, "Demasiadas redirecciones al descargar el comprobante")
