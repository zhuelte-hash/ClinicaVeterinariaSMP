from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user import UsuarioCreate, UsuarioRead, UsuarioUpdate
from app.security import get_current_admin_user
from app.services.user_service import (
    CorreoDuplicadoError,
    UserService,
    UsuarioReferenciadoError,
)

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "",
    response_model=list[UsuarioRead],
    dependencies=[Depends(get_current_admin_user)],
)
def get_users(
    db: DbSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    service = UserService(db)
    return service.get_all(skip=skip, limit=limit)


@router.get(
    "/{user_id}",
    response_model=UsuarioRead,
    dependencies=[Depends(get_current_admin_user)],
)
def get_user(user_id: int, db: DbSession):
    service = UserService(db)
    user = service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@router.post(
    "",
    response_model=UsuarioRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_admin_user)],
)
def create_user(user_data: UsuarioCreate, db: DbSession):
    service = UserService(db)
    try:
        return service.create(user_data)
    except CorreoDuplicadoError as exc:
        raise HTTPException(status_code=409, detail="El correo ya esta registrado") from exc


@router.patch(
    "/{user_id}",
    response_model=UsuarioRead,
    dependencies=[Depends(get_current_admin_user)],
)
def update_user(user_id: int, user_data: UsuarioUpdate, db: DbSession):
    service = UserService(db)
    user = service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    try:
        return service.update(user, user_data)
    except CorreoDuplicadoError as exc:
        raise HTTPException(status_code=409, detail="El correo ya esta registrado") from exc


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin_user)],
)
def delete_user(user_id: int, db: DbSession) -> Response:
    service = UserService(db)
    user = service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    try:
        service.delete(user)
    except UsuarioReferenciadoError as exc:
        raise HTTPException(
            status_code=409,
            detail="El usuario tiene registros asociados y no se puede eliminar",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
