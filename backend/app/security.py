from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import TokenPayload
from app.services.user_service import UserService

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def create_access_token(user_id: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return jwt.encode(
        {"sub": str(user_id), "exp": expires_at},
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
        return TokenPayload(user_id=int(subject))
    except (JWTError, TypeError, ValueError):
        raise credentials_exception()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    token_data = decode_access_token(token)
    user = UserService(db).get_by_id(token_data.user_id)
    if user is None:
        raise credentials_exception()
    return user


def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return user


def get_current_admin_user(user: User = Depends(get_current_active_user)) -> User:
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )
    return user
