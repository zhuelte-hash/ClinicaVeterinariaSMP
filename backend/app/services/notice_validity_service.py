"""Vigencia del horario, vacunas y destinatarios antes de entregar o preparar avisos."""
import datetime as dt

from sqlalchemy import func, select

from app.models.clinic import AplicacionPreventiva, Cita, EstadoCita, EstadoProcesoAtencion, ProcesoAtencion, TipoAplicacionPreventiva
from app.models.operations import MensajeSalida, PlantillaMensaje, Sucursal
from app.services.operational_message_service import global_row
from app.services.policy_service import PolicyService, ZONE
from app.services.access_service import aware
from app.services.whatsapp_config_service import normalized_phone

APPOINTMENT_EVENTS = {"cita_confirmada", "cita_reprogramada", "veterinario_reprogramacion", "veterinario_cancelacion"}


def cancel(item, reason):
    item.estado, item.error, item.proximo_intento = "cancelado", reason, None
    return False


def wait(item, reason, current):
    item.estado, item.error = "pendiente_configuracion", reason
    item.proximo_intento = current + dt.timedelta(hours=1)
    return False


def appointment_notice_ready(db, item, current):
    if item.canal != "whatsapp" or item.evento not in APPOINTMENT_EVENTS or not item.entidad_id:
        return True
    appointment = global_row(db, Cita, Cita.id == item.entidad_id)
    if appointment is None:
        return cancel(item, "La cita del aviso ya no está disponible.")
    professional = item.evento.startswith("veterinario_")
    if professional and appointment.veterinario_id != item.usuario_id:
        return cancel(item, "El profesional ya no es el asignado a la cita.")
    owner = appointment.mascota.cliente.usuario
    if not professional and (item.usuario_id != owner.id or not owner.activo or not owner.correo_verificado):
        return cancel(item, "El propietario ya no está activo, verificado o vinculado a la cita.")
    branch = db.get(Sucursal, appointment.sucursal_id)
    if branch is None or not branch.activa:
        return cancel(item, "La sucursal de la cita está inactiva.")
    expected = {EstadoCita.CANCELADA} if item.evento == "veterinario_cancelacion" else {EstadoCita.CONFIRMADA, EstadoCita.REPROGRAMADA}
    if appointment.estado not in expected:
        return cancel(item, "El aviso ya no corresponde al estado actual de la cita.")
    events = {"veterinario_reprogramacion", "veterinario_cancelacion"} if professional else {"cita_confirmada", "cita_reprogramada", "cita_cancelada"}
    latest = db.scalar(select(func.max(MensajeSalida.id)).where(
        MensajeSalida.canal == "whatsapp", MensajeSalida.entidad_id == appointment.id,
        MensajeSalida.usuario_id == item.usuario_id, MensajeSalida.evento.in_(events)))
    if item.id and latest and latest > item.id:
        return cancel(item, "Existe un cambio posterior de la cita; utiliza el aviso más reciente.")
    if item.evento != "veterinario_cancelacion":
        process = appointment.proceso_atencion
        if (aware(appointment.fecha_hora_programada) <= current or appointment.fecha_hora_llegada
                or (process and process.estado in {EstadoProcesoAtencion.EN_ATENCION, EstadoProcesoAtencion.CERRADA})):
            return cancel(item, "La cita ya pasó, registró llegada o inició su atención.")
        template = db.scalar(select(PlantillaMensaje).where(PlantillaMensaje.evento == item.evento))
        variables = template.variables if template else (["cita", "mascota", "fecha"] if professional else ["nombre", "mascota", "fecha"])
        values = dict(zip(variables, item.parametros))
        date = aware(appointment.fecha_hora_programada).astimezone(ZONE).strftime("%d/%m/%Y %H:%M")
        if values.get("fecha") != date:
            return cancel(item, "El horario cambió después de preparar este aviso.")
    if not professional:
        phone = normalized_phone(appointment.telefono_contacto or owner.telefono)
        if not 10 <= len(phone) <= 15 or phone.startswith("0"):
            return wait(item, "Corrige el teléfono de contacto de la cita.", current)
        item.destinatario = phone
    return True


def vaccine_notice_ready(db, item, current):
    if item.canal != "whatsapp" or item.evento != "vacuna":
        return True
    vaccine = db.get(AplicacionPreventiva, item.entidad_id) if item.entidad_id else None
    if vaccine is None or vaccine.tipo != TipoAplicacionPreventiva.VACUNA or vaccine.proxima_fecha is None:
        return cancel(item, "La aplicación ya no tiene una próxima vacuna programada.")
    process = db.get(ProcesoAtencion, vaccine.proceso_id)
    if process is None or process.estado == EstadoProcesoAtencion.CANCELADA:
        return cancel(item, "La atención de la vacuna ya no está disponible.")
    owner = process.mascota.cliente.usuario
    branch = db.get(Sucursal, owner.sucursal_id)
    if item.usuario_id != owner.id or not owner.activo or not owner.correo_verificado or branch is None or not branch.activa:
        return cancel(item, "El propietario o la sede de la vacuna ya no están disponibles.")
    if item.clave != f"vacuna:{vaccine.id}:{vaccine.proxima_fecha}":
        return cancel(item, "La próxima vacuna cambió de fecha; el worker preparará su nuevo aviso.")
    today = current.astimezone(ZONE).date()
    if vaccine.proxima_fecha < today:
        return cancel(item, "La fecha de la vacuna ya venció; coordina con el propietario.")
    if vaccine.proxima_fecha > today + dt.timedelta(days=PolicyService(db).get().dias_recordatorio_vacuna):
        return wait(item, "La vacuna todavía está fuera del plazo de recordatorio configurado.", current)
    phone = normalized_phone(owner.telefono)
    if not 10 <= len(phone) <= 15 or phone.startswith("0"):
        return wait(item, "Corrige el teléfono actual del propietario de la vacuna.", current)
    values = {"nombre": owner.nombre, "mascota": process.mascota.nombre, "producto": vaccine.producto, "fecha": str(vaccine.proxima_fecha)}
    template = db.scalar(select(PlantillaMensaje).where(PlantillaMensaje.evento == "vacuna"))
    variables = template.variables if template else ["nombre", "mascota", "producto", "fecha"]
    body = template.contenido if template else "Hola {nombre}, la próxima vacuna de {mascota} ({producto}) corresponde al {fecha}."
    try:
        item.parametros = [str(values[name]) for name in variables]
        item.contenido = body.format_map(values)
    except (KeyError, ValueError):
        return wait(item, "Revisa el texto y las variables del recordatorio de vacuna.", current)
    item.destinatario = phone
    return True
