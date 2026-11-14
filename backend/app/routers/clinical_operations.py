import datetime as dt
import re
from urllib.parse import quote
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.clinic import AplicacionPreventiva, Cita, ConfiguracionClinica, EstadoCita, ExamenMedicoAdjunto, Mascota, Notificacion, ProcesoAtencion
from app.models.operations import DerivacionClinica, EventoCita, SolicitudReprogramacion
from app.models.user import Usuario, TipoUsuario
from app.schemas.operations import PrivateNotes, ReferralAnswer, ReferralCreate, RescheduleRequest, RescheduleAnswer
from app.security import get_current_client_user, get_current_veterinarian_user, require_permission, check_permission
from app.services.access_service import aware, now
from app.services.appointment_service import AppointmentService, ACTIVE_BOOKING_STATES, InvalidScheduleError
from app.services.document_service import make_pdf
from app.services.operation_utils import row_data
from app.services.policy_service import PolicyService

router = APIRouter(tags=["Continuidad clínica y coordinación"])
Db = Annotated[Session, Depends(get_db)]
Vet = Annotated[Usuario, Depends(get_current_veterinarian_user)]
Client = Annotated[Usuario, Depends(get_current_client_user)]
Admin = Annotated[Usuario, Depends(require_permission("citas"))]
RESCHEDULABLE_STATES = ACTIVE_BOOKING_STATES - {EstadoCita.ATENDIDA}


def attachment_url(attachment, owner):
    settings = get_settings()
    token = jwt.encode({"file": attachment.id, "user": owner.id, "version": owner.version_sesion, "exp": now() + dt.timedelta(minutes=10), "aud": "clinical-file"}, settings.secret_key, algorithm=settings.algorithm)
    return f"/portal/archivos/{attachment.id}?token={token}"


