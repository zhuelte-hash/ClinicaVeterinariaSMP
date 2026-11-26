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
from app.models.clinic import AplicacionPreventiva, Cita, ConfiguracionClinica, EstadoCita, ExamenMedicoAdjunto, Mascota, Notificacion, ProcesoAtencion, TipoAplicacionPreventiva
from app.models.operations import DerivacionClinica, EventoCita, MensajeSalida, OrdenPendiente, SolicitudReprogramacion, Sucursal
from app.models.user import Usuario, TipoUsuario
from app.schemas.operations import ManualAttendance, PrivateNotes, ReferralAnswer, ReferralCreate, RescheduleRequest, RescheduleAnswer
from app.security import get_current_client_user, get_current_veterinarian_user, require_permission, check_permission
from app.services.access_service import aware, now
from app.services.appointment_service import AppointmentService, ACTIVE_BOOKING_STATES, InvalidScheduleError
from app.services.document_service import make_pdf
from app.services.operation_utils import branch_id, process_in_branch, row_data
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
    check_permission(db, client, "mascotas")
    pet = db.get(Mascota, pet_id)
    if pet is None or pet.cliente_id != client.id:
        raise HTTPException(404, "Mascota no encontrada")
    rows = db.scalars(select(AplicacionPreventiva).join(ProcesoAtencion, ProcesoAtencion.id == AplicacionPreventiva.proceso_id).where(ProcesoAtencion.mascota_id == pet.id, AplicacionPreventiva.tipo == TipoAplicacionPreventiva.VACUNA).order_by(AplicacionPreventiva.fecha_aplicacion, AplicacionPreventiva.id)).all()
    lines = [f"Paciente: {pet.nombre} · {pet.especie} · {pet.raza or 'Sin raza registrada'}", f"Nacimiento: {pet.fecha_nacimiento or 'Sin registrar'}", f"Propietario: {client.nombre}", "Aplicaciones registradas por el personal veterinario; próxima fecha según indicación clínica."]
    if not rows:
        lines.append("Sin vacunas registradas para esta mascota.")
    pdf = make_pdf("Carnet digital de vacunación", lines, [["Fecha", "Vacuna", "Lote", "Próxima fecha", "Veterinario"]] + [[row.fecha_aplicacion, row.producto, row.lote, row.proxima_fecha, db.get(Usuario, row.veterinario_id).nombre] for row in rows])
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="carnet-{pet.id}.pdf"', "Cache-Control": "private, no-store"})


@router.get("/portal/veterinario/atenciones/{process_id}/notas-privadas")
def private_notes(process_id: int, db: Db, user: Vet, response: Response):
    process = AppointmentService(db)._owned_process(user.id, process_id)
    if process is None:
        raise HTTPException(404, "Atención no asignada al profesional")
    response.headers["Cache-Control"] = "private, no-store"
    return {"notas": process.notas_privadas or ""}


@router.put("/portal/veterinario/atenciones/{process_id}/notas-privadas")
def write_private_notes(process_id: int, data: PrivateNotes, db: Db, user: Vet, response: Response):
    process = AppointmentService(db)._owned_process(user.id, process_id)
    if process is None:
        raise HTTPException(404, "Atención no asignada al profesional")
    process.notas_privadas = data.notas
    db.commit()
    response.headers["Cache-Control"] = "private, no-store"
    return {"notas": process.notas_privadas}


@router.get("/portal/veterinario/especialistas")
def specialists(db: Db, _user: Vet):
    check_permission(db, _user, "historias_clinicas")
    return [{"id": user.id, "nombre": user.nombre, "especialidad": user.especialidad} for user in db.scalars(select(Usuario).where(Usuario.tipo == TipoUsuario.VETERINARIO, Usuario.activo, Usuario.sucursal_id == branch_id(db), Usuario.id != _user.id)).all()]


@router.get("/portal/veterinario/derivaciones")
def referrals(db: Db, user: Vet):
    rows = db.scalars(select(DerivacionClinica).join(ProcesoAtencion, ProcesoAtencion.id == DerivacionClinica.proceso_id).where(process_in_branch(db), (DerivacionClinica.remitente_id == user.id) | (DerivacionClinica.receptor_id == user.id)).order_by(DerivacionClinica.id.desc())).all()
    return [{**row_data(row), "mascota_id": db.get(ProcesoAtencion, row.proceso_id).mascota_id, "mascota": db.get(ProcesoAtencion, row.proceso_id).mascota.nombre, "remitente": db.get(Usuario, row.remitente_id).nombre, "receptor": db.get(Usuario, row.receptor_id).nombre} for row in rows]


