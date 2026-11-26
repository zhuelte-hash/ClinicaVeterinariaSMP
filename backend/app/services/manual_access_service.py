"""Alcance de la bandeja manual por rol, operación y sede seleccionada."""
from fastapi import HTTPException
from sqlalchemy import String, and_, cast, false, literal, or_, select

from app.models.clinic import AplicacionPreventiva, Cita, Mascota, OrdenCobro, ProcesoAtencion
from app.models.operations import DerivacionClinica, MensajeSalida, OrdenPendiente
from app.models.user import TipoUsuario, Usuario
from app.security import check_permission
from app.services.operation_utils import branch_id, process_in_branch

APPOINTMENT_EVENTS = {"cita_confirmada", "cita_reprogramada", "cita_cancelada", "cita_no_asistio", "recordatorio_24h", "recordatorio_2h", "veterinario_reprogramacion", "veterinario_cancelacion"}
CLINICAL_EVENTS = {"receta", "laboratorio", "encuesta"}
FINANCIAL_EVENTS = {"orden_creada", "orden_recordatorio", "pago_validado"}


def manual_permission(db, user, edit=False):
    modules = {TipoUsuario.ADMINISTRADOR: "usuarios", TipoUsuario.VETERINARIO: "historias_clinicas", TipoUsuario.CAJERO: "ventas"}
    if user.tipo not in modules:
        raise HTTPException(403, "La bandeja manual corresponde al personal autorizado")
    action = ("crear" if user.tipo == TipoUsuario.CAJERO else "editar") if edit else "ver"
    check_permission(db, user, modules[user.tipo], action)


def manual_scope(db, user, permissions=True):
    manual_permission(db, user)
    messages = MensajeSalida
    appointments = select(Cita.id).where(Cita.sucursal_id == branch_id(db))
    processes = select(ProcesoAtencion.id).where(process_in_branch(db))
    if user.tipo == TipoUsuario.VETERINARIO:
        appointments = appointments.where(Cita.veterinario_id == user.id)
        referrals = select(DerivacionClinica.proceso_id).where(DerivacionClinica.receptor_id == user.id, DerivacionClinica.estado == "aceptada")
        processes = processes.where(or_(ProcesoAtencion.proceso_medico.has(veterinario_id=user.id), ProcesoAtencion.id.in_(referrals)))
    orders = select(OrdenPendiente.id).where(OrdenPendiente.sucursal_id == branch_id(db))
    if user.tipo == TipoUsuario.VETERINARIO:
        orders = orders.where(OrdenPendiente.proceso_id.in_(processes))
    sales = select(OrdenCobro.id).where(OrdenCobro.sucursal_id == branch_id(db))
    if user.tipo == TipoUsuario.VETERINARIO:
        sales = sales.where(OrdenCobro.preorden_id.in_(orders))
    direct_payment = and_(messages.evento == "pago_validado", messages.clave.like("venta-pagada:%"))
    legacy_payment_keys = orders.with_only_columns(literal("pago:") + cast(OrdenPendiente.id, String))
    financial = and_(messages.evento.in_(FINANCIAL_EVENTS), or_(
        and_(direct_payment, messages.entidad_id.in_(sales)),
        and_(~direct_payment, messages.entidad_id.in_(orders)),
        and_(messages.evento == "pago_validado", messages.entidad_id.is_(None), messages.clave.in_(legacy_payment_keys))))
    def allowed(module):
        if not permissions:
            return True
        try:
            check_permission(db, user, module)
            return True
        except HTTPException:
            return False
    if not allowed("ventas"):
        financial = false()
    if user.tipo == TipoUsuario.CAJERO:
        return financial
    vaccines = (select(AplicacionPreventiva.id)
                .join(ProcesoAtencion, ProcesoAtencion.id == AplicacionPreventiva.proceso_id)
                .join(Mascota, Mascota.id == ProcesoAtencion.mascota_id)
                .join(Usuario, Usuario.id == Mascota.cliente_id)
                .where(Usuario.sucursal_id == branch_id(db)))
    if user.tipo == TipoUsuario.VETERINARIO:
        vaccines = vaccines.where(AplicacionPreventiva.proceso_id.in_(processes))
    other = false()
    if user.tipo == TipoUsuario.ADMINISTRADOR:
        recipients = select(Usuario.id).where(Usuario.sucursal_id == branch_id(db))
        other = and_(~messages.evento.in_(APPOINTMENT_EVENTS | CLINICAL_EVENTS | FINANCIAL_EVENTS | {"vacuna"}), messages.usuario_id.in_(recipients))
    return or_(financial,
               and_(messages.evento.in_(APPOINTMENT_EVENTS), messages.entidad_id.in_(appointments)) if allowed("citas") else false(),
               and_(messages.evento.in_(CLINICAL_EVENTS), messages.entidad_id.in_(processes)) if allowed("historias_clinicas") else false(),
               and_(messages.evento == "vacuna", messages.entidad_id.in_(vaccines)) if allowed("historias_clinicas") else false(), other)
