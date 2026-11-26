"""Revalidación de cancelación y receta antes de entregar o reintentar."""
import datetime as dt

from sqlalchemy import select

from app.models.clinic import Cita, EstadoCita, EstadoProcesoAtencion, ProcesoAtencion
from app.models.operations import OrdenPendiente, Sucursal
from app.models.user import TipoUsuario, Usuario
from app.services.operational_message_service import global_row


def clinical_message_ready(db, item, current):
    if item.canal != "whatsapp" or item.evento not in {"cita_cancelada", "cita_no_asistio", "receta"}:
        return True

    def cancel(reason):
        item.estado, item.error, item.proximo_intento = "cancelado", reason, None
        return False

    def wait(reason):
        item.estado, item.error = "pendiente_configuracion", reason
        item.proximo_intento = current + dt.timedelta(minutes=5)
        return False

    owner = db.get(Usuario, item.usuario_id) if item.usuario_id else None
    if owner is None or not owner.activo or not owner.correo_verificado or owner.tipo != TipoUsuario.CLIENTE:
        return cancel("El propietario destinatario ya no está activo o verificado.")
    if item.evento == "receta":
        process = db.get(ProcesoAtencion, item.entidad_id) if item.entidad_id else None
        if process is None or process.mascota.cliente_id != owner.id or process.estado != EstadoProcesoAtencion.CERRADA:
            return cancel("La receta ya no corresponde a una atención cerrada del propietario.")
        order = db.scalar(select(OrdenPendiente).where(OrdenPendiente.proceso_id == process.id).execution_options(skip_branch_filter=True))
        if order is None or order.cliente_id != owner.id or order.estado in {"anulada", "vencida"}:
            return cancel("La orden asociada a la receta ya no está vigente; coordina con la clínica.")
        appointment = global_row(db, Cita, Cita.id == process.cita_id)
        if not item.documento:
            return wait("Falta el PDF de la receta para realizar el envío.")
    else:
        appointment = global_row(db, Cita, Cita.id == item.entidad_id)
        expected = EstadoCita.NO_ASISTIO if item.evento == "cita_no_asistio" else EstadoCita.CANCELADA
        if appointment is None or appointment.estado != expected:
            return cancel("La cita ya no tiene una cancelación o inasistencia vigente.")
    if appointment is None or appointment.mascota.cliente_id != owner.id:
        return cancel("La cita ya no corresponde al propietario destinatario.")
    branch = db.get(Sucursal, appointment.sucursal_id)
    if branch is None or not branch.activa:
        return cancel("La sucursal de la atención está inactiva.")
    phone = "".join(char for char in (appointment.telefono_contacto or owner.telefono or "") if char.isdigit())
    if len(phone) == 9:
        phone = "51" + phone
    if not 10 <= len(phone) <= 15 or phone.startswith("0"):
        return wait("Configura un teléfono válido de contacto de la reserva o del propietario.")
    item.destinatario = phone
    return True
