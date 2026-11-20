"""Aceptación nativa de las cinco historias en PostgreSQL temporal migrado."""
import datetime as dt
from io import BytesIO
import os
from urllib.parse import urlparse
from uuid import uuid4

from fastapi.testclient import TestClient
from pypdf import PdfReader
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import engine, get_db
from app.main import app
from app.models.clinic import AplicacionPreventiva, Caja, CategoriaProducto, Cita, HorarioVeterinario, Mascota, Producto, ProcesoAtencion, Proveedor, Servicio
from app.models.operations import Sucursal
from app.models.user import Cajero, Cliente, PermisoRol, TipoUsuario, Usuario, Veterinario
from app.security import create_access_token


@pytest.fixture
def native(monkeypatch):
    url = os.getenv("TEST_DATABASE_URL")
    if not url or os.getenv("DATABASE_URL") != url:
        pytest.skip("Requiere PostgreSQL local aislado de pruebas")
    parsed = urlparse(url)
    assert parsed.hostname in {"localhost", "127.0.0.1"} and "test" in parsed.path
    monkeypatch.setattr(get_settings(), "whatsapp_access_token", "")
    with engine.connect() as connection:
        transaction = connection.begin()
        db = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            marker = uuid4().hex
            branch = Sucursal(nombre="Independientes " + marker); db.add(branch); db.flush()
            db.info["sucursal_id"] = branch.id
            users = {role: Usuario(nombre=role, correo=f"{role}-{marker}@example.test", contrasena="hash", tipo=role, sucursal_id=branch.id) for role in ("cliente", "veterinario", "administrador", "cajero")}
            db.add_all(users.values()); db.flush()
            owner, vet, admin, cashier = [users[role] for role in ("cliente", "veterinario", "administrador", "cajero")]
            db.add_all([Cliente(usuario_id=owner.id), Veterinario(usuario_id=vet.id, colegiatura=marker), Cajero(usuario_id=cashier.id)])
            for role, modules in [(TipoUsuario.ADMINISTRADOR, ("citas", "ventas", "inventario")), (TipoUsuario.CLIENTE, ("mascotas",))]:
                for module in modules:
                    permission = db.scalar(select(PermisoRol).where(PermisoRol.rol == role, PermisoRol.modulo == module))
                    if permission is None:
                        permission = PermisoRol(rol=role, modulo=module); db.add(permission)
                    permission.puede_ver = True; permission.puede_editar = True; permission.puede_crear = True
            pet = Mascota(cliente_id=owner.id, nombre="Paciente nativo", especie="Perro")
            service = Servicio(codigo=marker, nombre="Consulta nativa", precio_referencial=0, duracion_estimada_min=30)
            category = CategoriaProducto(nombre="Categoría " + marker); supplier = Proveedor(razon_social="Proveedor " + marker)
            db.add_all([pet, service, category, supplier]); db.flush()
            start = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=8)).replace(hour=15, minute=0, second=0, microsecond=0)
            while start.weekday() >= 5:
                start += dt.timedelta(days=1)
            appointment = Cita(mascota_id=pet.id, servicio_id=service.id, veterinario_id=vet.id, sucursal_id=branch.id, estado="confirmada", fecha_hora_programada=start, fecha_hora_fin_programada=start + dt.timedelta(minutes=30))
            db.add(HorarioVeterinario(veterinario_id=vet.id, sucursal_id=branch.id, dia_semana=start.weekday(), hora_inicio=dt.time(8), hora_fin=dt.time(20), activo=True))
            process = ProcesoAtencion(mascota_id=pet.id, tipo="medica", estado="cerrada")
            product = Producto(categoria_id=category.id, proveedor_id=supplier.id, sucursal_id=branch.id, sku=marker, nombre="Producto nativo", precio_venta=99, stock_actual=10, costo_unitario=2)
            register = Caja(cajero_id=cashier.id, sucursal_id=branch.id, estado_caja="cerrada", fondo_inicial=100, efectivo_contado=99, diferencia=-1, fecha_cierre=start)
            db.add_all([appointment, process, product, register]); db.flush()
            db.add(AplicacionPreventiva(proceso_id=process.id, veterinario_id=vet.id, tipo="vacuna", producto="Vacuna nativa", lote="NATIVO", fecha_aplicacion=start.date()))
            db.commit()
            headers = {role: {"Authorization": "Bearer " + create_access_token(user.id)} for role, user in users.items()}
            app.dependency_overrides[get_db] = lambda: db
            with TestClient(app) as http:
                yield http, db, headers, appointment, pet, product, register, supplier, start
        finally:
            app.dependency_overrides.pop(get_db, None)
            db.close(); transaction.rollback()


def test_native_history_persists_real_change_and_actor(native):
    http, db, headers, appointment, *_, start = native
    response = http.patch(f"/admin/citas/{appointment.id}", headers=headers["administrador"], json={"fecha_hora_programada": (start + dt.timedelta(minutes=30)).isoformat(), "estado": "reprogramada", "nota_coordinacion": "Cambio nativo"})
    assert response.status_code == 200, response.text
    db.expire_all()
    result = http.get(f"/admin/operaciones/citas/{appointment.id}/historial", headers=headers["administrador"])
    assert result.status_code == 200 and result.json()["reprogramaciones"] == 1
    assert result.json()["eventos"][-1]["autor"] == "administrador"


def test_native_calendar_month_query(native):
    http, _db, headers, appointment, *_, start = native
    response = http.get("/admin/citas", headers=headers["administrador"], params={"fecha_inicial": start.date().replace(day=1).isoformat(), "fecha_final": start.date().isoformat()})
    assert response.status_code == 200, response.text
    assert [row["id"] for row in response.json()] == [appointment.id]


def test_native_client_downloads_specific_vaccine_pdf(native):
    http, _db, headers, _appointment, pet, *_ = native
    response = http.get(f"/portal/mascotas/{pet.id}/carnet", headers=headers["cliente"])
    assert response.status_code == 200, response.text
    assert "Vacuna nativa" in PdfReader(BytesIO(response.content)).pages[0].extract_text()


def test_native_closures_read_migrated_numeric_and_peru_dates(native):
    http, _db, headers, _appointment, _pet, _product, register, _supplier, start = native
    response = http.get("/admin/operaciones/cierres", headers=headers["administrador"], params={"desde": start.date().isoformat(), "hasta": start.date().isoformat()})
    assert response.status_code == 200, response.text
    data = response.json(); assert data["cantidad"] == 1 and data["por_dia"][0]["cantidad"] == 1
    assert float(data["totales"]["diferencia"]) == -1
    assert http.get(f"/admin/operaciones/cierres/{register.id}", headers=headers["administrador"]).status_code == 200


def test_native_purchase_updates_weighted_valuation(native):
    http, _db, headers, _appointment, _pet, product, _register, supplier, _start = native
    received = http.post("/admin/operaciones/compras", headers=headers["administrador"], json={"proveedor_id": supplier.id, "documento": "VAL-NATIVE", "detalles": [{"producto_id": product.id, "cantidad": 10, "costo_unitario": 4, "lote": "NATIVE-LOT"}]})
    assert received.status_code == 201, received.text
    response = http.get("/admin/operaciones/valorizacion", headers=headers["administrador"])
    assert response.status_code == 200 and float(response.json()["total"]) == 60
    assert float(response.json()["productos"][0]["costo"]) == 3
