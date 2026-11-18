"""Vigencia de recordatorios y cobros, revalidada antes de cada envío/reintento."""
import datetime as dt

from sqlalchemy import select

from app.models.clinic import Cita, ConfiguracionClinica, EstadoCita, EstadoPago, EstadoProcesoAtencion, OrdenCobro
from app.models.operations import AbonoOrden, OrdenPendiente, Sucursal
from app.models.user import TipoUsuario, Usuario
from app.services.access_service import aware

OPERATIONAL_EVENTS = {"recordatorio_24h", "recordatorio_2h", "orden_creada", "orden_recordatorio", "pago_validado"}


def reminder_event(appointment, current):
    if appointment.estado not in {EstadoCita.CONFIRMADA, EstadoCita.REPROGRAMADA} or appointment.fecha_hora_llegada:
        return None
    if appointment.proceso_atencion and appointment.proceso_atencion.estado in {EstadoProcesoAtencion.EN_ATENCION, EstadoProcesoAtencion.CERRADA}:
        return None
    remaining = aware(appointment.fecha_hora_programada) - current
    if dt.timedelta(0) < remaining <= dt.timedelta(hours=2):
        return "recordatorio_2h"
    if dt.timedelta(hours=2) < remaining <= dt.timedelta(hours=24):
        return "recordatorio_24h"
    return None


def reminder_key(event, appointment):
    date = aware(appointment.fecha_hora_programada).astimezone(dt.timezone.utc).isoformat()
    return f"{event}:{appointment.id}:{date}"


def has_payment_or_proof(db, order):
    return db.scalar(select(AbonoOrden.id).where(
        AbonoOrden.orden_id == order.id,
        (AbonoOrden.estado == "validado") | ((AbonoOrden.estado == "enviado") & AbonoOrden.comprobante.is_not(None))
    ).limit(1)) is not None


def global_row(db, model, *conditions):
    # La cola recorre todas las sedes; no depende de la sede con que inició el worker.
    return db.scalar(select(model).where(*conditions).execution_options(skip_branch_filter=True, populate_existing=True))


def operational_message_ready(db, item, current):
    if item.canal != "whatsapp" or item.evento not in OPERATIONAL_EVENTS:
        return True

    def cancel(reason):
        item.estado, item.error, item.proximo_intento = "cancelado", reason, None
        return False

    def wait(reason):
        item.estado, item.error = "pendiente_configuracion", reason
        item.proximo_intento = current + dt.timedelta(minutes=5)
        return False

    owner = db.get(Usuario, item.usuario_id) if item.usuario_id else None
    if owner is None or not owner.activo or owner.tipo != TipoUsuario.CLIENTE:
        return cancel("El cliente destinatario ya no está activo o autorizado.")

    if item.evento.startswith("recordatorio_"):
        appointment = global_row(db, Cita, Cita.id == item.entidad_id)
        if appointment is None or appointment.mascota.cliente_id != owner.id:
            return cancel("La cita ya no corresponde al destinatario.")
        if reminder_event(appointment, current) != item.evento or item.clave != reminder_key(item.evento, appointment):
            return cancel("Recordatorio fuera de plazo: la cita cambió de horario, estado o ya inició.")
        branch = db.get(Sucursal, appointment.sucursal_id)
        settings = db.scalar(select(ConfiguracionClinica).order_by(ConfiguracionClinica.id))
        if settings and not settings.recordatorios_citas:
            return wait("Recordatorios de citas desactivados en Configuración.")
        phone = appointment.telefono_contacto or owner.telefono
    else:
        direct_sale = item.evento == "pago_validado" and item.clave.startswith("venta-pagada:")
        if direct_sale:
            sale = global_row(db, OrdenCobro, OrdenCobro.id == item.entidad_id)
            if sale is None or sale.cliente_id != owner.id or sale.estado_pago != EstadoPago.VALIDADO_CONFIRMADO:
                return cancel("La venta ya no tiene un pago validado para este cliente.")
            branch = db.get(Sucursal, sale.sucursal_id)
        else:
            # Compatibilidad con confirmaciones antiguas cuya referencia era solo la clave.
            reference = item.entidad_id
            if reference is None and item.evento == "pago_validado" and item.clave.startswith("pago:"):
                suffix = item.clave.removeprefix("pago:")
                reference = int(suffix) if suffix.isdigit() else None
            order = global_row(db, OrdenPendiente, OrdenPendiente.id == reference)
            if order is None or order.cliente_id != owner.id:
                return cancel("La orden ya no corresponde al destinatario.")
            branch = db.get(Sucursal, order.sucursal_id)
            if item.evento == "pago_validado":
                sale = global_row(db, OrdenCobro, OrdenCobro.preorden_id == order.id)
                if order.estado != "pagada" or sale is None or sale.estado_pago != EstadoPago.VALIDADO_CONFIRMADO:
                    return cancel("La orden o su venta ya no tienen un pago confirmado.")
            elif item.evento == "orden_recordatorio":
                age = current - aware(order.fecha)
                if order.estado != "pendiente" or not dt.timedelta(hours=2) <= age < dt.timedelta(hours=48) or has_payment_or_proof(db, order):
                    return cancel("La orden ya tiene pago/comprobante, está finalizada o salió del plazo de seguimiento.")
            elif order.estado not in {"pendiente", "parcial"}:
                return cancel("La orden ya está pagada, anulada o vencida; no se solicita su pago.")
        if item.evento == "pago_validado" and not item.documento:
            return wait("Falta el PDF del comprobante de venta para confirmar el pago.")
        phone = owner.telefono

    if branch is None or not branch.activa:
        return cancel("La sede de la operación está inactiva.")
    normalized = "".join(char for char in (phone or "") if char.isdigit())
    if len(normalized) == 9:
        normalized = "51" + normalized
    if not 10 <= len(normalized) <= 15 or normalized.startswith("0"):
        return wait("Configura un teléfono válido del cliente o de contacto de la reserva.")
    item.destinatario = normalized
    return True