@router.post("/portal/veterinario/atenciones/{process_id}/derivaciones", status_code=201)
def create_referral(process_id: int, data: ReferralCreate, db: Db, user: Vet):
    process = AppointmentService(db)._owned_process(user.id, process_id)
    target = db.get(Usuario, data.receptor_id)
    if process is None or target is None or target.tipo != TipoUsuario.VETERINARIO or not target.activo or target.id == user.id or target.sucursal_id != branch_id(db):
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
    item = db.scalar(select(DerivacionClinica).join(ProcesoAtencion, ProcesoAtencion.id == DerivacionClinica.proceso_id).where(DerivacionClinica.id == referral_id, process_in_branch(db)).with_for_update())
    if item is None or item.receptor_id != user.id:
        raise HTTPException(404, "Derivación no encontrada")
    if item.estado != "pendiente":
        raise HTTPException(409, "La derivación ya fue respondida")
    item.estado, item.respuesta = "aceptada" if data.aceptar else "rechazada", data.respuesta
    item.aceptada_en = now() if data.aceptar else None
    db.add(Notificacion(usuario_id=item.remitente_id, tipo="derivacion", titulo="Respuesta a derivación clínica", mensaje=f"{user.nombre} {'aceptó' if data.aceptar else 'rechazó'} la derivación: {data.respuesta}"[:500]))
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
        from app.services.whatsapp_config_service import receiver_phone
        phone = receiver_phone(db)
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


@router.get("/portal/citas/{appointment_id}/asistencia-whatsapp")
def attendance_whatsapp(appointment_id: int, db: Db, user: Client):
    from app.services.policy_service import ZONE
    check_permission(db, user, "citas", "editar")
    appointment = AppointmentService(db)._get_owned_appointment(user.id, appointment_id)
    if appointment is None:
        raise HTTPException(404, "Cita no encontrada")
    scheduled = aware(appointment.fecha_hora_programada)
    if (appointment.estado not in {EstadoCita.CONFIRMADA, EstadoCita.REPROGRAMADA}
            or appointment.proceso_atencion is not None or appointment.fecha_hora_llegada is not None
            or scheduled <= now() or scheduled.astimezone(ZONE).date() > now().astimezone(ZONE).date() + dt.timedelta(days=1)):
        raise HTTPException(409, "La confirmación está disponible para citas de hoy o mañana aún no iniciadas")
    from app.services.whatsapp_config_service import receiver_phone
    phone = receiver_phone(db)
    if not 10 <= len(phone) <= 15:
        raise HTTPException(409, "La clínica debe configurar su teléfono de WhatsApp")
    from app.services.attendance_service import attendance_code
    command = f"ASISTIRE {appointment.id} {attendance_code(db, appointment)}"
    from app.config import get_settings
    manual = get_settings().whatsapp_provider == "manual"
    if manual:
        command = f"Hola, confirmo que asistiré a la cita #{appointment.id} de {appointment.mascota.nombre}, programada para el {scheduled.astimezone(ZONE):%d/%m/%Y a las %H:%M}.\nReferencia: {command}"
    return {"whatsapp_url": f"https://wa.me/{phone}?text={quote(command)}", "comando": command, "fecha_hora_programada": appointment.fecha_hora_programada,
            "modo": "manual" if manual else "automatico",
            "instrucciones": "La clínica revisará el mensaje y registrará manualmente su referencia en Citas. El envío no confirma automáticamente la asistencia." if manual else "Envía el comando completo desde el contacto de la reserva para que lo registre el webhook."}


@router.post("/admin/operaciones/citas/{appointment_id}/asistencia-manual")
def register_manual_attendance(appointment_id: int, data: ManualAttendance, db: Db, user: Admin, response: Response):
    import hmac
    from app.services.attendance_service import attendance_code
    from app.services.whatsapp_config_service import normalized_phone
    from app.services.policy_service import ZONE
    if get_settings().whatsapp_provider != "manual":
        raise HTTPException(409, "La recepción manual está disponible en el modo manual de WhatsApp")
    check_permission(db, user, "citas", "editar")
    appointment = db.scalar(select(Cita).where(Cita.id == appointment_id).with_for_update())
    if appointment is None:
        raise HTTPException(404, "Cita no encontrada en la sede seleccionada")
    owner = appointment.mascota.cliente.usuario
    branch = db.get(Sucursal, appointment.sucursal_id)
    if not owner.activo or not owner.correo_verificado or branch is None or not branch.activa:
        raise HTTPException(409, "La cuenta propietaria y la sede deben estar activas")
    phone = normalized_phone(data.telefono_remitente)
    if phone != normalized_phone(appointment.telefono_contacto or owner.telefono):
        raise HTTPException(409, "El remitente debe coincidir con el teléfono actual de la reserva")
    references = re.findall(r"\bASISTIR[EÉ]\s+(\d+)\s+([0-9a-f]{16})\b", data.referencia, re.I)
    if len(references) != 1 or int(references[0][0]) != appointment.id or not hmac.compare_digest(references[0][1].lower(), attendance_code(db, appointment)):
        raise HTTPException(409, "La referencia no corresponde al horario y contacto actuales; el cliente debe preparar otro mensaje")
    scheduled = aware(appointment.fecha_hora_programada)
    if (appointment.estado not in {EstadoCita.CONFIRMADA, EstadoCita.REPROGRAMADA}
            or appointment.proceso_atencion is not None or appointment.fecha_hora_llegada is not None
            or scheduled <= now() or scheduled.astimezone(ZONE).date() > now().astimezone(ZONE).date() + dt.timedelta(days=1)):
        raise HTTPException(409, "Solo se registra la asistencia de citas de hoy o mañana aún no iniciadas")
    if appointment.asistencia_confirmada_en is None:
        appointment.asistencia_confirmada_en = now()
        if appointment.veterinario_id:
            db.add(Notificacion(usuario_id=appointment.veterinario_id, cita_id=appointment.id, tipo="asistencia_confirmada", titulo="Asistencia registrada desde WhatsApp manual", mensaje=f"El personal registró la confirmación recibida para {appointment.mascota.nombre}, cita #{appointment.id}."))
    db.commit()
    response.headers["Cache-Control"] = "private, no-store"
    return {"cita_id": appointment.id, "asistencia_confirmada_en": appointment.asistencia_confirmada_en, "canal": "whatsapp_manual", "alcance": "Confirmación registrada por el personal a partir del mensaje recibido; no es una lectura automática de WhatsApp."}


