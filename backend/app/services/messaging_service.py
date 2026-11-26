import datetime as dt
import logging
import re
import smtplib
import ssl
from email.message import EmailMessage
from string import Formatter

import httpx
from fastapi import HTTPException
from sqlalchemy import or_, select

from app.config import get_settings
from app.database import SessionLocal
from app.models.operations import DesafioCuenta, MensajeSalida, PlantillaMensaje
from app.models.user import TipoUsuario, Usuario
from app.services.access_service import aware, now
from app.services.twilio_service import TwilioSendError, TwilioService

logger = logging.getLogger(__name__)


def deliver_account_email(message_id):
    """El primer envío no necesita worker; los fallos quedan en la cola de reintentos."""
    try:
        with SessionLocal() as db:
            item = db.scalar(select(MensajeSalida).where(MensajeSalida.id == message_id, MensajeSalida.canal == "correo", MensajeSalida.estado == "pendiente").with_for_update(skip_locked=True))
            if item is not None:
                MessagingService(db).deliver(item)
                db.commit()
    except Exception:
        logger.exception("No se pudo procesar el correo de cuenta %s; permanece en la cola", message_id)

EVENTS = {
    "bienvenida": ("Bienvenido/a {nombre} a la Clínica Veterinaria San Martín de Porres.", ["nombre"]),
    "cita_confirmada": ("Hola {nombre}, la cita de {mascota} está confirmada para {fecha}.", ["nombre", "mascota", "fecha"]),
    "cita_reprogramada": ("Hola {nombre}, la cita de {mascota} fue reprogramada para {fecha}.", ["nombre", "mascota", "fecha"]),
    "cita_cancelada": ("Hola {nombre}, la cita de {mascota} fue cancelada. Motivo: {motivo}.", ["nombre", "mascota", "motivo"]),
    "recordatorio_24h": ("Hola {nombre}, recuerda la cita de {mascota} para {fecha}. Responde ASISTIRE {cita} para confirmar asistencia.", ["nombre", "mascota", "fecha", "cita"]),
    "recordatorio_2h": ("Hola {nombre}, la cita de {mascota} es a las {fecha}. Te esperamos.", ["nombre", "mascota", "fecha"]),
    "vacuna": ("Hola {nombre}, la próxima vacuna de {mascota} ({producto}) corresponde al {fecha}.", ["nombre", "mascota", "producto", "fecha"]),
    "veterinario_reprogramacion": ("La cita {cita} de {mascota} fue reprogramada/aceptada para {fecha}.", ["cita", "mascota", "fecha"]),
    "veterinario_cancelacion": ("La cita {cita} de {mascota} fue cancelada. Motivo: {motivo}.", ["cita", "mascota", "motivo"]),
    "orden_creada": ("Hola {nombre}, tu orden {codigo} es por S/ {total}. Envía el comprobante incluyendo {codigo} en el mensaje.", ["nombre", "codigo", "total"]),
    "orden_recordatorio": ("Hola {nombre}, la orden {codigo} por S/ {total} sigue pendiente de comprobante.", ["nombre", "codigo", "total"]),
    "pago_validado": ("Hola {nombre}, validamos tu pago de la orden {codigo}. Adjuntamos tu comprobante de venta.", ["nombre", "codigo"]),
    "stock_bajo": ("Stock bajo: {producto}, disponible {cantidad}, mínimo {minimo}.", ["producto", "cantidad", "minimo"]),
    "vencimiento": ("El lote {lote} de {producto}, cantidad {cantidad}, vence el {fecha}.", ["lote", "producto", "cantidad", "fecha"]),
    "laboratorio": ("Hola {nombre}, los resultados de {mascota} ya están disponibles en tu cuenta: {enlace}.", ["nombre", "mascota", "enlace"]),
    "receta": ("Hola {nombre}, adjuntamos la receta de {mascota} y su orden {codigo}.", ["nombre", "mascota", "codigo"]),
    "encuesta": ("Hola {nombre}, cuéntanos cómo fue la atención de {mascota}: {enlace}.", ["nombre", "mascota", "enlace"]),
}


