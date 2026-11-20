"""Código de asistencia ligado a la versión del horario y al contacto autorizado."""
import datetime as dt
from sqlalchemy import select

from app.models.operations import EventoCita
from app.services.access_service import aware, digest


def schedule_event(db, appointment):
    return db.scalar(select(EventoCita).where(
        EventoCita.cita_id == appointment.id,
        EventoCita.actual["fecha_hora_programada"].as_string().is_not(None)
    ).order_by(EventoCita.id.desc()).limit(1))


def attendance_code(db, appointment):
    owner = appointment.mascota.cliente.usuario
    event = schedule_event(db, appointment)
    phone = "".join(filter(str.isdigit, appointment.telefono_contacto or owner.telefono or ""))
    if len(phone) == 9:
        phone = "51" + phone
    scheduled = aware(appointment.fecha_hora_programada).astimezone(dt.timezone.utc).isoformat()
    return digest(f"asistencia:{appointment.id}:{scheduled}:{event.id if event else 0}:{owner.id}:{owner.version_sesion}:{phone}:{appointment.sucursal_id}")[:16]