def client_communications(db, user, appointment_id):
    appointment = AppointmentService(db)._get_owned_appointment(user.id, appointment_id)
    if appointment is None:
        raise HTTPException(404, "Cita no encontrada")
    process = appointment.proceso_atencion
    rows = db.scalars(select(MensajeSalida).where(
        MensajeSalida.usuario_id == user.id, MensajeSalida.canal == "whatsapp",
        ((MensajeSalida.evento == "cita_cancelada") & (MensajeSalida.entidad_id == appointment.id)) |
        ((MensajeSalida.evento == "receta") & (MensajeSalida.entidad_id == (process.id if process else -1)))
    ).order_by(MensajeSalida.id.desc())).all()
    return appointment, process, rows


@router.get("/portal/citas/{appointment_id}/comunicaciones")
def own_communications(appointment_id: int, db: Db, user: Client, response: Response):
    from app.config import get_settings
    response.headers["Cache-Control"] = "private, no-store"
    appointment, process, rows = client_communications(db, user, appointment_id)
    # El permiso clínico también se aplica al enlace y al estado de la receta.
    try:
        check_permission(db, user, "historias_clinicas")
        clinical_allowed = True
    except HTTPException:
        clinical_allowed = False
    recipe = next((row for row in rows if row.evento == "receta" and row.documento), None) if clinical_allowed else None
    order = db.scalar(select(OrdenPendiente).where(OrdenPendiente.proceso_id == process.id, OrdenPendiente.cliente_id == user.id)) if process and clinical_allowed else None
    return {"cita_id": appointment.id, "estado_cita": appointment.estado, "asistencia_confirmada_en": appointment.asistencia_confirmada_en,
            "receta_disponible": bool(recipe and process.estado.value == "cerrada"),
            "orden": {"codigo": order.codigo, "total": order.total, "estado": order.estado} if order else None,
            "mensajes": [{"id": row.id, "evento": row.evento, "estado": row.estado, "intentos": row.intentos, "enviado_en": row.enviado_en, "entregado_en": row.entregado_en} for row in rows if clinical_allowed or row.evento != "receta"],
            "alcance": ("En modo manual, la clínica prepara y envía el aviso desde WhatsApp normal. Gestión manual no confirma entrega ni lectura. Descargar la receta no acredita recepción por WhatsApp."
                        if get_settings().whatsapp_provider == "manual" else "Enviado: aceptado por el proveedor. Entregado/leído: confirmado por webhook. Descargar la receta no acredita recepción por WhatsApp.")}


@router.get("/portal/citas/{appointment_id}/receta-pdf")
def own_prescription_pdf(appointment_id: int, db: Db, user: Client):
    check_permission(db, user, "historias_clinicas")
    _, process, rows = client_communications(db, user, appointment_id)
    recipe = next((row for row in rows if row.evento == "receta" and row.documento), None)
    if process is None or process.estado.value != "cerrada" or recipe is None:
        raise HTTPException(404, "La receta PDF estará disponible después del cierre de la atención")
    return Response(recipe.documento, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="receta-cita-{appointment_id}.pdf"', "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


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
    return {"cantidad": len(rows), "reprogramaciones": sum(row.anterior.get("fecha_hora_programada") is not None and row.anterior.get("fecha_hora_programada") != row.actual.get("fecha_hora_programada") for row in rows), "cancelaciones": sum(row.actual.get("estado") == "cancelada" and row.anterior.get("estado") != "cancelada" for row in rows), "eventos": [{**row_data(row), "autor": db.get(Usuario, row.usuario_id).nombre if row.usuario_id else "Sistema"} for row in rows], "alcance": "Eventos conservados desde la activación de la trazabilidad; no reconstruye cambios anteriores."}
