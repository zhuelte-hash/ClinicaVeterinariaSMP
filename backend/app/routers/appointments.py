import datetime
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import TipoUsuario, Usuario
from app.schemas.appointments import (
    AppointmentCreate,
    AppointmentCoordinationUpdate,
    AppointmentRead,
    AppointmentSummary,
    AvailabilitySlot,
    ClinicalRecordCreate,
    ClinicalRecordRead,
    AttentionStatusUpdate,
    DiagnosisCreate,
    DiagnosisRead,
    ExamOrderCreate,
    ExamOrderRead,
    ExamOrderUpdate,
    PrescriptionCreate,
    PrescriptionRead,
    ProcedureCreate,
    ProcedureRead,
    PreventiveApplicationCreate,
    PreventiveApplicationRead,
    VeterinarianAppointmentRead,
    PetCreate,
    PetRead,
    VeterinarianWalkInCreate,
    NotificationRead,
    ScheduleBlockCreate,
    ScheduleBlockRead,
    ScheduleRead,
    ScheduleUpdate,
    ServiceRead,
)
from app.schemas.user import (
    UsuarioCreate,
    UsuarioRead,
    UsuarioUpdate,
    VeterinarianClientCreate,
    VeterinarianClientUpdate,
)
from app.security import get_current_active_user, get_current_client_user, get_current_veterinarian_user
from app.services.appointment_service import (
    AppointmentConflictError,
    AppointmentNotCancelableError,
    AppointmentNotAcceptableError,
    AppointmentNotFoundError,
    AppointmentService,
    CoordinationError,
    InvalidScheduleError,
    PetNotFoundError,
    ServiceNotFoundError,
    ScheduleBlockNotFoundError,
)
from app.services.user_service import CorreoDuplicadoError, UserService

