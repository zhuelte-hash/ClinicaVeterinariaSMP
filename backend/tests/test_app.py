import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.security import get_current_active_user
from app.models.user import TipoUsuario, Usuario
from app.services.appointment_service import AppointmentService
from app.routers.users import delete_user


client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_usuarios_routes_are_documented() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/usuarios" in paths
    assert "/usuarios/{user_id}" in paths


def test_administrador_no_puede_eliminar_su_cuenta() -> None:
    admin = Usuario(
        id=7,
        nombre="Admin",
        correo="admin@example.com",
        contrasena="hash",
        tipo=TipoUsuario.ADMINISTRADOR,
    )

    with pytest.raises(HTTPException) as exc_info:
        delete_user(user_id=7, db=None, current_admin=admin)  # type: ignore[arg-type]

    assert exc_info.value.status_code == 409


def test_caja_routes_are_documented() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/caja/resumen" in paths
    assert "/caja/abrir" in paths
    assert "/caja/cerrar" in paths
    assert "/auth/register" in paths


def test_portal_citas_routes_are_documented() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/portal/mascotas" in paths
    assert "/portal/servicios" in paths
    assert "/portal/citas" in paths
    assert "/portal/citas/{appointment_id}/cancelar" in paths
    assert "/portal/citas/{appointment_id}/aceptar-horario" in paths
    assert "/portal/mascotas/{pet_id}/historial" in paths
    assert "/portal/notificaciones" in paths


def test_guest_can_read_booking_options_but_not_private_portal_data(monkeypatch: pytest.MonkeyPatch) -> None:
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(AppointmentService, "get_services", lambda self: [])
    monkeypatch.setattr(AppointmentService, "get_availability", lambda self, service_id, fecha: [])
    try:
        assert client.get("/portal/servicios").status_code == 200
        assert client.get("/portal/disponibilidad", params={"servicio_id": 1, "fecha": "2026-10-10"}).status_code == 200
        for path in ("/portal/mascotas", "/portal/citas", "/portal/mascotas/1/historial"):
            assert client.get(path).status_code == 401
        assert client.post("/portal/citas", json={}).status_code == 401
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_veterinarian_routes_are_documented() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/portal/veterinario/resumen" in paths
    assert "/portal/veterinario/horarios" in paths
    assert "/portal/veterinario/bloqueos" in paths
    assert "/portal/veterinario/solicitudes/{appointment_id}/atencion" in paths
    assert "/portal/veterinario/mascotas/{pet_id}/historial" in paths
    assert "/portal/veterinario/clientes" in paths
    assert "/portal/veterinario/clientes/{client_id}" in paths


def test_punto_venta_routes_are_documented() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/caja/productos" in paths
    assert "/caja/categorias" in paths
    assert "/caja/clientes" in paths
    assert "/caja/servicios" in paths
    assert "/caja/ventas" in paths
    assert "/caja/ventas/{order_id}/boleta" in paths


def test_sales_api_routes_and_admin_role() -> None:
    paths = client.get("/openapi.json").json()["paths"]
    for path in ("/api/ventas", "/api/admin/ventas", "/api/admin/ventas/resumen",
                 "/api/admin/ventas/{order_id}", "/api/admin/ventas/{order_id}/anular"):
        assert path in paths

    cashier = Usuario(id=7, nombre="Caja", correo="caja@example.com",
                      contrasena="hash", tipo=TipoUsuario.CAJERO)
    app.dependency_overrides[get_current_active_user] = lambda: cashier
    try:
        assert client.get("/api/admin/ventas").status_code == 403
        assert client.get("/api/admin/ventas/resumen").status_code == 403
        assert client.get("/api/admin/ventas/1").status_code == 403
        assert client.post("/api/admin/ventas/1/anular").status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)
