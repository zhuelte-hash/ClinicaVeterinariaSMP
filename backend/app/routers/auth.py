from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import Usuario
from app.schemas.auth import ClientRegisterRequest, LoginRequest, PasswordChangeRequest, TokenResponse, EmailRequest, VerifyEmailRequest, ResetPasswordRequest, OwnProfileUpdate
from app.schemas.user import UsuarioRead
from app.security import create_access_token, get_current_active_user
from app.services.user_service import CorreoDuplicadoError, UserService
from app.services.access_service import AccessService
from app.services.messaging_service import deliver_account_email

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(data: ClientRegisterRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    AccessService.require_email_delivery()
    service = UserService(db)
    try:
        user = service.create_client(data, commit=False)
        message_id = AccessService(db).issue(user, "verificar", commit=False)
        db.commit()
    except CorreoDuplicadoError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="El correo ya esta registrado") from exc
    except Exception:
        db.rollback()
        raise
    background_tasks.add_task(deliver_account_email, message_id)
    return TokenResponse(access_token="", user=user, verification_required=True)


@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = AccessService(db).authenticate(credentials.identifier, credentials.password)
    return TokenResponse(access_token=create_access_token(user.id, user.version_sesion), user=user)


@router.post("/verificar-correo", response_model=TokenResponse)
def verify_email(data: VerifyEmailRequest, db: Session = Depends(get_db)):
    user = AccessService(db).verify(str(data.correo), data.codigo)
    return TokenResponse(access_token=create_access_token(user.id, user.version_sesion), user=user)


@router.post("/reenviar-verificacion", status_code=202)
def resend(data: EmailRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    AccessService.require_email_delivery()
    user = UserService(db).get_by_email(str(data.correo))
    if user and user.activo and not user.correo_verificado:
        message_id = AccessService(db).issue(user, "verificar")
        background_tasks.add_task(deliver_account_email, message_id)
    return {"mensaje": "Si la cuenta requiere verificación, recibirás un nuevo código."}


@router.post("/recuperar-clave", status_code=202)
def forgot(data: EmailRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    AccessService.require_email_delivery()
    user = UserService(db).get_by_email(str(data.correo))
    if user and user.activo:
        message_id = AccessService(db).issue(user, "recuperar")
        background_tasks.add_task(deliver_account_email, message_id)
    return {"mensaje": "Si existe una cuenta activa, recibirás un enlace de recuperación."}


@router.post("/restablecer-clave", status_code=204)
def reset(data: ResetPasswordRequest, correo: str, db: Session = Depends(get_db)):
    AccessService(db).reset(correo, data.token, data.password)


@router.patch("/me", response_model=UsuarioRead)
def update_me(data: OwnProfileUpdate, db: Session = Depends(get_db), user: Usuario = Depends(get_current_active_user)):
    user.nombre = data.nombre
    if user.cliente:
        user.cliente.telefono, user.cliente.direccion = data.telefono, data.direccion
    else:
        user.telefono_personal = data.telefono
    db.commit()
    return user


@router.get("/me", response_model=UsuarioRead)
def get_me(current_user: Usuario = Depends(get_current_active_user)):
    return current_user


@router.get("/me/permisos")
def own_permissions(db: Session = Depends(get_db), user: Usuario = Depends(get_current_active_user)):
    from app.services.admin_service import AdminService
    return [item for item in AdminService(db).get_role_permissions() if item.rol == user.tipo]


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
    current_user.version_sesion += 1
    db.commit()
