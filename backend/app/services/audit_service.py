"""Auditoría transaccional y aislamiento de sede de las consultas operativas."""
from uuid import uuid4

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session, with_loader_criteria

from app.models.clinic import Caja, Cita, EstadoCita, HorarioVeterinario, OrdenCobro, Producto
from app.models.operations import CompraProveedor, Egreso, EventoAuditoria, EventoCita, OrdenPendiente
from app.models.user import Usuario
from app.services.operation_utils import json_value

SCOPED = (Caja, Cita, HorarioVeterinario, OrdenCobro, Producto, CompraProveedor, Egreso, OrdenPendiente)
CRITICAL = {"usuarios", "permisos_rol", "autorizaciones_descuento", "productos", "ajustes_inventario", "citas", "ordenes_cobro", "ordenes_pendientes", "abonos_orden", "cajas", "compras_proveedor", "movimientos_inventario", "egresos", "plantillas_mensaje", "politicas_clinica", "sucursales", "procesos_atencion", "derivaciones_clinicas", "servicios"}
HIDDEN = {"contrasena", "secreto_hash", "token_hash", "comprobante", "documento", "notas_privadas", "intentos_fallidos", "bloqueado_hasta"}


@event.listens_for(Session, "do_orm_execute")
def scope_queries(state):
    if not state.is_select or state.execution_options.get("skip_branch_filter"):
        return
    branch = state.session.info.get("sucursal_id", 1)
    for model in SCOPED:
        state.statement = state.statement.options(with_loader_criteria(model, model.sucursal_id == branch, include_aliases=True))


@event.listens_for(Session, "after_flush")
def capture_changes(db, _context):
    for item in list(db.new) + list(db.dirty) + list(db.deleted):
        table = getattr(item, "__tablename__", "")
        if table not in CRITICAL:
            continue
        state = inspect(item)
        changes = {}
        for column in state.mapper.columns:
            if column.key in HIDDEN:
                continue
            history = state.attrs[column.key].history
            if item in db.new or item in db.deleted or history.has_changes():
                changes[column.key] = {"antes": json_value(history.deleted[0]) if history.deleted else None, "despues": json_value(getattr(item, column.key))}
        if not changes:
            continue
        action = "crear" if item in db.new else "eliminar" if item in db.deleted else "editar"
        actor = db.info.get("actor_id") or getattr(item, "estado_actualizado_por", None)
        db.add(EventoAuditoria(usuario_id=actor, sucursal_id=db.info.get("sucursal_id"), entidad=table, registro_id=str(getattr(item, "id", "")), accion=action, cambios=changes))
        if isinstance(item, Cita):
            tracked = {key: value for key, value in changes.items() if key in {"estado", "fecha_hora_programada", "veterinario_id", "asistencia_confirmada_en", "fecha_hora_propuesta"}}
            if not tracked:
                continue
            event_name = "creada" if item in db.new else "reprogramada" if "fecha_hora_programada" in tracked else json_value(item.estado)
            db.add(EventoCita(cita_id=item.id, usuario_id=actor, accion=event_name, anterior={key: value["antes"] for key, value in tracked.items()}, actual={key: value["despues"] for key, value in tracked.items()}, motivo=item.nota_coordinacion))
            if item in db.new or item.estado not in {EstadoCita.CONFIRMADA, EstadoCita.REPROGRAMADA, EstadoCita.CANCELADA}:
                continue
            from app.services.messaging_service import MessagingService
            from app.services.access_service import aware
            from app.services.policy_service import ZONE
            service = MessagingService(db)
            client = item.mascota.cliente.usuario
            key = uuid4().hex
            name = "cita_cancelada" if item.estado == EstadoCita.CANCELADA else "cita_reprogramada" if event_name == "reprogramada" or item.estado == EstadoCita.REPROGRAMADA else "cita_confirmada"
            values = {"nombre": client.nombre, "mascota": item.mascota.nombre, "fecha": aware(item.fecha_hora_programada).astimezone(ZONE).strftime("%d/%m/%Y %H:%M"), "motivo": item.nota_coordinacion or "Coordinado con la clínica", "cita": item.id}
            service.to_user(client, name, f"cita:{item.id}:{key}", values, entity_id=item.id)
            if item.veterinario_id and name in {"cita_reprogramada", "cita_cancelada"}:
                vet = db.get(Usuario, item.veterinario_id)
                service.to_user(vet, "veterinario_cancelacion" if name == "cita_cancelada" else "veterinario_reprogramacion", f"vet:{item.id}:{key}", values, entity_id=item.id)
