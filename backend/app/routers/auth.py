from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import Usuario
from app.schemas.auth import ClientRegisterRequest, LoginRequest, PasswordChangeRequest, TokenResponse
from app.schemas.user import UsuarioRead
from app.security import create_access_token, get_current_active_user
from app.services.user_service import CorreoDuplicadoError, UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(data: ClientRegisterRequest, db: Session = Depends(get_db)):
    service = UserService(db)
    try:
        user = service.create_client(data)
    except CorreoDuplicadoError as exc:
        raise HTTPException(status_code=409, detail="El correo ya esta registrado") from exc
    return TokenResponse(access_token=create_access_token(user.id), user=user)


@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    service = UserService(db)
    user = service.get_by_identifier(credentials.identifier)
    if user is None or not service.verify_password(
        credentials.password, user.contrasena
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect identifier or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(user.id), user=user)


@router.get("/me", response_model=UsuarioRead)
def get_me(current_user: Usuario = Depends(get_current_active_user)):
    return current_user


@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    data: PasswordChangeRequest,
    current_user: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> None:
    service = UserService(db)
    if not service.verify_password(data.current_password, current_user.contrasena):
        raise HTTPException(status_code=400, detail="La contraseña actual no es correcta")
    current_user.contrasena = service._hash_password(data.new_password)
    db.commit()
