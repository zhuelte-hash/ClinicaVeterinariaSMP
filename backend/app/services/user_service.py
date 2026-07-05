from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def _hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def get_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        return self.db.query(User).offset(skip).limit(limit).all()

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def get_by_username(self, username: str) -> User | None:
        return self.db.query(User).filter(User.username == username).first()

    def create(self, data: UserCreate) -> User:
        user = User(
            email=data.email,
            username=data.username,
            full_name=data.full_name,
            hashed_password=self._hash_password(data.password),
            is_active=data.is_active,
            is_superuser=data.is_superuser,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User, data: UserUpdate) -> User:
        update_data = data.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = self._hash_password(update_data.pop("password"))
        for field, value in update_data.items():
            setattr(user, field, value)
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user: User) -> None:
        self.db.delete(user)
        self.db.commit()
