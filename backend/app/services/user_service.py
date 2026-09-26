from passlib.context import CryptContext
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import Administrador, Cajero, Cliente, TipoUsuario, Usuario, Veterinario
from app.schemas.auth import ClientRegisterRequest
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

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except ValueError:
            return False

    def get_all(self, skip: int = 0, limit: int = 100) -> list[Usuario]:
        statement = select(Usuario).order_by(Usuario.id).offset(skip).limit(limit)
        return list(self.db.scalars(statement).all())

    def get_by_id(self, user_id: int) -> Usuario | None:
        return self.db.get(Usuario, user_id)

    def get_by_email(self, email: str) -> Usuario | None:
        statement = select(Usuario).where(
            func.lower(Usuario.correo) == email.strip().lower()
        )
        return self.db.scalar(statement)

    def get_by_identifier(self, identifier: str) -> Usuario | None:
        return self.get_by_email(identifier)

    def create(self, data: UsuarioCreate) -> Usuario:
        user = Usuario(
            nombre=data.nombre,
            correo=str(data.correo),
            contrasena=self._hash_password(data.contrasena),
            tipo=data.tipo,
        )
        self._apply_role_profile(user, data)
        self.db.add(user)
        return self._commit(user)

    def create_client(self, data: ClientRegisterRequest) -> Usuario:
        user = Usuario(
            nombre=data.nombre,
            correo=str(data.correo),
            contrasena=self._hash_password(data.password),
            tipo=TipoUsuario.CLIENTE,
        )
        user.cliente = Cliente(telefono=data.telefono)
        self.db.add(user)
        return self._commit(user)

    def update(self, user: Usuario, data: UsuarioUpdate) -> Usuario:
        update_data = data.model_dump(exclude_unset=True)
        if "tipo" in update_data and update_data["tipo"] != user.tipo:
            raise ValueError("El rol no se puede cambiar; crea el perfil con sus datos profesionales")
        profile_data = {
            key: update_data.pop(key, None)
            for key in ("telefono", "colegiatura", "especialidad")
            if key in update_data
        }
        if "contrasena" in update_data:
            update_data["contrasena"] = self._hash_password(update_data["contrasena"])
        for field, value in update_data.items():
            setattr(user, field, value)
        self._apply_role_profile(user, profile_data, allow_existing=True)
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

    def _apply_role_profile(
        self,
        user: Usuario,
        data: UsuarioCreate | UsuarioUpdate | dict,
        *,
        allow_existing: bool = False,
    ) -> None:
        values = data if isinstance(data, dict) else data.model_dump(exclude_unset=True)
        if user.tipo == TipoUsuario.CLIENTE:
            if user.cliente is None:
                user.cliente = Cliente(telefono=values.get("telefono"))
            elif "telefono" in values:
                user.cliente.telefono = values["telefono"]
        elif user.tipo == TipoUsuario.VETERINARIO:
            veterinarian = user.veterinario
            colegiatura = values.get("colegiatura")
            if veterinarian is None:
                if not colegiatura:
                    raise ValueError("La colegiatura es obligatoria para un veterinario")
                veterinarian = Veterinario(
                    colegiatura=colegiatura,
                    especialidad=values.get("especialidad"),
                )
                user.veterinario = veterinarian
            elif allow_existing:
                if colegiatura is not None:
                    veterinarian.colegiatura = colegiatura
                if "especialidad" in values:
                    veterinarian.especialidad = values["especialidad"]
        elif user.tipo == TipoUsuario.CAJERO and user.cajero is None:
            user.cajero = Cajero()
        elif user.tipo == TipoUsuario.ADMINISTRADOR and user.administrador is None:
            user.administrador = Administrador()
