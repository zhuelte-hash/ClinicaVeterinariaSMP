from passlib.context import CryptContext
<<<<<<< Updated upstream
from sqlalchemy import or_
=======
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
>>>>>>> Stashed changes
from sqlalchemy.orm import Session

from app.models.user import Usuario
from app.schemas.user import UsuarioCreate, UsuarioUpdate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class CorreoDuplicadoError(Exception):
    pass


class UsuarioReferenciadoError(Exception):
    pass


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def _hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

<<<<<<< Updated upstream
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except ValueError:
            return False

    def get_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        return self.db.query(User).offset(skip).limit(limit).all()
=======
    def get_all(self, skip: int = 0, limit: int = 100) -> list[Usuario]:
        statement = select(Usuario).order_by(Usuario.id).offset(skip).limit(limit)
        return list(self.db.scalars(statement).all())
>>>>>>> Stashed changes

    def get_by_id(self, user_id: int) -> Usuario | None:
        return self.db.get(Usuario, user_id)

    def get_by_email(self, email: str) -> Usuario | None:
        statement = select(Usuario).where(
            func.lower(Usuario.correo) == email.strip().lower()
        )
        return self.db.scalar(statement)

<<<<<<< Updated upstream
    def get_by_username(self, username: str) -> User | None:
        return self.db.query(User).filter(User.username == username).first()

    def get_by_identifier(self, identifier: str) -> User | None:
        return self.db.query(User).filter(
            or_(User.email == identifier, User.username == identifier)
        ).first()

    def create(self, data: UserCreate) -> User:
        user = User(
            email=data.email,
            username=data.username,
            full_name=data.full_name,
            hashed_password=self._hash_password(data.password),
            is_active=True,
            is_superuser=False,
=======
    def create(self, data: UsuarioCreate) -> Usuario:
        user = Usuario(
            nombre=data.nombre,
            correo=str(data.correo),
            contrasena=self._hash_password(data.contrasena),
            tipo=data.tipo,
>>>>>>> Stashed changes
        )
        self.db.add(user)
        return self._commit(user)

    def update(self, user: Usuario, data: UsuarioUpdate) -> Usuario:
        update_data = data.model_dump(exclude_unset=True)
        if "contrasena" in update_data:
            update_data["contrasena"] = self._hash_password(update_data["contrasena"])
        for field, value in update_data.items():
            setattr(user, field, value)
        return self._commit(user)

    def delete(self, user: Usuario) -> None:
        self.db.delete(user)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise UsuarioReferenciadoError from exc

    def _commit(self, user: Usuario) -> Usuario:
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise CorreoDuplicadoError from exc
        self.db.refresh(user)
        return user
