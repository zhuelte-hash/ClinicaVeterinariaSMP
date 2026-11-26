"""Preparación privada de enlaces y adjuntos para envíos humanos con WhatsApp."""
from urllib.parse import quote

from fastapi import HTTPException
from sqlalchemy import and_, or_, select

from app.config import get_settings
from app.models.operations import EventoAuditoria, MensajeSalida
from app.models.clinic import AplicacionPreventiva, OrdenCobro
from app.security import check_permission
from app.services.messaging_service import MessagingService
from app.services.manual_access_service import APPOINTMENT_EVENTS, CLINICAL_EVENTS, FINANCIAL_EVENTS, manual_permission, manual_scope
from app.services.operation_utils import branch_id

MANUAL_PENDING = {"pendiente", "pendiente_configuracion", "error", "pendiente_manual"}


class ManualMessageService:
    def __init__(self, db, user):
        self.db, self.user = db, user

    def get(self, message_id):
        if get_settings().whatsapp_provider != "manual":
            raise HTTPException(409, "Selecciona el modo manual y reinicia el backend")
        manual_permission(self.db, self.user, edit=True)
        item = self.db.scalar(select(MensajeSalida).where(MensajeSalida.id == message_id, MensajeSalida.canal == "whatsapp", manual_scope(self.db, self.user, permissions=False)).with_for_update())
        if item is None:
            raise HTTPException(404, "Mensaje de WhatsApp no encontrado")
        if item.evento in CLINICAL_EVENTS:
            check_permission(self.db, self.user, "historias_clinicas")
        elif item.evento in FINANCIAL_EVENTS:
            check_permission(self.db, self.user, "ventas")
        elif item.evento in APPOINTMENT_EVENTS:
            check_permission(self.db, self.user, "citas")
        elif item.evento == "vacuna":
            check_permission(self.db, self.user, "historias_clinicas")
        return item

    def listing(self, event=None, state=None, context=None, reference=None):
        if get_settings().whatsapp_provider != "manual":
            raise HTTPException(409, "La bandeja está disponible en modo manual")
        statement = select(MensajeSalida).where(MensajeSalida.canal == "whatsapp", manual_scope(self.db, self.user))
        if event:
            statement = statement.where(MensajeSalida.evento == event)
        if (context is None) != (reference is None):
            raise HTTPException(422, "Indica el tipo y la referencia del filtro juntos")
        if context == "cita":
            statement = statement.where(MensajeSalida.evento.in_(APPOINTMENT_EVENTS), MensajeSalida.entidad_id == reference)
        elif context == "atencion":
            vaccines = select(AplicacionPreventiva.id).where(AplicacionPreventiva.proceso_id == reference)
            statement = statement.where(or_(
                and_(MensajeSalida.evento.in_(CLINICAL_EVENTS), MensajeSalida.entidad_id == reference),
                and_(MensajeSalida.evento == "vacuna", MensajeSalida.entidad_id.in_(vaccines))))
        elif context == "orden":
            statement = statement.where(MensajeSalida.evento.in_(FINANCIAL_EVENTS), ~MensajeSalida.clave.like("venta-pagada:%"), or_(
                MensajeSalida.entidad_id == reference,
                and_(MensajeSalida.evento == "pago_validado", MensajeSalida.entidad_id.is_(None), MensajeSalida.clave == f"pago:{reference}")))
        elif context == "venta":
            order = select(OrdenCobro.preorden_id).where(OrdenCobro.id == reference)
            legacy_order = self.db.scalar(order)
            statement = statement.where(MensajeSalida.evento == "pago_validado", or_(
                and_(MensajeSalida.clave.like("venta-pagada:%"), MensajeSalida.entidad_id == reference),
                and_(~MensajeSalida.clave.like("venta-pagada:%"), MensajeSalida.entidad_id.in_(order)),
                and_(MensajeSalida.entidad_id.is_(None), MensajeSalida.clave == f"pago:{legacy_order}")))
        elif context == "cliente":
            statement = statement.where(MensajeSalida.evento == "bienvenida", MensajeSalida.usuario_id == reference)
        if state == "pendientes":
            statement = statement.where(MensajeSalida.estado.in_(MANUAL_PENDING))
        elif state:
            statement = statement.where(MensajeSalida.estado == state)
        rows = self.db.scalars(statement.order_by(MensajeSalida.id.desc()).limit(200)).all()
        can_edit = True
        try:
            manual_permission(self.db, self.user, edit=True)
        except HTTPException:
            can_edit = False
        return {"modo": "manual", "puede_gestionar": can_edit,
                "mensajes": [{"id": item.id, "evento": item.evento, "estado": item.estado, "destinatario": item.destinatario,
                              "fecha": item.fecha, "entidad_id": item.entidad_id,
                              "documento_disponible": bool(item.documento), "error": item.error} for item in rows],
                "alcance": "Bandeja de la sede y de las operaciones autorizadas. Preparar o abrir no acredita entrega; gestionado_manual es lo declarado por el operador."}

    def prepare(self, message_id, application_url=None):
        item = self.get(message_id)
        if item.estado not in MANUAL_PENDING:
            raise HTTPException(409, "El mensaje ya está gestionado, cancelado o enviado por un proveedor")
        MessagingService(self.db).deliver(item, application_url)
        self.db.commit()
        if item.estado != "pendiente_manual":
            raise HTTPException(409, item.error or "El mensaje ya no está disponible")
        return item

    def instructions(self, item):
        return {"id": item.id, "evento": item.evento, "destinatario": item.destinatario,
                "contenido": item.contenido, "whatsapp_url": f"https://wa.me/{item.destinatario}?text={quote(item.contenido)}",
                "documento_disponible": bool(item.documento),
                "instrucciones": "Abre WhatsApp y pulsa Enviar. Si hay PDF, descárgalo y adjúntalo con el clip del chat. Abrir el enlace no envía el mensaje ni acredita entrega."}

    def finish(self, message_id, application_url=None):
        item = self.get(message_id)
        if item.estado == "gestionado_manual":
            return item
        item = self.prepare(message_id, application_url)
        item.estado, item.error, item.proximo_intento = "gestionado_manual", None, None
        self.db.add(EventoAuditoria(usuario_id=self.user.id, sucursal_id=branch_id(self.db), entidad="mensajes_salida", registro_id=str(item.id), accion="gestion_manual", cambios={"estado": {"antes": "pendiente_manual", "despues": "gestionado_manual"}, "evento": item.evento}))
        self.db.commit()
        return item
