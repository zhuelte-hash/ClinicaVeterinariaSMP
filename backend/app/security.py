from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.user import PermisoRol, TipoUsuario, Usuario
from app.schemas.auth import TokenPayload
from app.services.user_service import UserService
from app.permissions import default_permission, portal_permission

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def create_access_token(user_id: int, version: int = 0) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return jwt.encode(
        {"sub": str(user_id), "exp": expires_at, "version": version},
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def decode_access_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        subject = payload.get("sub")
        if subject is None:
            raise credentials_exception()
        return TokenPayload(user_id=int(subject), version=int(payload.get("version", 0)))
    except (JWTError, TypeError, ValueError):
        raise credentials_exception()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    token_data = decode_access_token(token)
    user = UserService(db).get_by_id(token_data.user_id)
    if user is None or user.version_sesion != token_data.version:
        raise credentials_exception()
    db.info["actor_id"] = user.id
    return user


def get_current_active_user(request: Request, user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)) -> Usuario:
    if not user.activo or not user.correo_verificado:
        raise HTTPException(403, "La cuenta está desactivada o su correo no está verificado")
    try:
        branch = int(request.headers.get("X-Sucursal-ID", user.sucursal_id or 1))
    except ValueError as exc:
        raise HTTPException(422, "Sucursal no válida") from exc
    if branch < 1 or (user.tipo not in {TipoUsuario.ADMINISTRADOR, TipoUsuario.CLIENTE} and branch != user.sucursal_id):
        raise HTTPException(403, "No tienes acceso a esta sucursal")
    from app.models.operations import Sucursal
    location = db.get(Sucursal, branch)
    if location is None or not location.activa:
        raise HTTPException(422, "La sucursal no está disponible")
    db.info["sucursal_id"] = branch
    permission = portal_permission(request.url.path, request.method)
    if permission:
        check_permission(db, user, *permission)
    return user


def check_permission(db, user, module, action="ver"):
    permission = db.scalar(select(PermisoRol).where(PermisoRol.rol == user.tipo, PermisoRol.modulo == module))
    allowed = default_permission(user.tipo, module, action) if permission is None else permission.puede_ver and getattr(permission, f"puede_{action}", False)
    if not allowed:
        raise HTTPException(403, "No tienes permiso para realizar esta acción en este módulo")


def get_current_admin_user(
    user: Usuario = Depends(get_current_active_user),
) -> Usuario:
    if user.tipo != TipoUsuario.ADMINISTRADOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )
    return user


def get_current_cashier_user(
    user: Usuario = Depends(get_current_active_user),
) -> Usuario:
    if user.tipo != TipoUsuario.CAJERO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cashier access required",
        )
    return user


def get_current_client_user(
    user: Usuario = Depends(get_current_active_user),
) -> Usuario:
    if user.tipo != TipoUsuario.CLIENTE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client access required",
        )
    return user


def get_current_veterinarian_user(
    user: Usuario = Depends(get_current_active_user),
) -> Usuario:
    if user.tipo != TipoUsuario.VETERINARIO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Veterinarian access required",
        )
    return user


def require_permission(module: str, action: str = "ver"):
    field = f"puede_{action}"

    def dependency(
        user: Usuario = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ) -> Usuario:
        # La matriz administra únicamente las rutas de administración. Los
        # portales de caja, veterinaria y clientes tienen su propio rol.
        if user.tipo != TipoUsuario.ADMINISTRADOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Se requiere rol de administrador",
            )
        check_permission(db, user, module, action)
        return user

    return dependency
