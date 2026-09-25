import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.clinic import Cita, EstadoCita, Mascota, Servicio
from app.models.user import Usuario
from app.schemas.appointments import AppointmentCreate, PetCreate

CLINIC_TIMEZONE = ZoneInfo("America/Lima")


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

    def create_appointment(self, client: Usuario, data: AppointmentCreate) -> Cita:
        pet = self.db.get(Mascota, data.mascota_id)
        if pet is None or pet.cliente_id != client.id:
            raise PetNotFoundError
        if self.db.get(Servicio, data.servicio_id) is None:
            raise ServiceNotFoundError
        self._validate_schedule(data.fecha_hora_programada)

        appointment = Cita(
            mascota_id=data.mascota_id,
            servicio_id=data.servicio_id,
            fecha_hora_programada=data.fecha_hora_programada,
            motivo=data.motivo,
            es_urgente=data.es_urgente,
        )
        self.db.add(appointment)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise AppointmentConflictError from exc
        return self._get_appointment_with_details(appointment.id)

    def cancel_appointment(self, client_id: int, appointment_id: int) -> Cita:
        appointment = self._get_owned_appointment(client_id, appointment_id)
        if appointment is None:
            raise AppointmentNotFoundError
        if appointment.estado not in {
            EstadoCita.PENDIENTE,
            EstadoCita.CONFIRMADA,
            EstadoCita.REPROGRAMADA,
        }:
            raise AppointmentNotCancelableError
        appointment.estado = EstadoCita.CANCELADA
        self.db.commit()
        return self._get_appointment_with_details(appointment.id)

    def _get_owned_appointment(self, client_id: int, appointment_id: int) -> Cita | None:
        statement = (
            select(Cita)
            .join(Cita.mascota)
            .where(Cita.id == appointment_id, Mascota.cliente_id == client_id)
        )
        return self.db.scalar(statement)

    def _get_appointment_with_details(self, appointment_id: int) -> Cita:
        statement = (
            select(Cita)
            .where(Cita.id == appointment_id)
            .options(selectinload(Cita.mascota), selectinload(Cita.servicio))
        )
        return self.db.scalars(statement).one()

    def _validate_schedule(self, scheduled_at: datetime.datetime) -> None:
        now = datetime.datetime.now(datetime.timezone.utc)
        if scheduled_at.astimezone(datetime.timezone.utc) <= now:
            raise InvalidScheduleError("La cita debe programarse en el futuro")
        local_time = scheduled_at.astimezone(CLINIC_TIMEZONE)
        if local_time.weekday() == 6 or not 8 <= local_time.hour < 19:
            raise InvalidScheduleError(
                "El horario de atencion es de lunes a sabado, de 08:00 a 19:00"
            )