router = APIRouter(prefix="/portal", tags=["Portal de clientes"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentClient = Annotated[Usuario, Depends(get_current_client_user)]
CurrentVeterinarian = Annotated[Usuario, Depends(get_current_veterinarian_user)]
CurrentUser = Annotated[Usuario, Depends(get_current_active_user)]


@router.get("/mascotas", response_model=list[PetRead])
def get_pets(db: DbSession, client: CurrentClient):
    return AppointmentService(db).get_pets(client.id)


@router.post("/mascotas", response_model=PetRead, status_code=status.HTTP_201_CREATED)
def create_pet(data: PetCreate, db: DbSession, client: CurrentClient):
    return AppointmentService(db).create_pet(client, data)


@router.get("/servicios", response_model=list[ServiceRead])
def get_services(db: DbSession):
    return AppointmentService(db).get_services()


@router.get("/disponibilidad", response_model=list[AvailabilitySlot])
def get_availability(
    servicio_id: int,
    fecha: datetime.date,
    db: DbSession,
):
    try:
        return AppointmentService(db).get_availability(servicio_id, fecha)
    except ServiceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Servicio no encontrado") from exc


@router.get("/citas", response_model=list[AppointmentRead])
def get_appointments(db: DbSession, client: CurrentClient):
    return AppointmentService(db).get_appointments(client.id)


@router.get("/mascotas/{pet_id}/historial", response_model=list[ClinicalRecordRead])
def get_client_pet_history(pet_id: int, db: DbSession, client: CurrentClient):
    return [_clinical_read(item) for item in AppointmentService(db).get_pet_history(pet_id, client_id=client.id)]


@router.post("/citas", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
def create_appointment(data: AppointmentCreate, db: DbSession, client: CurrentClient):
    try:
        return AppointmentService(db).create_appointment(client, data)
    except PetNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Mascota no encontrada") from exc
    except ServiceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Servicio no encontrado") from exc
    except InvalidScheduleError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AppointmentConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail="Ese horario ya fue reservado. Selecciona otro.",
        ) from exc


@router.patch("/citas/{appointment_id}/cancelar", response_model=AppointmentRead)
def cancel_appointment(appointment_id: int, db: DbSession, client: CurrentClient):
    try:
        return AppointmentService(db).cancel_appointment(client.id, appointment_id)
    except AppointmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Cita no encontrada") from exc
    except AppointmentNotCancelableError as exc:
        raise HTTPException(status_code=409, detail="La cita ya no puede cancelarse") from exc


@router.patch("/citas/{appointment_id}/aceptar-horario", response_model=AppointmentRead)
def accept_proposed_time(appointment_id: int, db: DbSession, client: CurrentClient):
    try:
        return AppointmentService(db).accept_proposed_time(client.id, appointment_id)
    except AppointmentNotAcceptableError as exc:
        raise HTTPException(status_code=409, detail="La cita no tiene un horario propuesto aceptable") from exc
    except AppointmentConflictError as exc:
        raise HTTPException(status_code=409, detail="El horario propuesto ya no está disponible") from exc
    except InvalidScheduleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _veterinarian_read(appointment):
    client = appointment.mascota.cliente.usuario
    data = AppointmentRead.model_validate(appointment).model_dump()
    data.update(
        cliente_id=client.id,
        cliente_nombre=client.nombre,
        cliente_correo=client.correo,
    )
    return data


@router.get(
    "/veterinario/solicitudes",
    response_model=list[VeterinarianAppointmentRead],
    tags=["Portal veterinario"],
)
def get_veterinarian_appointments(
    db: DbSession,
    veterinarian: CurrentVeterinarian,
    fecha: datetime.date | None = None,
    estado: str | None = None,
    busqueda: str | None = None,
):
    parsed_state = None
    if estado:
        try:
            from app.models.clinic import EstadoCita

            parsed_state = EstadoCita(estado)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Estado no válido") from exc
    appointments = AppointmentService(db).get_veterinarian_appointments(
        veterinarian.id, fecha, parsed_state, busqueda
    )
    return [_veterinarian_read(appointment) for appointment in appointments]


@router.get(
    "/veterinario/clientes",
    response_model=list[UsuarioRead],
    tags=["Portal veterinario"],
)
def get_veterinarian_clients(
    db: DbSession,
    _veterinarian: CurrentVeterinarian,
    q: str | None = Query(default=None, max_length=100),
):
    return UserService(db).get_clients(q)


@router.post(
    "/veterinario/clientes",
    response_model=UsuarioRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Portal veterinario"],
)
def create_veterinarian_client(
    data: VeterinarianClientCreate,
    db: DbSession,
    _veterinarian: CurrentVeterinarian,
):
    try:
        payload = data.model_dump()
        payload["contrasena"] = payload["contrasena"] or secrets.token_urlsafe(16)
        return UserService(db).create(
            UsuarioCreate(tipo=TipoUsuario.CLIENTE, **payload)
        )
    except CorreoDuplicadoError as exc:
        raise HTTPException(status_code=409, detail="El correo ya esta registrado") from exc


@router.get("/veterinario/servicios", response_model=list[ServiceRead], tags=["Portal veterinario"])
def get_veterinarian_services(db: DbSession, _veterinarian: CurrentVeterinarian):
    return AppointmentService(db).get_services()


@router.post("/veterinario/clientes/{client_id}/mascotas", response_model=PetRead, status_code=status.HTTP_201_CREATED, tags=["Portal veterinario"])
def create_veterinarian_pet(client_id: int, data: PetCreate, db: DbSession, _veterinarian: CurrentVeterinarian):
    client = db.get(Usuario, client_id)
    if client is None or client.tipo != TipoUsuario.CLIENTE:
        raise HTTPException(status_code=404, detail="Propietario no encontrado")
    return AppointmentService(db).create_pet_for_client(client_id, data)


@router.get("/veterinario/clientes/{client_id}/mascotas", response_model=list[PetRead], tags=["Portal veterinario"])
def get_veterinarian_pets(client_id: int, db: DbSession, _veterinarian: CurrentVeterinarian):
    client = db.get(Usuario, client_id)
    if client is None or client.tipo != TipoUsuario.CLIENTE:
        raise HTTPException(status_code=404, detail="Propietario no encontrado")
    return AppointmentService(db).get_pets(client_id)


@router.post("/veterinario/atenciones/iniciar", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED, tags=["Portal veterinario"])
def start_veterinarian_walk_in(data: VeterinarianWalkInCreate, db: DbSession, veterinarian: CurrentVeterinarian):
    try:
        return AppointmentService(db).create_walk_in_appointment(veterinarian, data)
    except PetNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Mascota no encontrada") from exc
    except ServiceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Servicio no encontrado") from exc
    except AppointmentConflictError as exc:
        raise HTTPException(status_code=409, detail="No hay un espacio inmediato; intenta nuevamente para buscar el siguiente horario disponible.") from exc


@router.patch(
    "/veterinario/clientes/{client_id}",
    response_model=UsuarioRead,
    tags=["Portal veterinario"],
)
def update_veterinarian_client(
    client_id: int,
    data: VeterinarianClientUpdate,
    db: DbSession,
    _veterinarian: CurrentVeterinarian,
):
    service = UserService(db)
    client = service.get_by_id(client_id)
    if client is None or client.tipo != TipoUsuario.CLIENTE:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    update_data = data.model_dump(exclude_none=True)
    try:
        return service.update(client, UsuarioUpdate(**update_data))
    except CorreoDuplicadoError as exc:
        raise HTTPException(status_code=409, detail="El correo ya esta registrado") from exc


@router.get("/veterinario/resumen", response_model=AppointmentSummary, tags=["Portal veterinario"])
def get_veterinarian_summary(db: DbSession, veterinarian: CurrentVeterinarian):
    return AppointmentService(db).get_summary(veterinarian.id)


@router.post("/veterinario/solicitudes/{appointment_id}/llegada", response_model=VeterinarianAppointmentRead, tags=["Portal veterinario"])
def register_veterinarian_arrival(appointment_id: int, db: DbSession, veterinarian: CurrentVeterinarian):
    try:
        return _veterinarian_read(AppointmentService(db).register_arrival(veterinarian, appointment_id))
    except AppointmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Cita no encontrada") from exc
    except CoordinationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/veterinario/horarios", response_model=list[ScheduleRead], tags=["Portal veterinario"])
def get_veterinarian_schedules(db: DbSession, veterinarian: CurrentVeterinarian):
    return AppointmentService(db).get_schedules(veterinarian.id)


@router.post("/veterinario/horarios", response_model=ScheduleRead, status_code=status.HTTP_201_CREATED, tags=["Portal veterinario"])
def create_veterinarian_schedule(data: ScheduleUpdate, db: DbSession, veterinarian: CurrentVeterinarian):
    try:
        return AppointmentService(db).create_schedule(veterinarian.id, data)
    except InvalidScheduleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/veterinario/horarios/{schedule_id}", response_model=ScheduleRead, tags=["Portal veterinario"])
def update_veterinarian_schedule(schedule_id: int, data: ScheduleUpdate, db: DbSession, veterinarian: CurrentVeterinarian):
    try:
        return AppointmentService(db).update_schedule(veterinarian.id, schedule_id, data)
    except ScheduleBlockNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Horario no encontrado") from exc
    except InvalidScheduleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/veterinario/bloqueos", response_model=list[ScheduleBlockRead], tags=["Portal veterinario"])
def get_veterinarian_blocks(db: DbSession, veterinarian: CurrentVeterinarian):
    return AppointmentService(db).get_blocks(veterinarian.id)


@router.post("/veterinario/bloqueos", response_model=ScheduleBlockRead, status_code=status.HTTP_201_CREATED, tags=["Portal veterinario"])
def create_veterinarian_block(data: ScheduleBlockCreate, db: DbSession, veterinarian: CurrentVeterinarian):
    try:
        return AppointmentService(db).create_block(veterinarian.id, data)
    except InvalidScheduleError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/veterinario/bloqueos/{block_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Portal veterinario"])
def delete_veterinarian_block(block_id: int, db: DbSession, veterinarian: CurrentVeterinarian):
    try:
        AppointmentService(db).delete_block(veterinarian.id, block_id)
    except ScheduleBlockNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Bloqueo no encontrado") from exc
    return None


@router.get("/veterinario/mascotas/{pet_id}/historial", response_model=list[ClinicalRecordRead], tags=["Portal veterinario"])
def get_veterinarian_pet_history(pet_id: int, db: DbSession, veterinarian: CurrentVeterinarian):
    return [_clinical_read(item) for item in AppointmentService(db).get_pet_history(pet_id, veterinarian_id=veterinarian.id)]


@router.post("/veterinario/mascotas/{pet_id}/historial", response_model=ClinicalRecordRead, status_code=status.HTTP_201_CREATED, tags=["Portal veterinario"])
def create_initial_pet_history(
    pet_id: int,
    data: ClinicalRecordCreate,
    db: DbSession,
    veterinarian: CurrentVeterinarian,
):
    try:
        return _clinical_read(AppointmentService(db).create_initial_clinical_record(veterinarian, pet_id, data))
    except AppointmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Mascota no encontrada o no asignada al veterinario") from exc


@router.patch(
    "/veterinario/solicitudes/{appointment_id}",
    response_model=VeterinarianAppointmentRead,
    tags=["Portal veterinario"],
)
def coordinate_appointment(
    appointment_id: int,
    data: AppointmentCoordinationUpdate,
    db: DbSession,
    veterinarian: CurrentVeterinarian,
):
    try:
        appointment = AppointmentService(db).coordinate_appointment(
            veterinarian, appointment_id, data
        )
        return _veterinarian_read(appointment)
    except AppointmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada") from exc
    except CoordinationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except InvalidScheduleError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AppointmentConflictError as exc:
        raise HTTPException(status_code=409, detail="El horario se cruza con otra cita confirmada") from exc


@router.patch(
    "/veterinario/solicitudes/{appointment_id}/atencion",
    response_model=ClinicalRecordRead,
    tags=["Portal veterinario"],
)
def register_clinical_record(
    appointment_id: int,
    data: ClinicalRecordCreate,
    db: DbSession,
    veterinarian: CurrentVeterinarian,
):
    try:
        return _clinical_read(AppointmentService(db).create_clinical_record(veterinarian, appointment_id, data))
    except AppointmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Cita no encontrada o no asignada") from exc
    except CoordinationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/veterinario/solicitudes/{appointment_id}/atencion/iniciar",
    response_model=ClinicalRecordRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Portal veterinario"],
)
def start_clinical_record(appointment_id: int, db: DbSession, veterinarian: CurrentVeterinarian):
    try:
        return _clinical_read(AppointmentService(db).start_clinical_record(veterinarian, appointment_id))
    except AppointmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Cita no encontrada o no asignada") from exc
    except CoordinationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _clinical_not_found(exc: AppointmentNotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail="Atención no encontrada o no asignada al veterinario")


@router.patch("/veterinario/atenciones/{process_id}/estado", response_model=ClinicalRecordRead, tags=["Portal veterinario"])
def update_attention_status(process_id: int, data: AttentionStatusUpdate, db: DbSession, veterinarian: CurrentVeterinarian):
    try:
        process = AppointmentService(db).update_attention_status(veterinarian, process_id, data)
        return _clinical_read(AppointmentService(db).get_clinical_record_for_process(process.id))
    except AppointmentNotFoundError as exc:
        raise _clinical_not_found(exc) from exc
    except CoordinationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/veterinario/atenciones/{process_id}/diagnosticos", response_model=DiagnosisRead, status_code=status.HTTP_201_CREATED, tags=["Portal veterinario"])
def add_diagnosis(process_id: int, data: DiagnosisCreate, db: DbSession, veterinarian: CurrentVeterinarian):
    try:
        return AppointmentService(db).add_diagnosis(veterinarian, process_id, data)
    except AppointmentNotFoundError as exc:
        raise _clinical_not_found(exc) from exc


@router.post("/veterinario/atenciones/{process_id}/ordenes-examen", response_model=ExamOrderRead, status_code=status.HTTP_201_CREATED, tags=["Portal veterinario"])
def add_exam_order(process_id: int, data: ExamOrderCreate, db: DbSession, veterinarian: CurrentVeterinarian):
    try:
        return AppointmentService(db).add_exam_order(veterinarian, process_id, data)
    except AppointmentNotFoundError as exc:
        raise _clinical_not_found(exc) from exc


@router.get("/veterinario/atenciones/{process_id}/ordenes-examen", response_model=list[ExamOrderRead], tags=["Portal veterinario"])
def get_exam_orders(process_id: int, db: DbSession, veterinarian: CurrentVeterinarian):
    try:
        return AppointmentService(db).get_exam_orders(veterinarian, process_id)
    except AppointmentNotFoundError as exc:
        raise _clinical_not_found(exc) from exc


@router.patch("/veterinario/ordenes-examen/{order_id}", response_model=ExamOrderRead, tags=["Portal veterinario"])
def update_exam_order(order_id: int, data: ExamOrderUpdate, db: DbSession, veterinarian: CurrentVeterinarian):
    try:
        return AppointmentService(db).update_exam_order(veterinarian, order_id, data)
    except AppointmentNotFoundError as exc:
        raise _clinical_not_found(exc) from exc
    except CoordinationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.put("/veterinario/atenciones/{process_id}/receta", response_model=PrescriptionRead, tags=["Portal veterinario"])
def save_prescription(process_id: int, data: PrescriptionCreate, db: DbSession, veterinarian: CurrentVeterinarian):
    try:
        return AppointmentService(db).save_prescription(veterinarian, process_id, data)
    except AppointmentNotFoundError as exc:
        raise _clinical_not_found(exc) from exc


@router.post("/veterinario/atenciones/{process_id}/procedimientos", response_model=ProcedureRead, status_code=status.HTTP_201_CREATED, tags=["Portal veterinario"])
def add_procedure(process_id: int, data: ProcedureCreate, db: DbSession, veterinarian: CurrentVeterinarian):
    try:
        return AppointmentService(db).add_procedure(veterinarian, process_id, data)
    except AppointmentNotFoundError as exc:
        raise _clinical_not_found(exc) from exc


@router.post("/veterinario/atenciones/{process_id}/preventivos", response_model=PreventiveApplicationRead, status_code=status.HTTP_201_CREATED, tags=["Portal veterinario"])
def add_preventive(process_id: int, data: PreventiveApplicationCreate, db: DbSession, veterinarian: CurrentVeterinarian):
    try:
        return AppointmentService(db).add_preventive(veterinarian, process_id, data)
    except AppointmentNotFoundError as exc:
        raise _clinical_not_found(exc) from exc


@router.get("/notificaciones", response_model=list[NotificationRead], tags=["Notificaciones"])
def get_notifications(db: DbSession, user: CurrentUser):
    return AppointmentService(db).get_notifications(user.id)


@router.patch("/notificaciones/{notification_id}/leer", response_model=NotificationRead, tags=["Notificaciones"])
def mark_notification_read(notification_id: int, db: DbSession, user: CurrentUser):
    notification = AppointmentService(db).mark_notification_read(user.id, notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    return notification


def _clinical_read(process):
    medical = process.proceso_medico
    ficha = medical.ficha_clinica if medical else None
    veterinarian = medical.veterinario if medical else None
    return ClinicalRecordRead(
        id=process.id,
        cita_id=process.cita_id,
        mascota_id=process.mascota_id,
        tipo=process.tipo.value,
        fecha_inicio=process.fecha_inicio,
        fecha_fin=process.fecha_fin,
        estado=process.estado.value,
        fecha_cierre=process.fecha_cierre,
        observaciones=process.observaciones,
        motivo_consulta=process.motivo_consulta,
        anamnesis=process.anamnesis,
        diagnostico=medical.diagnostico if medical else None,
        tratamiento=medical.tratamiento if medical else None,
        peso=ficha.peso if ficha else None,
        temperatura=ficha.temperatura if ficha else None,
        historial_alergias=ficha.historial_alergias if ficha else None,
        vacunas=ficha.vacunas if ficha else None,
        desparasitaciones=ficha.desparasitaciones if ficha else None,
        medicamentos=ficha.medicamentos if ficha else None,
        procedimientos=ficha.procedimientos if ficha else None,
        examenes_resultados=ficha.examenes_resultados if ficha else None,
        proxima_fecha_control=process.proxima_fecha_control,
        veterinario_id=veterinarian.usuario_id if veterinarian else 0,
        veterinario_nombre=veterinarian.usuario.nombre if veterinarian else "",
        servicio_nombre=process.cita.servicio.nombre if process.cita else "Ficha inicial",
    )
