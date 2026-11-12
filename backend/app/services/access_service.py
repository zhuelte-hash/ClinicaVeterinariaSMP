import datetime as dt
import hashlib
import hmac
import secrets

from fastapi import HTTPException
from sqlalchemy import select, update

from app.config import get_settings
from app.models.operations import DesafioCuenta, MensajeSalida, Sucursal
from app.models.user import TipoUsuario, Usuario
from app.services.user_service import UserService


def now():
    return dt.datetime.now(dt.timezone.utc)


def aware(value):
    return value.replace(tzinfo=dt.timezone.utc) if value and value.tzinfo is None else value


def digest(value):
    return hmac.new(get_settings().secret_key.encode(), value.encode(), hashlib.sha256).hexdigest()


class AccessService:
    def __init__(self, db):
        self.db = db
        self.users = UserService(db)

    def authenticate(self, identifier, password):
        user = self.db.scalar(select(Usuario).where(Usuario.correo == identifier.strip().lower()).with_for_update())
        if user and user.bloqueado_hasta and aware(user.bloqueado_hasta) > now():
            raise HTTPException(423, "Cuenta bloqueada temporalmente por intentos fallidos. Intenta más tarde.")
        if user and user.bloqueado_hasta:
            user.intentos_fallidos = 0
            user.bloqueado_hasta = None
        valid = user is not None and self.users.verify_password(password, user.contrasena)
        if not valid:
            if user:
                user.intentos_fallidos += 1
                if user.intentos_fallidos >= 5:
                    user.bloqueado_hasta = now() + dt.timedelta(minutes=get_settings().login_lock_minutes)
                self.db.commit()
            raise HTTPException(401, "Correo o contraseña incorrectos")
        if not user.activo:
            raise HTTPException(403, "Esta cuenta fue desactivada")
        if not user.correo_verificado:
            raise HTTPException(403, "Verifica tu correo antes de iniciar sesión")
        user.intentos_fallidos = 0
        user.bloqueado_hasta = None
        self.db.commit()
        return user

    def issue(self, user, purpose):
        latest = self.db.scalar(select(DesafioCuenta).where(DesafioCuenta.usuario_id == user.id, DesafioCuenta.proposito == purpose).order_by(DesafioCuenta.id.desc()))
        if latest and (now() - aware(latest.creado_en)).total_seconds() < 60:
            raise HTTPException(429, "Espera un minuto antes de solicitar otro correo")
        self.db.execute(update(DesafioCuenta).where(DesafioCuenta.usuario_id == user.id, DesafioCuenta.proposito == purpose, DesafioCuenta.usado_en.is_(None)).values(usado_en=now()))
        secret = f"{secrets.randbelow(1_000_000):06d}" if purpose == "verificar" else secrets.token_urlsafe(40)
        challenge = DesafioCuenta(usuario_id=user.id, proposito=purpose, secreto_hash=digest(f"{user.id}:{purpose}:{secret}"), expira_en=now() + dt.timedelta(minutes=15 if purpose == "verificar" else 60))
        self.db.add(challenge)
        self.db.flush()
        message = (f"Tu código de verificación es {secret}. Caduca en 15 minutos." if purpose == "verificar" else f"Define una nueva contraseña en {get_settings().frontend_url}/recuperar-clave?token={secret}&correo={user.correo}. El enlace caduca en una hora y solo puede utilizarse una vez.")
        self.db.add(MensajeSalida(clave=f"cuenta:{challenge.id}", canal="correo", evento=purpose, destinatario=user.correo, usuario_id=user.id, asunto="Verifica tu cuenta" if purpose == "verificar" else "Recuperación de contraseña", contenido=message))
        self.db.commit()

    def verify(self, email, secret):
        user = self.users.get_by_email(email)
        self._use(user, "verificar", secret)
        user.correo_verificado = True
        self.db.commit()
        from app.services.messaging_service import MessagingService
        MessagingService(self.db).to_user(user, "bienvenida", f"bienvenida:{user.id}", {"nombre": user.nombre})
        self.db.commit()
        return user

    def reset(self, email, token, password):
        user = self.users.get_by_email(email)
        self._use(user, "recuperar", token)
        user.contrasena = self.users._hash_password(password)
        user.version_sesion += 1
        user.intentos_fallidos = 0
        user.bloqueado_hasta = None
        self.db.commit()

    def _use(self, user, purpose, secret):
        challenge = self.db.scalar(select(DesafioCuenta).where(DesafioCuenta.usuario_id == user.id, DesafioCuenta.proposito == purpose, DesafioCuenta.usado_en.is_(None)).order_by(DesafioCuenta.id.desc()).with_for_update()) if user else None
        if not challenge or challenge.intentos >= 5 or aware(challenge.expira_en) <= now():
            raise HTTPException(400, "El código o enlace es inválido, fue usado o ha caducado")
        if not hmac.compare_digest(challenge.secreto_hash, digest(f"{user.id}:{purpose}:{secret}")):
            challenge.intentos += 1
            self.db.commit()
            raise HTTPException(400, "El código o enlace es inválido")
        challenge.usado_en = now()

    def set_active(self, actor, user, active):
        if actor.id == user.id:
            raise HTTPException(409, "No puedes desactivar tu propia cuenta")
        if user.tipo == TipoUsuario.CLIENTE:
            raise HTTPException(422, "Esta acción corresponde al personal de la clínica")
        if user.activo != active:
            self.db.info["actor_id"] = actor.id
            user.activo = active
            user.version_sesion += 1
        self.db.commit()
        return user
