import datetime as dt
import secrets

from sqlalchemy import select

from app.config import get_settings
from app.models.clinic import AplicacionPreventiva, Cita, ConfiguracionClinica, EstadoCita, EstadoProcesoAtencion, Mascota, ProcesoAtencion, Producto
from app.models.operations import EncuestaConsulta, LoteInventario, MensajeSalida, OrdenPendiente, Sucursal
from app.models.user import TipoUsuario, Usuario
from app.services.access_service import aware, digest, now
from app.services.messaging_service import MessagingService
from app.services.policy_service import PolicyService, ZONE


def notify_result(db, process, key):
    user = process.mascota.cliente.usuario
    MessagingService(db).to_user(user, "laboratorio", key, {"nombre": user.nombre, "mascota": process.mascota.nombre, "enlace": f"{get_settings().frontend_url}/mis-mascotas"}, entity_id=process.id)


def run_automations(db):
    from app.services.appointment_service import AppointmentService
    from app.services.billing_service import BillingService
    service = MessagingService(db)
    count = 0
    current_branch = db.info.get("sucursal_id", 1)
    for location in db.scalars(select(Sucursal).where(Sucursal.activa)).all():
        db.info["sucursal_id"] = location.id
        policy = PolicyService(db).get()
        settings = db.scalar(select(ConfiguracionClinica).order_by(ConfiguracionClinica.id))
        AppointmentService(db).expire_unattended_appointments()
        appointments = db.scalars(select(Cita).where(Cita.estado.in_([EstadoCita.CONFIRMADA, EstadoCita.REPROGRAMADA]), Cita.fecha_hora_programada > now(), Cita.fecha_hora_programada <= now() + dt.timedelta(hours=24)).with_for_update(skip_locked=True)).all()
        if not settings or settings.recordatorios_citas:
            for appointment in appointments:
                remaining = aware(appointment.fecha_hora_programada) - now()
                event = "recordatorio_2h" if remaining <= dt.timedelta(hours=2) else "recordatorio_24h"
                owner = appointment.mascota.cliente.usuario
                service.to_user(owner, event, f"{event}:{appointment.id}:{aware(appointment.fecha_hora_programada).isoformat()}", {"nombre": owner.nombre, "mascota": appointment.mascota.nombre, "fecha": aware(appointment.fecha_hora_programada).astimezone(ZONE).strftime("%d/%m/%Y %H:%M"), "cita": appointment.id}, entity_id=appointment.id)
        preventives = db.scalars(select(AplicacionPreventiva).join(ProcesoAtencion, ProcesoAtencion.id == AplicacionPreventiva.proceso_id).join(ProcesoAtencion.cita).where(AplicacionPreventiva.proxima_fecha >= now().astimezone(ZONE).date(), AplicacionPreventiva.proxima_fecha <= now().astimezone(ZONE).date() + dt.timedelta(days=policy.dias_recordatorio_vacuna)).with_for_update(skip_locked=True)).all()
        for item in preventives:
            process = db.get(ProcesoAtencion, item.proceso_id)
            owner = process.mascota.cliente.usuario
            service.to_user(owner, "vacuna", f"vacuna:{item.id}:{item.proxima_fecha}", {"nombre": owner.nombre, "mascota": process.mascota.nombre, "producto": item.producto, "fecha": item.proxima_fecha}, entity_id=item.id)
        pending = db.scalars(select(OrdenPendiente).where(OrdenPendiente.estado == "pendiente", OrdenPendiente.fecha <= now() - dt.timedelta(hours=2)).with_for_update(skip_locked=True)).all()
        for order in pending:
            info = BillingService(db).serialize(order)
            if info["sin_comprobante"] and info["abonado"] == 0:
                owner = db.get(Usuario, order.cliente_id)
                service.to_user(owner, "orden_recordatorio", f"orden_2h:{order.id}", {"nombre": owner.nombre, "codigo": order.codigo, "total": order.total}, entity_id=order.id)
                if aware(order.fecha) < now() - dt.timedelta(hours=48):
                    order.estado = "vencida"
        admins = db.scalars(select(Usuario).where(Usuario.tipo == TipoUsuario.ADMINISTRADOR, Usuario.activo)).all()
        lots = db.execute(select(LoteInventario, Producto).join(Producto, Producto.id == LoteInventario.producto_id).where(LoteInventario.cantidad > 0, LoteInventario.vencimiento <= dt.date.today() + dt.timedelta(days=policy.dias_alerta_vencimiento)).with_for_update(skip_locked=True)).all()
        for lot, product in lots:
            for admin in admins:
                service.to_user(admin, "vencimiento", f"vence:{lot.id}:{lot.vencimiento}:{admin.id}", {"lote": lot.codigo, "producto": product.nombre, "cantidad": lot.cantidad, "fecha": lot.vencimiento}, entity_id=lot.id)
        processes = db.scalars(select(ProcesoAtencion).join(ProcesoAtencion.cita).where(ProcesoAtencion.estado == EstadoProcesoAtencion.CERRADA, ProcesoAtencion.fecha_cierre <= now() - dt.timedelta(hours=24)).with_for_update(skip_locked=True)).all()
        for process in processes:
            if db.scalar(select(EncuestaConsulta.id).where(EncuestaConsulta.proceso_id == process.id)):
                continue
            token = secrets.token_urlsafe(40)
            db.add(EncuestaConsulta(proceso_id=process.id, token_hash=digest(token), expira_en=now() + dt.timedelta(days=30)))
            owner = process.mascota.cliente.usuario
            service.to_user(owner, "encuesta", f"encuesta:{process.id}", {"nombre": owner.nombre, "mascota": process.mascota.nombre, "enlace": f"{get_settings().frontend_url}/encuesta/{token}"}, entity_id=process.id)
        db.commit()
    db.info["sucursal_id"] = current_branch
    count += service.process()
    return {"mensajes_procesados": count}