class MessagingService:
    def __init__(self, db):
        self.db = db
        self.settings = get_settings()

    def templates(self):
        existing = {row.evento: row for row in self.db.scalars(select(PlantillaMensaje)).all()}
        return [{"evento": event, "nombre_proveedor": existing[event].nombre_proveedor if event in existing else "", "contenido": existing[event].contenido if event in existing else body, "variables": existing[event].variables if event in existing else variables, "idioma": existing[event].idioma if event in existing else "es_PE", "activa": existing[event].activa if event in existing else True} for event, (body, variables) in EVENTS.items()]

    def save_template(self, event, data):
        if event not in EVENTS:
            raise HTTPException(422, "Evento de mensajería no válido")
        expected = set(EVENTS[event][1])
        try:
            parsed = list(Formatter().parse(data.contenido))
            fields = {name for _, name, _, _ in parsed if name is not None}
        except ValueError as exc:
            raise HTTPException(422, "Sintaxis de plantilla inválida") from exc
        if (fields != expected or set(data.variables) != expected or len(data.variables) != len(expected)
                or any(spec or conversion for _, name, spec, conversion in parsed if name is not None)):
            raise HTTPException(422, f"Variables requeridas: {', '.join(EVENTS[event][1])}")
        item = self.db.scalar(select(PlantillaMensaje).where(PlantillaMensaje.evento == event))
        previous_variables = item.variables if item else EVENTS[event][1]
        if previous_variables != data.variables:
            pending = self.db.scalars(select(MensajeSalida).where(
                MensajeSalida.evento == event, MensajeSalida.canal == "whatsapp",
                MensajeSalida.estado.in_(["pendiente", "error", "pendiente_configuracion", "pendiente_manual"])
            ).with_for_update()).all()
            if any(len(row.parametros) != len(previous_variables) for row in pending):
                raise HTTPException(409, "Hay mensajes pendientes incompatibles; revísalos antes de cambiar el orden de variables")
            for row in pending:
                values = dict(zip(previous_variables, row.parametros))
                row.parametros = [values[name] for name in data.variables]
        if item is None:
            item = PlantillaMensaje(evento=event)
            self.db.add(item)
        for key, value in data.model_dump().items():
            setattr(item, key, value)
        self.db.commit()
        return next(row for row in self.templates() if row["evento"] == event)

    def preview(self, event, values):
        template = next((row for row in self.templates() if row["evento"] == event), None)
        if template is None:
            raise HTTPException(422, "Evento de mensajería no válido")
        if set(values) != set(EVENTS[event][1]):
            raise HTTPException(422, f"Ejemplos requeridos: {', '.join(EVENTS[event][1])}")
        return {"evento": event, "contenido": template["contenido"].format_map(values),
                "parametros": [{"posicion": i + 1, "variable": name, "valor": values[name]}
                               for i, name in enumerate(template["variables"])],
                "encabezado": "documento PDF" if event in {"receta", "pago_validado"} else "sin documento",
                "alcance": ("Texto para enviar manualmente con WhatsApp normal. Descarga y adjunta los PDF en el chat."
                            if self.settings.whatsapp_provider == "manual" else "Vista previa del texto local para Twilio Sandbox; requiere una ventana de 24 horas. Los PDF se envían sin leyenda."
                            if self.settings.whatsapp_provider == "twilio" else "Vista previa de la plantilla guardada; no envía ni acredita aprobación en Meta.")}

    def to_user(self, user, event, key, values, document=None, filename=None, entity_id=None, phone=None):
        previous = self.db.scalar(select(MensajeSalida).where(MensajeSalida.clave == key))
        if previous:
            return previous
        template = next(item for item in self.templates() if item["evento"] == event)
        body = template["contenido"].format_map({key: str(value) for key, value in values.items()})
        phone = "".join(char for char in (phone or user.telefono or "") if char.isdigit())
        if len(phone) == 9:
            phone = "51" + phone
        item = MensajeSalida(clave=key, canal="whatsapp", evento=event, destinatario=phone, usuario_id=user.id, entidad_id=entity_id, contenido=body, parametros=[str(values[value]) for value in template["variables"]], documento=document, documento_nombre=filename, estado="pendiente_manual" if self.settings.whatsapp_provider == "manual" else "pendiente")
        self.db.add(item)
        return item

    def process(self, limit=50):
        rows = self.db.scalars(select(MensajeSalida).where(MensajeSalida.estado.in_(["pendiente", "error", "pendiente_configuracion"]), MensajeSalida.intentos < 5, or_(MensajeSalida.proximo_intento.is_(None), MensajeSalida.proximo_intento <= now())).order_by(MensajeSalida.id).limit(limit).with_for_update(skip_locked=True)).all()
        for item in rows:
            if item.proximo_intento and aware(item.proximo_intento) > now():
                continue
            self.deliver(item)
        self.db.commit()
        return len(rows)

    def operation_ready(self, item, application_url=None):
        from app.services.operational_message_service import operational_message_ready
        if not operational_message_ready(self.db, item, now()):
            return False
        from app.services.customer_message_service import customer_message_ready
        if not customer_message_ready(self.db, item, now(), application_url):
            return False
        from app.services.clinical_message_service import clinical_message_ready
        if not clinical_message_ready(self.db, item, now()):
            return False
        from app.services.notice_validity_service import appointment_notice_ready, vaccine_notice_ready
        if not appointment_notice_ready(self.db, item, now()) or not vaccine_notice_ready(self.db, item, now()):
            return False
        if item.canal == "whatsapp" and item.evento in {"veterinario_reprogramacion", "veterinario_cancelacion"}:
            user = self.db.get(Usuario, item.usuario_id) if item.usuario_id else None
            if user is None or not user.activo or user.tipo != TipoUsuario.VETERINARIO:
                item.estado, item.error = "cancelado", "El veterinario destinatario ya no está activo o autorizado."
                return False
            phone = "".join(filter(str.isdigit, user.telefono or ""))
            if len(phone) == 9:
                phone = "51" + phone
            if not 10 <= len(phone) <= 15 or phone.startswith("0"):
                item.estado, item.error = "pendiente_configuracion", "Configura un teléfono válido del veterinario en Personal."
                item.proximo_intento = now() + dt.timedelta(minutes=5)
                return False
            # Relee el teléfono para permitir corregirlo antes de un reintento.
            item.destinatario = phone
        return True

    def render_manual(self, item, template):
        if template is not None:
            if len(item.parametros or []) != len(template["variables"]):
                item.estado, item.error = "pendiente_configuracion", "Revisa las variables del aviso antes de prepararlo."
                return False
            values = dict(zip(template["variables"], item.parametros))
            item.contenido = template["contenido"].format_map(values)
        if item.evento in {"recordatorio_24h", "recordatorio_2h"}:
            from app.models.clinic import Cita
            from app.services.attendance_service import attendance_code
            from app.services.operational_message_service import global_row
            appointment = global_row(self.db, Cita, Cita.id == item.entidad_id)
            command = f"ASISTIRE {appointment.id} {attendance_code(self.db, appointment)}"
            pattern = rf"\bASISTIR[EÉ]\s+{appointment.id}\b(?:\s+[0-9a-f]{{16}}\b)?"
            if re.search(pattern, item.contenido, re.I):
                item.contenido = re.sub(pattern, lambda _: command, item.contenido, flags=re.I)
            else:
                item.contenido += f"\nPara confirmar tu asistencia, responde con esta referencia completa: {command}"
        return True

    def deliver(self, item, application_url=None):
        if item.estado in {"enviado", "entregado", "leido", "cancelado", "gestionado_manual"}:
            return
        if not self.operation_ready(item, application_url):
            return
        if item.canal == "correo" and item.evento in {"verificar", "recuperar"} and item.entidad_id:
            challenge = self.db.get(DesafioCuenta, item.entidad_id)
            owner = self.db.get(Usuario, challenge.usuario_id) if challenge else None
            if (challenge is None or challenge.usado_en is not None or aware(challenge.expira_en) <= now()
                    or owner is None or not owner.activo or owner.correo.lower() != item.destinatario.lower()
                    or (item.evento == "verificar" and owner.correo_verificado)):
                item.estado, item.contenido = "cancelado", ""
                item.error = "El código/enlace o la cuenta destinataria ya no están vigentes; solicita un correo nuevo."
                return
        manual = item.canal == "whatsapp" and self.settings.whatsapp_provider == "manual"
        twilio = item.canal == "whatsapp" and self.settings.whatsapp_provider == "twilio"
        configured = self.settings.smtp_host and self.settings.mail_from if item.canal == "correo" else manual or twilio or (self.settings.whatsapp_access_token and self.settings.whatsapp_phone_number_id)
        template = next((row for row in self.templates() if row["evento"] == item.evento), None) if item.canal == "whatsapp" else None
        if not configured or (template is not None and ((not manual and not twilio and not template["nombre_proveedor"]) or not template["activa"])):
            item.estado = "pendiente_configuracion"
            item.error = "Activa el texto de este evento en Configuración → Comunicaciones." if manual or twilio else "Configura SMTP/remitente o WhatsApp/plantilla aprobada para este evento."
            item.proximo_intento = now() + dt.timedelta(minutes=5)
            return
        if item.canal == "whatsapp" and not item.destinatario and item.usuario_id:
            user = self.db.get(Usuario, item.usuario_id)
            item.destinatario = "".join(filter(str.isdigit, user.telefono or ""))
            if len(item.destinatario) == 9:
                item.destinatario = "51" + item.destinatario
        if not item.destinatario:
            item.estado = "error"
            item.error = "El destinatario no tiene teléfono de contacto"
            return
        if manual:
            from app.services.whatsapp_config_service import normalized_phone
            if not self.render_manual(item, template):
                return
            phone = normalized_phone(item.destinatario)
            if not re.fullmatch(r"[1-9]\d{9,14}", phone):
                item.estado, item.error = "pendiente_configuracion", "Corrige el teléfono del destinatario antes de abrir WhatsApp."
                return
            item.destinatario, item.estado, item.error, item.proximo_intento = phone, "pendiente_manual", None, None
            return
        if twilio and not TwilioService(self.db).ready(item):
            return
        item.intentos += 1
        try:
            if item.canal == "correo":
                message = EmailMessage()
                message["From"], message["To"], message["Subject"] = self.settings.mail_from, item.destinatario, item.asunto
                message.set_content(item.contenido)
                cls = smtplib.SMTP_SSL if self.settings.smtp_ssl else smtplib.SMTP
                with cls(self.settings.smtp_host, self.settings.smtp_port, timeout=20) as smtp:
                    if self.settings.smtp_starttls and not self.settings.smtp_ssl:
                        smtp.starttls(context=ssl.create_default_context())
                    if self.settings.smtp_username:
                        smtp.login(self.settings.smtp_username, self.settings.smtp_password)
                    smtp.send_message(message)
                item.proveedor_id = f"smtp:{item.id}"
            elif twilio:
                item.proveedor_id = TwilioService(self.db).send(item)
            else:
                base = f"{self.settings.whatsapp_api_url}/{self.settings.whatsapp_phone_number_id}"
                headers = {"Authorization": f"Bearer {self.settings.whatsapp_access_token}"}
                components = [{"type": "body", "parameters": [{"type": "text", "text": value} for value in item.parametros]}]
                if item.documento:
                    upload = httpx.post(f"{base}/media", headers=headers, data={"messaging_product": "whatsapp", "type": "application/pdf"}, files={"file": (item.documento_nombre or "documento.pdf", item.documento, "application/pdf")}, timeout=30)
                    upload.raise_for_status()
                    components.insert(0, {"type": "header", "parameters": [{"type": "document", "document": {"id": upload.json()["id"], "filename": item.documento_nombre or "documento.pdf"}}]})
                response = httpx.post(f"{base}/messages", headers=headers, json={"messaging_product": "whatsapp", "to": item.destinatario, "type": "template", "template": {"name": template["nombre_proveedor"], "language": {"code": template["idioma"]}, "components": components}}, timeout=20)
                response.raise_for_status()
                item.proveedor_id = response.json()["messages"][0]["id"]
            item.estado, item.error, item.enviado_en = "enviado", None, now()
            if twilio:
                self.db.flush()
        except TwilioSendError as exc:
            item.estado = "pendiente_configuracion" if exc.configuration else "error"
            item.error = str(exc)
            item.proximo_intento = now() + dt.timedelta(minutes=5 if exc.configuration else 2 ** item.intentos)
        except (httpx.HTTPError, smtplib.SMTPException, OSError, KeyError, ValueError):
            item.estado, item.error = "error", "El proveedor rechazó o no pudo procesar el envío; revisa configuración y vuelve a intentar."
            item.proximo_intento = now() + dt.timedelta(minutes=2 ** item.intentos)
