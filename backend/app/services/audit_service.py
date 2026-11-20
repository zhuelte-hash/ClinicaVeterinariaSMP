"""Auditoría transaccional y aislamiento de sede de las consultas operativas."""
from uuid import uuid4

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session, with_loader_criteria

from app.models.clinic import Caja, Cita, EstadoCita, HorarioVeterinario, OrdenCobro, Producto
from app.models.operations import CompraProveedor, Egreso, EventoAuditoria, EventoCita, OrdenPendiente
from app.models.user import Usuario
from app.services.operation_utils import json_value

SCOPED = (Caja, Cita, HorarioVeterinario, OrdenCobro, Producto, CompraProveedor, Egreso, OrdenPendiente)
CRITICAL = {"usuarios", "permisos_rol", "autorizaciones_descuento", "productos", "ajustes_inventario", "citas", "ordenes_cobro", "ordenes_pendientes", "abonos_orden", "cajas", "compras_proveedor", "movimientos_inventario", "egresos", "plantillas_mensaje", "politicas_clinica", "sucursales", "procesos_atencion", "derivaciones_clinicas", "servicios", "horarios_veterinario", "unidades_medida", "lotes_inventario", "configuracion_clinica", "solicitudes_reprogramacion"}
HIDDEN = {"contrasena", "secreto_hash", "token_hash", "comprobante", "documento", "notas_privadas", "intentos_fallidos", "bloqueado_hasta"}
CRITICAL.add("horarios_veterinarios")


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
                changes[column.key] = {
                    "antes": json_value(getattr(item, column.key)) if item in db.deleted else json_value(history.deleted[0]) if history.deleted else None,
                    "despues": None if item in db.deleted else json_value(getattr(item, column.key)),
                }
        if not changes:
            continue
        action = "crear" if item in db.new else "eliminar" if item in db.deleted else "editar"
        actor = db.info.get("actor_id") or getattr(item, "estado_actualizado_por", None)
        record_id = ":".join(str(getattr(item, column.key)) for column in state.mapper.primary_key)
        db.add(EventoAuditoria(usuario_id=actor, sucursal_id=db.info.get("sucursal_id"), entidad=table, registro_id=record_id, accion=action, cambios=changes))
        if isinstance(item, Cita):
            tracked = {key: value for key, value in changes.items() if key in {"estado", "fecha_hora_programada", "veterinario_id", "asistencia_confirmada_en", "fecha_hora_propuesta"}}
            if not tracked:
                continue
            from app.services.access_service import aware
            if item not in db.new:
                # Distintas representaciones de un mismo instante no son cambios.
                for key in ("fecha_hora_programada", "fecha_hora_propuesta"):
                    history = state.attrs[key].history
                    if key in tracked and history.deleted and history.deleted[0] is not None and getattr(item, key) is not None and aware(history.deleted[0]) == aware(getattr(item, key)):
                        tracked.pop(key)
            if not tracked:
                continue
            event_name = "creada" if item in db.new else "cancelada" if "estado" in tracked and item.estado == EstadoCita.CANCELADA else "reprogramada" if "fecha_hora_programada" in tracked else "reasignada" if "veterinario_id" in tracked and "estado" not in tracked else "asistencia_confirmada" if set(tracked) == {"asistencia_confirmada_en"} else "horario_propuesto" if set(tracked) == {"fecha_hora_propuesta"} else "estado_actualizado" if "estado" in tracked else "actualizada"
            db.add(EventoCita(cita_id=item.id, usuario_id=actor, accion=event_name, anterior={key: value["antes"] for key, value in tracked.items()}, actual={key: value["despues"] for key, value in tracked.items()}, motivo=item.nota_coordinacion))
            if item in db.new or item.estado not in {EstadoCita.CONFIRMADA, EstadoCita.REPROGRAMADA, EstadoCita.CANCELADA}:
                continue
            from app.services.messaging_service import MessagingService
            from app.services.access_service import aware
            from app.services.policy_service import ZONE
            service = MessagingService(db)
            client = item.mascota.cliente.usuario
            # La confirmación de asistencia, la reasignación y la propuesta de
            # horario se auditan, pero no son una nueva confirmación al cliente.
            state_changed = "estado" in tracked
            schedule_history = state.attrs.fecha_hora_programada.history
            schedule_changed = bool(
                "fecha_hora_programada" in tracked and schedule_history.deleted
                and aware(schedule_history.deleted[0]) != aware(item.fecha_hora_programada)
            )
            if item.estado == EstadoCita.CANCELADA and state_changed:
                name = "cita_cancelada"
            elif schedule_changed and not (state_changed and item.estado == EstadoCita.CONFIRMADA):
                name = "cita_reprogramada"
            elif state_changed and item.estado == EstadoCita.CONFIRMADA:
                name = "cita_confirmada"
            elif state_changed and item.estado == EstadoCita.REPROGRAMADA:
                name = "cita_reprogramada"
            else:
                continue
            key = uuid4().hex
            values = {"nombre": client.nombre, "mascota": item.mascota.nombre, "fecha": aware(item.fecha_hora_programada).astimezone(ZONE).strftime("%d/%m/%Y %H:%M"), "motivo": item.nota_coordinacion or "Coordinado con la clínica", "cita": item.id}
            service.to_user(client, name, f"cita:{item.id}:{key}", values, entity_id=item.id, phone=item.telefono_contacto)
            if item.veterinario_id and name in {"cita_reprogramada", "cita_cancelada"}:
                vet = db.get(Usuario, item.veterinario_id)
                service.to_user(vet, "veterinario_cancelacion" if name == "cita_cancelada" else "veterinario_reprogramacion", f"vet:{item.id}:{key}", values, entity_id=item.id)


@event.listens_for(EventoCita, "before_update")
@event.listens_for(EventoCita, "before_delete")
def preserve_appointment_history(_mapper, _connection, _target):
    raise ValueError("El historial de citas es inmutable")
