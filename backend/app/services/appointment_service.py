import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.clinic import (
    BloqueoHorario,
    Cita,
    EstadoCita,
    FichaClinica,
    HorarioVeterinario,
    Mascota,
    Notificacion,
    ProcesoAtencion,
    ProcesoAtencionEstetica,
    ProcesoAtencionMedica,
    Servicio,
    TipoProcesoAtencion,
)
from app.models.user import Cliente, Usuario, Veterinario
from app.schemas.appointments import (
    AppointmentCoordinationUpdate,
    AppointmentCreate,
    ClinicalRecordCreate,
    PetCreate,
    ScheduleBlockCreate,
    ScheduleUpdate,
)

CLINIC_TIMEZONE = ZoneInfo("America/Lima")
ACTIVE_CONFIRMED_STATES = {
    EstadoCita.CONFIRMADA,
    EstadoCita.REPROGRAMADA,
    EstadoCita.ATENDIDA,
}
ACTIVE_BOOKING_STATES = ACTIVE_CONFIRMED_STATES | {
    EstadoCita.PENDIENTE,
    EstadoCita.PENDIENTE_CONTACTO,
    EstadoCita.CONTACTANDO_CLIENTE,
    EstadoCita.ESPERANDO_RESPUESTA,
    EstadoCita.REQUIERE_OTRO_HORARIO,
}


class PetNotFoundError(Exception):
    pass


class ServiceNotFoundError(Exception):
    pass


class AppointmentConflictError(Exception):
    pass


class InvalidScheduleError(Exception):
    pass


class AppointmentNotFoundError(Exception):
    pass


class AppointmentNotCancelableError(Exception):
    pass


class AppointmentNotAcceptableError(Exception):
    pass


class CoordinationError(Exception):
    pass


class ScheduleBlockNotFoundError(Exception):
    pass


