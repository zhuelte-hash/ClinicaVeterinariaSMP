"""Vigencia de bienvenida, laboratorio y encuestas antes de usar el proveedor."""
import datetime as dt
import re

from sqlalchemy import select

from app.models.clinic import Cita, EstadoProcesoAtencion, ProcesoAtencion
from app.models.operations import EncuestaConsulta, PlantillaMensaje, Sucursal
from app.models.user import TipoUsuario, Usuario
from app.services.access_service import aware, digest
from app.config import get_settings


def customer_message_ready(db, item, current, application_url=None):
    if item.canal != "whatsapp" or item.evento not in {"bienvenida", "laboratorio", "encuesta"}:
        return True

    def cancel(reason):
        item.estado, item.error, item.proximo_intento = "cancelado", reason, None
        return False

    user = db.get(Usuario, item.usuario_id) if item.usuario_id else None
    if user is None or not user.activo or not user.correo_verificado or user.tipo != TipoUsuario.CLIENTE:
        return cancel("El cliente ya no está activo o verificado.")
    branch_id = user.sucursal_id
    if item.evento != "bienvenida":
        process = db.get(ProcesoAtencion, item.entidad_id) if item.entidad_id else None
        if process is None or process.mascota.cliente_id != user.id or process.estado == EstadoProcesoAtencion.CANCELADA:
            return cancel("La atención ya no está disponible para este destinatario.")
        if process.cita_id:
            appointment = db.scalar(select(Cita).where(Cita.id == process.cita_id).execution_options(skip_branch_filter=True))
            if appointment is None:
                return cancel("La cita de la atención ya no existe.")
            branch_id = appointment.sucursal_id
        if item.evento == "encuesta":
            survey = db.scalar(select(EncuestaConsulta).where(EncuestaConsulta.proceso_id == process.id))
            if process.estado != EstadoProcesoAtencion.CERRADA or survey is None or survey.respondida_en or aware(survey.expira_en) <= current:
                return cancel("La encuesta ya fue respondida, caducó o la atención no está cerrada.")
    branch = db.get(Sucursal, branch_id)
    if branch is None or not branch.activa:
        return cancel("La sucursal de la operación está inactiva.")
    phone = "".join(char for char in (user.telefono or "") if char.isdigit())
    if len(phone) == 9:
        phone = "51" + phone
    if not 10 <= len(phone) <= 15 or phone.startswith("0"):
        item.estado, item.error = "pendiente_configuracion", "Configura un teléfono válido del cliente."
        item.proximo_intento = current + dt.timedelta(minutes=5)
        return False
    item.destinatario = phone
    if item.evento in {"laboratorio", "encuesta"}:
        template = db.scalar(select(PlantillaMensaje).where(PlantillaMensaje.evento == item.evento))
        variables = template.variables if template else ["nombre", "mascota", "enlace"]
        values = dict(zip(variables, item.parametros))
        previous = values.get("enlace", "")
        base = (application_url or get_settings().frontend_url).rstrip("/")
        replacement = None
        if item.evento == "laboratorio" and "/mis-mascotas" in previous:
            replacement = base + "/mis-mascotas"
        elif item.evento == "encuesta" and "/encuesta/" in previous:
            token = re.search(r"/encuesta/([A-Za-z0-9_-]+)", previous)
            if token is None or digest(token[1]) != survey.token_hash:
                return cancel("El enlace de encuesta ya no corresponde a su referencia privada.")
            replacement = base + "/encuesta/" + token[1]
        if replacement and replacement != previous:
            item.contenido = item.contenido.replace(previous, replacement)
            values["enlace"] = replacement
            item.parametros = [values[name] for name in variables]
    return True
