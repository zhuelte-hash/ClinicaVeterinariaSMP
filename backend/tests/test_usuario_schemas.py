import pytest
from pydantic import ValidationError

from app.models.user import TipoUsuario
from app.schemas.user import UsuarioCreate, UsuarioUpdate


def test_usuario_create_normaliza_datos() -> None:
    usuario = UsuarioCreate(
        nombre="  Ana   Torres ",
        correo="ANA@EXAMPLE.COM",
        contrasena="segura123",
        tipo=TipoUsuario.CLIENTE,
    )

    assert usuario.nombre == "Ana Torres"
    assert usuario.correo == "ana@example.com"


def test_usuario_create_rechaza_contrasena_corta() -> None:
    with pytest.raises(ValidationError):
        UsuarioCreate(
            nombre="Ana Torres",
            correo="ana@example.com",
            contrasena="corta",
            tipo=TipoUsuario.CLIENTE,
        )


def test_usuario_update_rechaza_nulo_explicito() -> None:
    with pytest.raises(ValidationError):
        UsuarioUpdate(nombre=None)