class AppointmentService:
    def __init__(self, db: Session):
        self.db = db

    def get_pets(self, client_id: int) -> list[Mascota]:
        return list(
            self.db.scalars(
                select(Mascota)
                .where(Mascota.cliente_id == client_id)
                .order_by(Mascota.nombre)
            ).all()
        )

    def create_pet(self, client: Usuario, data: PetCreate) -> Mascota:
        pet = Mascota(cliente_id=client.id, **data.model_dump())
        self.db.add(pet)
        self.db.commit()
        self.db.refresh(pet)
        return pet

    def get_services(self) -> list[Servicio]:
        return list(self.db.scalars(select(Servicio).order_by(Servicio.nombre)).all())

    def get_appointments(self, client_id: int) -> list[Cita]:
        statement = (
            select(Cita)
            .join(Cita.mascota)
            .where(Mascota.cliente_id == client_id)
            .options(selectinload(Cita.mascota), selectinload(Cita.servicio))
            .order_by(Cita.fecha_hora_programada.desc())
        )
        return list(self.db.scalars(statement).all())

    def get_availability(
        self, service_id: int, requested_date: datetime.date
    ) -> list[dict[str, object]]:
        service = self.db.get(Servicio, service_id)
        if service is None:
            raise ServiceNotFoundError
        weekday = requested_date.weekday()
        schedules = list(
            self.db.scalars(
                select(HorarioVeterinario)
                .where(HorarioVeterinario.dia_semana == weekday, HorarioVeterinario.activo)
                .options(selectinload(HorarioVeterinario.veterinario).selectinload(Veterinario.usuario))
            ).all()
        )
        slots: list[dict[str, object]] = []
        for schedule in schedules:
            cursor = datetime.datetime.combine(
                requested_date, schedule.hora_inicio, tzinfo=CLINIC_TIMEZONE
            )
            end = datetime.datetime.combine(
                requested_date, schedule.hora_fin, tzinfo=CLINIC_TIMEZONE
            )
            while cursor + datetime.timedelta(minutes=service.duracion_estimada_min) <= end:
                if cursor > datetime.datetime.now(datetime.timezone.utc) and not self._has_block(
                    schedule.veterinario_id,
                    cursor,
                    cursor + datetime.timedelta(minutes=service.duracion_estimada_min),
                ):
                    if not self._has_conflict(schedule.veterinario_id, cursor, service):
                        slots.append(
                            {
                                "fecha_hora": cursor,
                                "veterinario_id": schedule.veterinario_id,
                                "veterinario_nombre": schedule.veterinario.usuario.nombre,
                            }
                        )
                cursor += datetime.timedelta(minutes=30)
        return slots

    def create_appointment(self, client: Usuario, data: AppointmentCreate) -> Cita:
        pet = self.db.get(Mascota, data.mascota_id)
        if pet is None or pet.cliente_id != client.id:
            raise PetNotFoundError
        service = self.db.get(Servicio, data.servicio_id)
        if service is None:
            raise ServiceNotFoundError
        veterinarian = self.db.get(Veterinario, data.veterinario_id)
        if veterinarian is None:
            raise InvalidScheduleError("El veterinario seleccionado no existe")
        self._validate_schedule(data.fecha_hora_programada, service.duracion_estimada_min)
        self.db.execute(text("SELECT pg_advisory_xact_lock(735291)"))
        if not self._has_schedule(
            veterinarian.usuario_id, data.fecha_hora_programada, service.duracion_estimada_min
        ):
            raise InvalidScheduleError("El veterinario no tiene disponibilidad para ese horario")
        if self._has_conflict(veterinarian.usuario_id, data.fecha_hora_programada, service):
            raise AppointmentConflictError
        client_record = self.db.get(Cliente, client.id)
        appointment = Cita(
            mascota_id=data.mascota_id,
            servicio_id=data.servicio_id,
            fecha_hora_programada=data.fecha_hora_programada,
            fecha_hora_fin_programada=data.fecha_hora_programada + datetime.timedelta(minutes=service.duracion_estimada_min),
            estado=EstadoCita.PENDIENTE_CONTACTO,
            veterinario_id=veterinarian.usuario_id,
            motivo=data.motivo,
            es_urgente=data.es_urgente,
            telefono_contacto=data.telefono_contacto or (client_record.telefono if client_record else None),
            preferencia_contacto=data.preferencia_contacto,
        )
        self.db.add(appointment)
        try:
            self.db.flush()
            self.db.add(
                Notificacion(
                    usuario_id=veterinarian.usuario_id,
                    cita_id=appointment.id,
                    tipo="nueva_solicitud",
                    titulo="Nueva solicitud de cita",
                    mensaje=f"{pet.nombre} tiene una solicitud para {service.nombre}.",
                )
            )
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise AppointmentConflictError from exc
        return self._get_appointment_with_details(appointment.id)

    def cancel_appointment(self, client_id: int, appointment_id: int) -> Cita:
        appointment = self._get_owned_appointment(client_id, appointment_id, for_update=True)
        if appointment is None:
            raise AppointmentNotFoundError
        if appointment.estado in {EstadoCita.CANCELADA, EstadoCita.ATENDIDA}:
            raise AppointmentNotCancelableError
        appointment.estado = EstadoCita.CANCELADA
        self.db.add(
            Notificacion(
                usuario_id=appointment.veterinario_id,
                cita_id=appointment.id,
                tipo="cita_cancelada",
                titulo="Cita cancelada por el cliente",
                mensaje=f"La cita de {appointment.mascota.nombre} fue cancelada.",
            )
        ) if appointment.veterinario_id else None
        self.db.commit()
        return self._get_appointment_with_details(appointment.id)

    def accept_proposed_time(self, client_id: int, appointment_id: int) -> Cita:
        appointment = self._get_owned_appointment(client_id, appointment_id, for_update=True)
        if appointment is None or appointment.estado != EstadoCita.REQUIERE_OTRO_HORARIO:
            raise AppointmentNotAcceptableError
        if appointment.veterinario_id is None or appointment.fecha_hora_propuesta is None:
            raise AppointmentNotAcceptableError
        self._confirm_without_overlap(
            appointment,
            appointment.veterinario_id,
            appointment.fecha_hora_propuesta,
        )
        appointment.fecha_hora_programada = appointment.fecha_hora_propuesta
        appointment.fecha_hora_fin_programada = appointment.fecha_hora_propuesta + datetime.timedelta(
            minutes=appointment.servicio.duracion_estimada_min
        )
        appointment.fecha_hora_propuesta = None
        appointment.estado = EstadoCita.REPROGRAMADA
        self.db.add(
            Notificacion(
                usuario_id=appointment.veterinario_id,
                cita_id=appointment.id,
                tipo="cita_confirmada",
                titulo="El cliente aceptó el horario",
                mensaje=f"El cliente aceptó el nuevo horario para {appointment.mascota.nombre}.",
            )
        )
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise AppointmentConflictError from exc
        return self._get_appointment_with_details(appointment.id)

    def get_veterinarian_appointments(
        self,
        veterinarian_id: int,
        requested_date: datetime.date | None = None,
        state: EstadoCita | None = None,
        search: str | None = None,
    ) -> list[Cita]:
        statement = (
            select(Cita)
            .join(Cita.mascota)
            .join(Mascota.cliente)
            .join(Cliente.usuario)
            .where((Cita.veterinario_id == veterinarian_id) | (Cita.veterinario_id.is_(None)))
            .options(
                selectinload(Cita.mascota),
                selectinload(Cita.servicio),
                selectinload(Cita.mascota).selectinload(Mascota.cliente).selectinload(Cliente.usuario),
            )
            .order_by(Cita.fecha_hora_programada)
        )
        if state is None:
            statement = statement.where(
                Cita.estado.not_in({EstadoCita.CANCELADA, EstadoCita.ATENDIDA, EstadoCita.NO_ASISTIO})
            )
        if requested_date:
            start = datetime.datetime.combine(requested_date, datetime.time.min, tzinfo=CLINIC_TIMEZONE)
            end = start + datetime.timedelta(days=1)
            statement = statement.where(Cita.fecha_hora_programada >= start, Cita.fecha_hora_programada < end)
        if state:
            statement = statement.where(Cita.estado == state)
        if search:
            term = f"%{search.strip()}%"
            statement = statement.where(or_(Mascota.nombre.ilike(term), Servicio.nombre.ilike(term)))
        return list(self.db.scalars(statement).all())

    def coordinate_appointment(
        self,
        veterinarian: Usuario,
        appointment_id: int,
        data: AppointmentCoordinationUpdate,
    ) -> Cita:
        appointment = self._get_appointment_with_details(appointment_id, for_update=True)
        if appointment is None:
            raise AppointmentNotFoundError
        if appointment.veterinario_id not in (None, veterinarian.id):
            raise AppointmentNotFoundError
        allowed_transitions = {
            EstadoCita.PENDIENTE_CONTACTO: {
                EstadoCita.CONTACTANDO_CLIENTE,
                EstadoCita.ESPERANDO_RESPUESTA,
                EstadoCita.REQUIERE_OTRO_HORARIO,
                EstadoCita.CONFIRMADA,
                EstadoCita.CANCELADA,
                EstadoCita.CLIENTE_NO_RESPONDIO,
            },
            EstadoCita.CONTACTANDO_CLIENTE: {
                EstadoCita.ESPERANDO_RESPUESTA,
                EstadoCita.REQUIERE_OTRO_HORARIO,
                EstadoCita.CONFIRMADA,
                EstadoCita.CANCELADA,
                EstadoCita.CLIENTE_NO_RESPONDIO,
            },
            EstadoCita.ESPERANDO_RESPUESTA: {
                EstadoCita.REQUIERE_OTRO_HORARIO,
                EstadoCita.CONFIRMADA,
                EstadoCita.CANCELADA,
                EstadoCita.CLIENTE_NO_RESPONDIO,
            },
            EstadoCita.REQUIERE_OTRO_HORARIO: {
                EstadoCita.CONTACTANDO_CLIENTE,
                EstadoCita.CONFIRMADA,
                EstadoCita.CANCELADA,
            },
            EstadoCita.CONFIRMADA: {EstadoCita.CANCELADA},
        }
        if data.estado == EstadoCita.ATENDIDA:
            raise CoordinationError("Registra la atención clínica para marcarla como atendida")
        if data.estado not in allowed_transitions.get(appointment.estado, set()):
            raise CoordinationError("La transición de estado no está permitida")
        if data.estado == EstadoCita.REQUIERE_OTRO_HORARIO and data.fecha_hora_propuesta is None:
            raise CoordinationError("Debes indicar el nuevo horario propuesto")
        if data.estado == EstadoCita.CANCELADA and not data.nota_coordinacion:
            raise CoordinationError("Indica el motivo del rechazo o cancelación")
        if data.fecha_hora_propuesta is not None:
            self._validate_schedule(data.fecha_hora_propuesta, appointment.servicio.duracion_estimada_min)
            if not self._has_schedule(
                veterinarian.id,
                data.fecha_hora_propuesta,
                appointment.servicio.duracion_estimada_min,
            ):
                raise InvalidScheduleError("El horario propuesto no está dentro de la agenda del veterinario")
            if self._has_conflict(
                veterinarian.id,
                data.fecha_hora_propuesta,
                appointment.servicio,
                appointment.id,
            ):
                raise AppointmentConflictError
        if data.estado == EstadoCita.CONFIRMADA:
            scheduled_at = data.fecha_hora_propuesta or appointment.fecha_hora_propuesta or appointment.fecha_hora_programada
            self._confirm_without_overlap(appointment, veterinarian.id, scheduled_at)
            appointment.fecha_hora_programada = scheduled_at
            appointment.fecha_hora_fin_programada = scheduled_at + datetime.timedelta(
                minutes=appointment.servicio.duracion_estimada_min
            )
            appointment.fecha_hora_propuesta = None
        elif data.fecha_hora_propuesta is not None:
            appointment.fecha_hora_propuesta = data.fecha_hora_propuesta
        appointment.veterinario_id = veterinarian.id
        appointment.estado = data.estado
        appointment.nota_coordinacion = data.nota_coordinacion
        appointment.estado_actualizado_por = veterinarian.id
        try:
            self.db.add(
                Notificacion(
                    usuario_id=appointment.mascota.cliente_id,
                    cita_id=appointment.id,
                    tipo="cambio_cita",
                    titulo="Actualización de tu solicitud",
                    mensaje=f"La solicitud de {appointment.mascota.nombre} cambió a {appointment.estado.value}.",
                )
            )
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise AppointmentConflictError from exc
        return self._get_appointment_with_details(appointment.id)

    def get_summary(self, veterinarian_id: int) -> dict[str, int]:
        now = datetime.datetime.now(datetime.timezone.utc)
        active = self.get_veterinarian_appointments(veterinarian_id)
        return {
            "pendientes": sum(item.estado == EstadoCita.PENDIENTE_CONTACTO for item in active),
            "confirmadas": sum(item.estado in {EstadoCita.CONFIRMADA, EstadoCita.REPROGRAMADA} for item in active),
            "atendidas": self.db.scalar(
                select(func.count(Cita.id)).where(
                    Cita.veterinario_id == veterinarian_id, Cita.estado == EstadoCita.ATENDIDA
                )
            ) or 0,
            "proximas": sum(
                item.estado in {EstadoCita.CONFIRMADA, EstadoCita.REPROGRAMADA}
                and item.fecha_hora_programada >= now
                for item in active
            ),
        }

    def get_schedules(self, veterinarian_id: int) -> list[HorarioVeterinario]:
        return list(self.db.scalars(
            select(HorarioVeterinario)
            .where(HorarioVeterinario.veterinario_id == veterinarian_id)
            .order_by(HorarioVeterinario.dia_semana, HorarioVeterinario.hora_inicio)
        ).all())

    def create_schedule(self, veterinarian_id: int, data: ScheduleUpdate) -> HorarioVeterinario:
        self._ensure_schedule_not_overlapping(veterinarian_id, data)
        schedule = HorarioVeterinario(veterinario_id=veterinarian_id, **data.model_dump())
        self.db.add(schedule)
        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def update_schedule(self, veterinarian_id: int, schedule_id: int, data: ScheduleUpdate) -> HorarioVeterinario:
        schedule = self.db.scalar(select(HorarioVeterinario).where(
            HorarioVeterinario.id == schedule_id,
            HorarioVeterinario.veterinario_id == veterinarian_id,
        ))
        if schedule is None:
            raise ScheduleBlockNotFoundError
        self._ensure_schedule_not_overlapping(veterinarian_id, data, schedule_id)
        for key, value in data.model_dump().items():
            setattr(schedule, key, value)
        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def _ensure_schedule_not_overlapping(
        self,
        veterinarian_id: int,
        data: ScheduleUpdate,
        excluded_schedule_id: int | None = None,
    ) -> None:
        if not data.activo:
            return
        statement = select(HorarioVeterinario).where(
            HorarioVeterinario.veterinario_id == veterinarian_id,
            HorarioVeterinario.dia_semana == data.dia_semana,
            HorarioVeterinario.activo,
            HorarioVeterinario.hora_inicio < data.hora_fin,
            HorarioVeterinario.hora_fin > data.hora_inicio,
        )
        if excluded_schedule_id is not None:
            statement = statement.where(HorarioVeterinario.id != excluded_schedule_id)
        if self.db.scalar(statement) is not None:
            raise InvalidScheduleError("El horario se cruza con otro horario activo")

    def get_blocks(self, veterinarian_id: int) -> list[BloqueoHorario]:
        return list(self.db.scalars(select(BloqueoHorario).where(
            BloqueoHorario.veterinario_id == veterinarian_id
        ).order_by(BloqueoHorario.fecha_hora_inicio)).all())

    def create_block(self, veterinarian_id: int, data: ScheduleBlockCreate) -> BloqueoHorario:
        if data.fecha_hora_fin <= data.fecha_hora_inicio:
            raise InvalidScheduleError("El final del bloqueo debe ser posterior al inicio")
        block = BloqueoHorario(veterinario_id=veterinarian_id, **data.model_dump())
        self.db.add(block)
        self.db.commit()
        self.db.refresh(block)
        return block

    def delete_block(self, veterinarian_id: int, block_id: int) -> None:
        block = self.db.scalar(select(BloqueoHorario).where(
            BloqueoHorario.id == block_id,
            BloqueoHorario.veterinario_id == veterinarian_id,
        ))
        if block is None:
            raise ScheduleBlockNotFoundError
        self.db.delete(block)
        self.db.commit()

    def create_clinical_record(
        self, veterinarian: Usuario, appointment_id: int, data: ClinicalRecordCreate
    ) -> ProcesoAtencion:
        appointment = self._get_appointment_with_details(appointment_id)
        if appointment is None or appointment.veterinario_id != veterinarian.id:
            raise AppointmentNotFoundError
        if appointment.estado not in {EstadoCita.CONFIRMADA, EstadoCita.REPROGRAMADA}:
            raise CoordinationError("La atención solo puede registrarse en una cita confirmada")
        process = appointment.proceso_atencion
        if process is None:
            process_type = (
                TipoProcesoAtencion.MEDICA if appointment.servicio.medico else TipoProcesoAtencion.ESTETICA
            )
            process = ProcesoAtencion(
                cita_id=appointment.id,
                mascota_id=appointment.mascota_id,
                tipo=process_type,
                observaciones=data.observaciones,
                motivo_consulta=data.motivo_consulta,
                anamnesis=data.anamnesis,
                proxima_fecha_control=data.proxima_fecha_control,
            )
            self.db.add(process)
            self.db.flush()
        else:
            process.observaciones = data.observaciones
            process.motivo_consulta = data.motivo_consulta
            process.anamnesis = data.anamnesis
            process.proxima_fecha_control = data.proxima_fecha_control
        if appointment.servicio.medico:
            medical = process.proceso_medico
            if medical is None:
                medical = ProcesoAtencionMedica(proceso_id=process.id, veterinario_id=veterinarian.id)
                self.db.add(medical)
            medical.diagnostico = data.diagnostico
            medical.tratamiento = data.tratamiento
            if any(
                value is not None
                for value in (
                    data.peso,
                    data.temperatura,
                    data.historial_alergias,
                    data.vacunas,
                    data.desparasitaciones,
                    data.medicamentos,
                    data.procedimientos,
                    data.examenes_resultados,
                )
            ):
                record = medical.ficha_clinica
                if record is None:
                    record = FichaClinica(proceso_medico_id=process.id)
                    self.db.add(record)
                record.peso = data.peso
                record.temperatura = data.temperatura
                record.historial_alergias = data.historial_alergias
                record.vacunas = data.vacunas
                record.desparasitaciones = data.desparasitaciones
                record.medicamentos = data.medicamentos
                record.procedimientos = data.procedimientos
                record.examenes_resultados = data.examenes_resultados
        else:
            aesthetic = process.proceso_estetica
            if aesthetic is None:
                aesthetic = ProcesoAtencionEstetica(proceso_id=process.id)
                self.db.add(aesthetic)
            aesthetic.notas_especiales_estilista = data.observaciones
        appointment.estado = EstadoCita.ATENDIDA
        appointment.estado_actualizado_por = veterinarian.id
        process.fecha_fin = datetime.datetime.now(datetime.timezone.utc)
        self.db.commit()
        return self.get_clinical_record_for_process(process.id)

    def create_initial_clinical_record(
        self, veterinarian: Usuario, pet_id: int, data: ClinicalRecordCreate
    ) -> ProcesoAtencion:
        pet = self.db.get(Mascota, pet_id)
        if pet is None or not self.db.scalar(select(Cita.id).where(
            Cita.mascota_id == pet_id, Cita.veterinario_id == veterinarian.id
        ).limit(1)):
            raise AppointmentNotFoundError
        process = ProcesoAtencion(
            cita_id=None,
            mascota_id=pet_id,
            tipo=TipoProcesoAtencion.MEDICA,
            observaciones=data.observaciones,
            motivo_consulta=data.motivo_consulta,
            anamnesis=data.anamnesis,
            proxima_fecha_control=data.proxima_fecha_control,
            fecha_fin=datetime.datetime.now(datetime.timezone.utc),
        )
        self.db.add(process)
        self.db.flush()
        self._populate_medical_process(veterinarian, process, data)
        self.db.commit()
        return self.get_clinical_record_for_process(process.id)

    def _populate_medical_process(
        self, veterinarian: Usuario, process: ProcesoAtencion, data: ClinicalRecordCreate
    ) -> None:
        medical = ProcesoAtencionMedica(proceso_id=process.id, veterinario_id=veterinarian.id)
        medical.diagnostico = data.diagnostico
        medical.tratamiento = data.tratamiento
        self.db.add(medical)
        if any(value is not None for value in (
            data.peso, data.temperatura, data.historial_alergias, data.vacunas,
            data.desparasitaciones, data.medicamentos, data.procedimientos,
            data.examenes_resultados,
        )):
            self.db.add(FichaClinica(
                proceso_medico_id=process.id,
                peso=data.peso,
                temperatura=data.temperatura,
                historial_alergias=data.historial_alergias,
                vacunas=data.vacunas,
                desparasitaciones=data.desparasitaciones,
                medicamentos=data.medicamentos,
                procedimientos=data.procedimientos,
                examenes_resultados=data.examenes_resultados,
            ))

    def get_clinical_record_for_process(self, process_id: int) -> ProcesoAtencion:
        return self.db.scalar(select(ProcesoAtencion).where(ProcesoAtencion.id == process_id).options(
            selectinload(ProcesoAtencion.cita).selectinload(Cita.servicio),
            selectinload(ProcesoAtencion.proceso_medico).selectinload(ProcesoAtencionMedica.ficha_clinica),
            selectinload(ProcesoAtencion.proceso_medico).selectinload(ProcesoAtencionMedica.veterinario).selectinload(Veterinario.usuario),
        ))

    def get_pet_history(self, pet_id: int, *, client_id: int | None = None, veterinarian_id: int | None = None) -> list[ProcesoAtencion]:
        statement = select(ProcesoAtencion).where(ProcesoAtencion.mascota_id == pet_id)
        if client_id is not None:
            statement = statement.join(ProcesoAtencion.mascota).where(Mascota.cliente_id == client_id)
        if veterinarian_id is not None:
            statement = statement.outerjoin(ProcesoAtencion.cita).outerjoin(
                ProcesoAtencion.proceso_medico
            ).where(
                or_(
                    Cita.veterinario_id == veterinarian_id,
                    ProcesoAtencionMedica.veterinario_id == veterinarian_id,
                )
            )
        return list(self.db.scalars(statement.options(
            selectinload(ProcesoAtencion.cita).selectinload(Cita.servicio),
            selectinload(ProcesoAtencion.proceso_medico).selectinload(ProcesoAtencionMedica.ficha_clinica),
            selectinload(ProcesoAtencion.proceso_medico).selectinload(ProcesoAtencionMedica.veterinario).selectinload(Veterinario.usuario),
        ).order_by(ProcesoAtencion.fecha_inicio.desc())).all())

    def get_notifications(self, user_id: int) -> list[Notificacion]:
        return list(self.db.scalars(select(Notificacion).where(
            Notificacion.usuario_id == user_id
        ).order_by(Notificacion.fecha_creacion.desc()).limit(50)).all())

    def mark_notification_read(self, user_id: int, notification_id: int) -> Notificacion | None:
        notification = self.db.scalar(select(Notificacion).where(
            Notificacion.id == notification_id,
            Notificacion.usuario_id == user_id,
        ))
        if notification is None:
            return None
        notification.leida = True
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def _confirm_without_overlap(self, appointment: Cita, veterinarian_id: int, scheduled_at: datetime.datetime) -> None:
        if not self._has_schedule(veterinarian_id, scheduled_at, appointment.servicio.duracion_estimada_min):
            raise InvalidScheduleError("El veterinario no tiene disponibilidad en ese horario")
        candidate_end = scheduled_at + datetime.timedelta(minutes=appointment.servicio.duracion_estimada_min)
        if self._has_block(veterinarian_id, scheduled_at, candidate_end):
            raise InvalidScheduleError("El veterinario no está disponible en ese horario")
        self.db.execute(text("SELECT pg_advisory_xact_lock(735291)"))
        existing = self.db.scalars(
            select(Cita)
            .join(Cita.servicio)
            .where(
                Cita.veterinario_id == veterinarian_id,
                Cita.id != appointment.id,
                Cita.estado.in_(ACTIVE_BOOKING_STATES),
            )
        ).all()
        for item in existing:
            item_end = item.fecha_hora_programada + datetime.timedelta(minutes=item.servicio.duracion_estimada_min)
            if scheduled_at < item_end and item.fecha_hora_programada < candidate_end:
                raise AppointmentConflictError

    def _has_conflict(
        self,
        veterinarian_id: int,
        start: datetime.datetime,
        service: Servicio,
        excluded_appointment_id: int | None = None,
    ) -> bool:
        end = start + datetime.timedelta(minutes=service.duracion_estimada_min)
        existing = self.db.scalars(
            select(Cita)
            .join(Cita.servicio)
            .where(Cita.veterinario_id == veterinarian_id, Cita.estado.in_(ACTIVE_BOOKING_STATES))
        ).all()
        return any(
            item.id != excluded_appointment_id
            and start < item.fecha_hora_programada + datetime.timedelta(minutes=item.servicio.duracion_estimada_min)
            and item.fecha_hora_programada < end
            for item in existing
        )

    def _has_block(self, veterinarian_id: int, start: datetime.datetime, end: datetime.datetime) -> bool:
        return self.db.scalar(select(BloqueoHorario.id).where(
            BloqueoHorario.veterinario_id == veterinarian_id,
            BloqueoHorario.fecha_hora_inicio < end,
            BloqueoHorario.fecha_hora_fin > start,
        ).limit(1)) is not None

    def _has_schedule_for_any_veterinarian(self, start: datetime.datetime, duration_min: int) -> bool:
        weekday = start.astimezone(CLINIC_TIMEZONE).weekday()
        schedules = self.db.execute(
            select(HorarioVeterinario.id, HorarioVeterinario.veterinario_id).where(
                HorarioVeterinario.dia_semana == weekday,
                HorarioVeterinario.activo,
                HorarioVeterinario.hora_inicio <= start.astimezone(CLINIC_TIMEZONE).time(),
                HorarioVeterinario.hora_fin >= (
                    start.astimezone(CLINIC_TIMEZONE) + datetime.timedelta(minutes=duration_min)
                ).time(),
            )
        ).all()
        end = start + datetime.timedelta(minutes=duration_min)
        return any(not self._has_block(veterinarian_id, start, end) for _, veterinarian_id in schedules)

    def _has_schedule(self, veterinarian_id: int, start: datetime.datetime, duration_min: int) -> bool:
        local_start = start.astimezone(CLINIC_TIMEZONE)
        local_end = local_start + datetime.timedelta(minutes=duration_min)
        has_schedule = self.db.scalar(
            select(HorarioVeterinario.id).where(
                HorarioVeterinario.veterinario_id == veterinarian_id,
                HorarioVeterinario.dia_semana == local_start.weekday(),
                HorarioVeterinario.activo,
                HorarioVeterinario.hora_inicio <= local_start.time(),
                HorarioVeterinario.hora_fin >= local_end.time(),
            ).limit(1)
        ) is not None
        return has_schedule and not self._has_block(
            veterinarian_id,
            start,
            start + datetime.timedelta(minutes=duration_min),
        )

    def _get_owned_appointment(
        self, client_id: int, appointment_id: int, *, for_update: bool = False
    ) -> Cita | None:
        statement = select(Cita).join(Cita.mascota).where(
            Cita.id == appointment_id, Mascota.cliente_id == client_id
        )
        if for_update:
            statement = statement.with_for_update()
        return self.db.scalar(statement)

    def _get_appointment_with_details(
        self, appointment_id: int, *, for_update: bool = False
    ) -> Cita | None:
        statement = (
            select(Cita)
            .where(Cita.id == appointment_id)
            .options(
                selectinload(Cita.mascota),
                selectinload(Cita.servicio),
                selectinload(Cita.proceso_atencion),
                selectinload(Cita.mascota).selectinload(Mascota.cliente).selectinload(Cliente.usuario),
            )
        )
        if for_update:
            statement = statement.with_for_update()
        return self.db.scalars(statement).one_or_none()

    def _validate_schedule(self, scheduled_at: datetime.datetime, duration_min: int) -> None:
        now = datetime.datetime.now(datetime.timezone.utc)
        if scheduled_at.astimezone(datetime.timezone.utc) <= now:
            raise InvalidScheduleError("La cita debe programarse en el futuro")
        local_start = scheduled_at.astimezone(CLINIC_TIMEZONE)
        local_end = local_start + datetime.timedelta(minutes=duration_min)
        if local_start.weekday() == 6 or local_start.time() < datetime.time(8) or local_end.time() > datetime.time(19):
            raise InvalidScheduleError("El horario de atención es de lunes a sábado, de 08:00 a 19:00")
