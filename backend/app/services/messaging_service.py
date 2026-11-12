import datetime as dt
import smtplib
import ssl
from email.message import EmailMessage
from string import Formatter

import httpx
from fastapi import HTTPException
from sqlalchemy import select

from app.config import get_settings
from app.models.operations import MensajeSalida, PlantillaMensaje
from app.models.user import Usuario
from app.services.access_service import aware, now

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
            fields = {name for _, name, _, _ in Formatter().parse(data.contenido) if name}
        except ValueError as exc:
            raise HTTPException(422, "Sintaxis de plantilla inválida") from exc
        if fields != expected or set(data.variables) != expected:
            raise HTTPException(422, f"Variables requeridas: {', '.join(EVENTS[event][1])}")
        item = self.db.scalar(select(PlantillaMensaje).where(PlantillaMensaje.evento == event))
        if item is None:
            item = PlantillaMensaje(evento=event)
            self.db.add(item)
        for key, value in data.model_dump().items():
            setattr(item, key, value)
        self.db.commit()
        return next(row for row in self.templates() if row["evento"] == event)

    def to_user(self, user, event, key, values, document=None, filename=None, entity_id=None):
        previous = self.db.scalar(select(MensajeSalida).where(MensajeSalida.clave == key))
        if previous:
            return previous
        template = next(item for item in self.templates() if item["evento"] == event)
        body = template["contenido"].format_map({key: str(value) for key, value in values.items()})
        phone = "".join(char for char in (user.telefono or "") if char.isdigit())
        if len(phone) == 9:
            phone = "51" + phone
        item = MensajeSalida(clave=key, canal="whatsapp", evento=event, destinatario=phone, usuario_id=user.id, entidad_id=entity_id, contenido=body, parametros=[str(values[value]) for value in template["variables"]], documento=document, documento_nombre=filename)
        self.db.add(item)
        return item

    def process(self, limit=50):
        rows = self.db.scalars(select(MensajeSalida).where(MensajeSalida.estado.in_(["pendiente", "error", "pendiente_configuracion"]), MensajeSalida.intentos < 5).order_by(MensajeSalida.id).limit(limit).with_for_update(skip_locked=True)).all()
        for item in rows:
            if item.proximo_intento and aware(item.proximo_intento) > now():
                continue
            self.deliver(item)
        self.db.commit()
        return len(rows)

    def deliver(self, item):
        configured = self.settings.smtp_host and self.settings.mail_from if item.canal == "correo" else self.settings.whatsapp_access_token and self.settings.whatsapp_phone_number_id
        template = next((row for row in self.templates() if row["evento"] == item.evento), None) if item.canal == "whatsapp" else None
        if not configured or (template is not None and (not template["nombre_proveedor"] or not template["activa"])):
            item.estado = "pendiente_configuracion"
            item.error = "Configura SMTP/remitente o WhatsApp/plantilla aprobada para este evento."
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
        except (httpx.HTTPError, smtplib.SMTPException, OSError, KeyError, ValueError):
            item.estado, item.error = "error", "El proveedor rechazó o no pudo procesar el envío; revisa configuración y vuelve a intentar."
            item.proximo_intento = now() + dt.timedelta(minutes=2 ** item.intentos)