@router.get("/portal/archivos/{file_id}")
def clinical_file(file_id: int, token: str, db: Db):
    settings = get_settings()
    try:
        data = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm], audience="clinical-file")
        user = db.get(Usuario, int(data["user"]))
        if int(data["file"]) != file_id or user is None or not user.activo or user.version_sesion != data["version"]:
            raise ValueError("Token inválido")
    except (JWTError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(403, "El enlace caducó o no autoriza este archivo") from exc
    attachment = db.get(ExamenMedicoAdjunto, file_id)
    if attachment is None or attachment.ficha_clinica.proceso_medico.proceso.mascota.cliente_id != user.id:
        raise HTTPException(404, "Archivo no encontrado")
    name = Path(attachment.archivo_ruta).name
    backend = Path(__file__).resolve().parents[2]
    filename = backend / "clinical_private" / name
    if not filename.is_file():
        filename = backend / "uploads" / "clinical" / name
    if not filename.is_file():
        raise HTTPException(404, "Archivo no disponible")
    return FileResponse(filename, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.get("/portal/mascotas/{pet_id}/carnet")
def vaccination_card(pet_id: int, db: Db, client: Client):
    pet = db.get(Mascota, pet_id)
    if pet is None or pet.cliente_id != client.id:
        raise HTTPException(404, "Mascota no encontrada")
    rows = db.scalars(select(AplicacionPreventiva).join(ProcesoAtencion, ProcesoAtencion.id == AplicacionPreventiva.proceso_id).where(ProcesoAtencion.mascota_id == pet.id).order_by(AplicacionPreventiva.fecha_aplicacion)).all()
    pdf = make_pdf("Carnet digital de vacunación y desparasitación", [f"Paciente: {pet.nombre} · {pet.especie} · {pet.raza or 'Sin raza registrada'}", f"Nacimiento: {pet.fecha_nacimiento or 'Sin registrar'}", f"Propietario: {client.nombre}"], [["Fecha", "Aplicación", "Producto", "Lote", "Próxima fecha"]] + [[row.fecha_aplicacion, row.tipo.value, row.producto, row.lote, row.proxima_fecha] for row in rows])
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="carnet-{pet.id}.pdf"'})


@router.get("/portal/veterinario/atenciones/{process_id}/notas-privadas")
def private_notes(process_id: int, db: Db, user: Vet):
    process = AppointmentService(db)._owned_process(user.id, process_id)
    if process is None:
        raise HTTPException(404, "Atención no asignada al profesional")
    return {"notas": process.notas_privadas or ""}


@router.put("/portal/veterinario/atenciones/{process_id}/notas-privadas")
def write_private_notes(process_id: int, data: PrivateNotes, db: Db, user: Vet):
    process = AppointmentService(db)._owned_process(user.id, process_id)
    if process is None:
        raise HTTPException(404, "Atención no asignada al profesional")
    process.notas_privadas = data.notas
    db.commit()
    return {"notas": process.notas_privadas}


@router.get("/portal/veterinario/especialistas")
def specialists(db: Db, _user: Vet):
    return [{"id": user.id, "nombre": user.nombre, "especialidad": user.especialidad} for user in db.scalars(select(Usuario).where(Usuario.tipo == TipoUsuario.VETERINARIO, Usuario.activo)).all()]


@router.get("/portal/veterinario/derivaciones")
def referrals(db: Db, user: Vet):
    rows = db.scalars(select(DerivacionClinica).where((DerivacionClinica.remitente_id == user.id) | (DerivacionClinica.receptor_id == user.id)).order_by(DerivacionClinica.id.desc())).all()
    return [{**row_data(row), "mascota_id": db.get(ProcesoAtencion, row.proceso_id).mascota_id} for row in rows]


@router.post("/portal/veterinario/atenciones/{process_id}/derivaciones", status_code=201)
def create_referral(process_id: int, data: ReferralCreate, db: Db, user: Vet):
    process = AppointmentService(db)._owned_process(user.id, process_id)
    target = db.get(Usuario, data.receptor_id)
    if process is None or target is None or target.tipo != TipoUsuario.VETERINARIO or not target.activo or target.id == user.id:
        raise HTTPException(422, "Selecciona una atención propia y otro especialista activo")
    if db.scalar(select(DerivacionClinica.id).where(DerivacionClinica.proceso_id == process.id, DerivacionClinica.receptor_id == target.id, DerivacionClinica.estado.in_(["pendiente", "aceptada"]))):
        raise HTTPException(409, "Ya existe una derivación activa a este especialista")
    item = DerivacionClinica(proceso_id=process.id, remitente_id=user.id, receptor_id=target.id, motivo=data.motivo)
    db.add(item)
    db.add(Notificacion(usuario_id=target.id, tipo="derivacion", titulo="Nueva derivación clínica", mensaje=f"{user.nombre} derivó el caso de {process.mascota.nombre}: {data.motivo}"[:500]))
    db.commit()
    return row_data(item)


@router.post("/portal/veterinario/derivaciones/{referral_id}/responder")
def answer_referral(referral_id: int, data: ReferralAnswer, db: Db, user: Vet):
    item = db.scalar(select(DerivacionClinica).where(DerivacionClinica.id == referral_id).with_for_update())
    if item is None or item.receptor_id != user.id:
        raise HTTPException(404, "Derivación no encontrada")
    if item.estado != "pendiente":
        raise HTTPException(409, "La derivación ya fue respondida")
    item.estado, item.respuesta = "aceptada" if data.aceptar else "rechazada", data.respuesta
    item.aceptada_en = now() if data.aceptar else None
    db.commit()
    return row_data(item)


def request_reschedule(db, user, appointment_id, data):
    service = AppointmentService(db)
    appointment = service._get_owned_appointment(user.id, appointment_id, for_update=True)
    if appointment is None or appointment.estado not in RESCHEDULABLE_STATES or appointment.proceso_atencion is not None:
        raise HTTPException(409, "La cita no puede reprogramarse")
    if aware(appointment.fecha_hora_programada) - now() < dt.timedelta(hours=max(4, PolicyService(db).get().horas_reprogramacion)):
        raise HTTPException(409, "No se cumple la anticipación mínima de reprogramación")
    if aware(appointment.fecha_hora_programada) == data.fecha_propuesta:
        raise HTTPException(409, "Selecciona un horario diferente al de la cita actual")
    try:
        service._validate_schedule(data.fecha_propuesta, appointment.servicio.duracion_estimada_min)
    except InvalidScheduleError as exc:
        raise HTTPException(409, str(exc)) from exc
    if appointment.veterinario_id and (not service._has_schedule(appointment.veterinario_id, data.fecha_propuesta, appointment.servicio.duracion_estimada_min) or service._has_conflict(appointment.veterinario_id, data.fecha_propuesta, appointment.servicio, appointment.id)):
        raise HTTPException(409, "La franja propuesta no está disponible")
    if db.scalar(select(SolicitudReprogramacion.id).where(SolicitudReprogramacion.cita_id == appointment.id, SolicitudReprogramacion.estado == "pendiente")):
        raise HTTPException(409, "Ya hay una solicitud pendiente para esta cita")
    phone = ""
    if data.canal == "whatsapp":
        config = db.scalar(select(ConfiguracionClinica).order_by(ConfiguracionClinica.id))
        phone = re.sub(r"\D", "", config.telefono if config else "")
        if len(phone) == 9:
            phone = "51" + phone
        if not 10 <= len(phone) <= 15:
            raise HTTPException(409, "La clínica debe configurar su teléfono de WhatsApp en Administración → Configuración")
    item = SolicitudReprogramacion(cita_id=appointment.id, cliente_id=user.id, fecha_propuesta=data.fecha_propuesta, motivo=data.motivo, canal=data.canal)
    db.add(item)
    if appointment.veterinario_id:
        db.add(Notificacion(usuario_id=appointment.veterinario_id, cita_id=appointment.id, tipo="solicitud_reprogramacion", titulo="Solicitud de nuevo horario", mensaje=f"{appointment.mascota.nombre}: {data.fecha_propuesta}. {data.motivo}"[:500]))
    db.commit()
    result = row_data(item)
    if phone:
        from app.services.policy_service import ZONE
        text = f"Solicito reprogramar la cita #{appointment.id} de {appointment.mascota.nombre}. Solicitud #{item.id}. Nuevo horario: {data.fecha_propuesta.astimezone(ZONE):%d/%m/%Y %H:%M}. Motivo: {data.motivo}. Quedo a la espera de confirmación."
        result["whatsapp_url"] = f"https://wa.me/{phone}?text={quote(text)}"
    return result


@router.post("/portal/citas/{appointment_id}/reprogramacion", status_code=201)
def reschedule(appointment_id: int, data: RescheduleRequest, db: Db, user: Client):
    return request_reschedule(db, user, appointment_id, data)


@router.get("/admin/operaciones/reprogramaciones")
def reschedule_requests(db: Db, _user: Admin):
    return [row_data(row) for row in db.scalars(select(SolicitudReprogramacion).join(Cita, Cita.id == SolicitudReprogramacion.cita_id).order_by(SolicitudReprogramacion.id.desc())).all()]


@router.get("/portal/reprogramaciones")
def own_reschedule_requests(db: Db, user: Client):
    return [row_data(row) for row in db.scalars(select(SolicitudReprogramacion).where(SolicitudReprogramacion.cliente_id == user.id).order_by(SolicitudReprogramacion.id.desc())).all()]


@router.post("/admin/operaciones/reprogramaciones/{request_id}/resolver")
def resolve_reschedule(request_id: int, data: RescheduleAnswer, db: Db, user: Admin):
    from app.schemas.admin import AdminAppointmentUpdate
    from app.services.admin_service import AdminService, AdminConflictError, AdminNotFoundError
    check_permission(db, user, "citas", "editar")
    item = db.scalar(select(SolicitudReprogramacion).join(Cita, Cita.id == SolicitudReprogramacion.cita_id).where(SolicitudReprogramacion.id == request_id).with_for_update())
    if item is None or item.estado != "pendiente":
        raise HTTPException(409, "Solicitud no encontrada o ya resuelta")
    appointment = db.get(Cita, item.cita_id)
    if appointment.estado not in RESCHEDULABLE_STATES or appointment.proceso_atencion is not None:
        raise HTTPException(409, "La cita ya no admite reprogramación")
    item.estado = "aceptada" if data.aceptar else "rechazada"
    try:
        if data.aceptar:
            AdminService(db).update_appointment(item.cita_id, AdminAppointmentUpdate(estado="reprogramada", fecha_hora_programada=aware(item.fecha_propuesta), nota_coordinacion=data.motivo), user.id)
        else:
            db.commit()
    except (AdminConflictError, AdminNotFoundError, ValueError) as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc
    return row_data(item)


@router.get("/admin/operaciones/citas/{appointment_id}/historial")
def appointment_history(appointment_id: int, db: Db, _user: Admin):
    if AppointmentService(db)._get_appointment_with_details(appointment_id) is None:
        raise HTTPException(404, "Cita no encontrada")
    rows = db.scalars(select(EventoCita).where(EventoCita.cita_id == appointment_id).order_by(EventoCita.id)).all()
    return {"cantidad": len(rows), "reprogramaciones": sum(row.accion == "reprogramada" for row in rows), "eventos": [{**row_data(row), "autor": db.get(Usuario, row.usuario_id).nombre if row.usuario_id else "Sistema"} for row in rows]}
