import pytest
import datetime
from zoneinfo import ZoneInfo
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


def test_booking_hours_exclude_lunch_and_allow_evening() -> None:
    timezone = ZoneInfo("America/Lima")
    slot = lambda hour, minute=0: datetime.datetime(2026, 10, 8, hour, minute, tzinfo=timezone)
    within = AppointmentService._within_booking_hours
    assert within(slot(8), 30)
    assert within(slot(11, 30), 30)
    assert not within(slot(11, 30), 60)
    assert not within(slot(12), 30)
    assert within(slot(13), 30)
    assert within(slot(19, 30), 30)
    assert not within(slot(19, 30), 60)


def test_veterinarian_routes_are_documented() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/portal/veterinario/resumen" in paths
    assert "/portal/veterinario/horarios" in paths
    assert "/portal/veterinario/bloqueos" in paths
    assert "/portal/veterinario/solicitudes/{appointment_id}/atencion" in paths
    assert "/portal/veterinario/solicitudes/{appointment_id}/atencion/iniciar" in paths
    assert "/portal/veterinario/atenciones/{process_id}/diagnosticos" in paths
    assert "/portal/veterinario/atenciones/{process_id}/ordenes-examen" in paths
    assert "/portal/veterinario/atenciones/{process_id}/receta" in paths
    assert "/portal/veterinario/atenciones/{process_id}/procedimientos" in paths
    assert "/portal/veterinario/atenciones/{process_id}/preventivos" in paths
    assert "/portal/veterinario/mascotas/{pet_id}/historial" in paths
    assert "/portal/veterinario/atenciones/{process_id}/ordenes-examen" in paths
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


def test_catalog_is_public_and_inventory_requires_login() -> None:
    from types import SimpleNamespace

    class FakeSession:
        def scalars(self, statement):
            assert "productos.activo" in str(statement)
            return SimpleNamespace(all=lambda: [SimpleNamespace(
                id=42, sku="WEB-ALI-01", nombre="Alimento", precio_venta=42.90,
                stock_actual=3, stock_minimo=2, activo=True, imagen_url="/logo.png",
                categoria_id=1, categoria=SimpleNamespace(nombre="Alimentos"),
            )])

    app.dependency_overrides[get_db] = lambda: FakeSession()
    try:
        response = client.get("/catalogo/productos")
        assert response.status_code == 200
        assert response.json()[0]["sku"] == "WEB-ALI-01"
        assert client.get("/admin/inventario").status_code == 401
        assert client.patch("/admin/inventario/42", json={"stock_actual": 0}).status_code == 401
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_non_admin_cannot_enter_admin_routes_even_with_enabled_matrix() -> None:
    from types import SimpleNamespace

    cashier = Usuario(id=10, nombre="Caja", correo="caja@example.com",
                      contrasena="hash", tipo=TipoUsuario.CAJERO)
    app.dependency_overrides[get_current_active_user] = lambda: cashier
    app.dependency_overrides[get_db] = lambda: SimpleNamespace(scalar=lambda _: SimpleNamespace(puede_ver=True, puede_editar=True))
    try:
        assert client.get("/admin/productos").status_code == 403
        assert client.get("/admin/inventario").status_code == 403
        assert client.get("/admin/clientes").status_code == 403
        assert client.get("/usuarios").status_code == 403
        assert client.post("/admin/permisos/recomendados").status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)
        app.dependency_overrides.pop(get_db, None)


def test_recommended_roles_leave_administration_to_admin_only() -> None:
    from app.services.admin_service import AdminService, PERMISSION_MODULES

    class FakeSession:
        def __init__(self):
            self.records = []

        def scalars(self, _statement):
            return self

        def all(self):
            return self.records

        def add(self, record):
            self.records.append(record)

        def commit(self):
            pass

    db = FakeSession()
    permissions = AdminService(db).apply_recommended_permissions()
    assert len(permissions) == len(PERMISSION_MODULES) * len(TipoUsuario)
    assert all(permission.puede_editar for permission in permissions if permission.rol == TipoUsuario.ADMINISTRADOR)
    assert all(not permission.puede_ver for permission in permissions if permission.rol != TipoUsuario.ADMINISTRADOR)


def test_staff_listing_filters_clients_before_pagination() -> None:
    from app.services.user_service import UserService

    class FakeSession:
        def scalars(self, statement):
            self.statement = str(statement)
            return self

        def all(self):
            return []

    db = FakeSession()
    assert UserService(db).get_all(solo_personal=True) == []
    assert "usuarios.tipo !=" in db.statement


def test_admin_clients_summary_exposes_appointment_counts() -> None:
    from types import SimpleNamespace
    from app.services.admin_service import AdminService

    admin = Usuario(id=9, nombre="Admin", correo="admin@example.com",
                    contrasena="hash", tipo=TipoUsuario.ADMINISTRADOR)
    app.dependency_overrides[get_current_active_user] = lambda: admin
    app.dependency_overrides[get_db] = lambda: SimpleNamespace(scalar=lambda _: None)
    original = AdminService.get_clients
    AdminService.get_clients = lambda self: [SimpleNamespace(
        id=3, nombre="María", correo="maria@example.com", telefono="987654321",
        direccion=None, mascotas=2, citas=4, ultima_cita=None,
    )]
    try:
        response = client.get("/admin/clientes")
        assert response.status_code == 200
        assert response.json()[0]["mascotas"] == 2
        assert response.json()[0]["citas"] == 4
    finally:
        AdminService.get_clients = original
        app.dependency_overrides.pop(get_current_active_user, None)
        app.dependency_overrides.pop(get_db, None)
