import pytest
from pydantic import ValidationError

from app.models.user import TipoUsuario
from app.schemas.auth import ClientRegisterRequest
from app.schemas.appointments import AppointmentCreate, ScheduleUpdate
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


def test_usuario_veterinario_requiere_colegiatura() -> None:
    with pytest.raises(ValidationError):
        UsuarioCreate(
            nombre="Veterinario Sin Perfil",
            correo="vet@example.com",
            contrasena="segura123",
            tipo=TipoUsuario.VETERINARIO,
        )


def test_registro_cliente_normaliza_datos() -> None:
    cliente = ClientRegisterRequest(
        nombre="  Maria   Lopez ",
        correo="MARIA@EXAMPLE.COM",
        password="segura123",
        telefono=" 999999999 ",
    )

    assert cliente.nombre == "Maria Lopez"
    assert cliente.correo == "maria@example.com"
    assert cliente.telefono == "999999999"


def test_reserva_requiere_veterinario_y_zona_horaria() -> None:
    with pytest.raises(ValidationError):
        AppointmentCreate(
            mascota_id=1,
            servicio_id=1,
            fecha_hora_programada="2030-01-02T10:00:00",
        )

    reserva = AppointmentCreate(
        mascota_id=1,
        servicio_id=1,
        veterinario_id=2,
        fecha_hora_programada="2030-01-02T10:00:00-05:00",
    )
    assert reserva.veterinario_id == 2


def test_horario_rechaza_fin_anterior_al_inicio() -> None:
    with pytest.raises(ValidationError):
        ScheduleUpdate(
            dia_semana=0,
            hora_inicio="12:00",
            hora_fin="10:00",
        )
