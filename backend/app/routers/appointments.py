from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import Usuario
from app.schemas.appointments import (
    AppointmentCreate,
    AppointmentRead,
    PetCreate,
    PetRead,
    ServiceRead,
)
from app.security import get_current_client_user
from app.services.appointment_service import (
    AppointmentConflictError,
    AppointmentNotCancelableError,
    AppointmentNotFoundError,
    AppointmentService,
    InvalidScheduleError,
    PetNotFoundError,
    ServiceNotFoundError,
)

router = APIRouter(prefix="/portal", tags=["Portal de clientes"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentClient = Annotated[Usuario, Depends(get_current_client_user)]


@router.get("/mascotas", response_model=list[PetRead])
def get_pets(db: DbSession, client: CurrentClient):
    return AppointmentService(db).get_pets(client.id)


@router.post("/mascotas", response_model=PetRead, status_code=status.HTTP_201_CREATED)
def create_pet(data: PetCreate, db: DbSession, client: CurrentClient):
    return AppointmentService(db).create_pet(client, data)


@router.get("/servicios", response_model=list[ServiceRead])
def get_services(db: DbSession, _client: CurrentClient):
    return AppointmentService(db).get_services()


@router.get("/citas", response_model=list[AppointmentRead])
def get_appointments(db: DbSession, client: CurrentClient):
    return AppointmentService(db).get_appointments(client.id)


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
