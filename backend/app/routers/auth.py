from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import Usuario
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UsuarioRead
from app.security import create_access_token, get_current_active_user
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


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
