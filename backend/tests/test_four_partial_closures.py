"""E18: aceptación HU-035/086/096/102 con HTTP, JWT y persistencia aislada."""
import datetime as dt
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from sqlalchemy import select

from test_admin_clinical_flows import clinic
from test_priority_stories import operations, create_order
from test_eleven_partial_stories import configure_phone, date_range, receive
from app.models.clinic import Cita, ConfiguracionClinica, EstadoCita, Notificacion, OrdenCobro
from app.models.operations import MovimientoCaja, SolicitudReprogramacion, Sucursal
from app.models.user import Cliente, PermisoRol, TipoUsuario, Usuario
from app.security import create_access_token
from app.services.access_service import aware


def proposal(start, **changes):
    return {"fecha_propuesta": (start + dt.timedelta(hours=4)).isoformat(), "motivo": "Cambio por trabajo & viaje", "canal": "whatsapp", **changes}


def test_whatsapp_request_is_persisted_encoded_and_does_not_move_original(operations):
    http, db, headers, start, _ = operations
    configure_phone(db)
    response = http.post("/portal/citas/1/reprogramacion", headers=headers[1], json=proposal(start))
    assert response.status_code == 201, response.text
    data = response.json()
    url = urlsplit(data["whatsapp_url"])
    assert url.netloc == "wa.me" and url.path == "/51965939522"
    message = parse_qs(url.query)["text"][0]
    assert f"Solicitud #{data['id']}" in message and "Cambio por trabajo & viaje" in message
    assert aware(db.get(Cita, 1).fecha_hora_programada) == start
    assert http.get("/portal/reprogramaciones", headers=headers[1]).json()[0]["id"] == data["id"]
    assert http.post("/portal/citas/1/reprogramacion", headers=headers[1], json=proposal(start)).status_code == 409


@pytest.mark.parametrize("kind", ["pasado", "fuera_horario", "sin_cambio"])
def test_invalid_reschedule_returns_conflict_without_creating_request(operations, kind):
    http, db, headers, start, _ = operations
    configure_phone(db)
    date = {"pasado": dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1), "fuera_horario": start.replace(hour=7), "sin_cambio": start}[kind]
    response = http.post("/portal/citas/1/reprogramacion", headers=headers[1], json=proposal(start, fecha_propuesta=date.isoformat()))
    assert response.status_code == 409, response.text
    assert db.scalars(select(SolicitudReprogramacion)).all() == []
    assert aware(db.get(Cita, 1).fecha_hora_programada) == start


@pytest.mark.parametrize("state", [EstadoCita.ATENDIDA, EstadoCita.CANCELADA, EstadoCita.NO_ASISTIO])
def test_finished_appointments_do_not_allow_client_reschedule(operations, state):
    http, db, headers, start, _ = operations
    db.get(Cita, 1).estado = state; db.commit()
    assert http.post("/portal/citas/1/reprogramacion", headers=headers[1], json=proposal(start, canal="web")).status_code == 409


def test_reschedule_checks_ownership_phone_and_configured_lead_time(operations, monkeypatch):
    http, db, headers, start, _ = operations
    from app.routers import clinical_operations
    db.add(Usuario(id=8, nombre="Otro cliente", correo="other-client@example.com", contrasena="hash", tipo=TipoUsuario.CLIENTE)); db.flush()
    db.add(Cliente(usuario_id=8)); db.commit()
    other = {"Authorization": f"Bearer {create_access_token(8)}"}
    assert http.post("/portal/citas/1/reprogramacion", headers=other, json=proposal(start)).status_code == 409
    assert http.post("/portal/citas/1/reprogramacion", headers=headers[1], json=proposal(start)).status_code == 409
    configure_phone(db)
    policy = http.get("/publico/institucional").json(); policy["horas_reprogramacion"] = 6
    assert http.put("/admin/operaciones/configuracion", headers=headers[4], json=policy).status_code == 200
    monkeypatch.setattr(clinical_operations, "now", lambda: start - dt.timedelta(hours=5))
    assert http.post("/portal/citas/1/reprogramacion", headers=headers[1], json=proposal(start)).status_code == 409
    assert db.scalars(select(SolicitudReprogramacion)).all() == []


def test_reschedule_resolution_cannot_move_an_already_attended_appointment(operations):
    http, db, headers, start, _ = operations
    item = http.post("/portal/citas/1/reprogramacion", headers=headers[1], json=proposal(start, canal="web")).json()
    db.get(Cita, 1).estado = EstadoCita.ATENDIDA; db.commit()
    response = http.post(f"/admin/operaciones/reprogramaciones/{item['id']}/resolver", headers=headers[4], json={"aceptar": True, "motivo": "Aceptar solicitud"})
    assert response.status_code == 409
    assert db.get(SolicitudReprogramacion, item["id"]).estado == "pendiente"


def test_monthly_rankings_use_peru_boundaries_and_distinguish_requested_attended(operations):
    http, db, headers, start, product = operations
    for quantity, instant in [(2, dt.datetime(2026, 11, 1, 4, 59, tzinfo=dt.timezone.utc)), (3, dt.datetime(2026, 11, 1, 5, 0, tzinfo=dt.timezone.utc))]:
        response = http.post("/api/ventas", headers=headers[5], json={"cliente_id": 1, "medio_pago": "efectivo", "items": [{"producto_id": product, "cantidad": quantity}]})
        assert response.status_code == 201, response.text
        sale = db.get(OrdenCobro, response.json()["orden_id"])
        sale.comprobante_venta.fecha_emision = instant
    db.get(Cita, 1).fecha_hora_programada = dt.datetime(2026, 10, 10, 15, tzinfo=dt.timezone.utc)
    db.get(Cita, 1).estado = EstadoCita.ATENDIDA
    db.get(Cita, 2).fecha_hora_programada = dt.datetime(2026, 10, 12, 15, tzinfo=dt.timezone.utc)
    db.get(Cita, 2).estado = EstadoCita.CANCELADA
    db.commit()
    data = http.get("/admin/operaciones/dashboard", headers=headers[4], params={"desde": "2026-10-01", "hasta": "2026-10-31"}).json()
    assert data["productos_mas_vendidos"] == [{"id": product, "nombre": "Medicina", "cantidad": 2}]
    assert data["servicios_mas_solicitados"] == [{"id": 1, "nombre": "Consulta", "cantidad": 2}]
    assert data["servicios_mas_atendidos"] == [{"id": 1, "nombre": "Consulta", "cantidad": 1}]
    november = http.get("/admin/operaciones/dashboard", headers=headers[4], params={"desde": "2026-11-01", "hasta": "2026-11-30"}).json()
    assert november["productos_mas_vendidos"][0]["cantidad"] == 3


def test_financial_period_counts_installments_when_received_without_double_counting_sale(operations):
    http, db, headers, _, product = operations
    order, _ = create_order(http, headers[5], product)
    for amount, instant in [(10, dt.datetime(2026, 2, 25, 15, tzinfo=dt.timezone.utc)), (30, dt.datetime(2026, 3, 14, 15, tzinfo=dt.timezone.utc))]:
        result = http.post(f"/operaciones/ordenes/{order['id']}/abonos", headers=headers[5], json={"monto": amount, "medio": "efectivo", "canal": "caja", "clave_idempotencia": str(uuid4())})
        assert result.status_code == 201, result.text
        movement = db.scalar(select(MovimientoCaja).order_by(MovimientoCaja.id.desc()))
        movement.fecha = instant; db.commit()
    sale = db.scalar(select(OrdenCobro).where(OrdenCobro.preorden_id == order["id"]))
    sale.comprobante_venta.fecha_emision = dt.datetime(2026, 3, 14, 15, tzinfo=dt.timezone.utc); db.commit()
    result = http.post("/api/ventas", headers=headers[5], json={"cliente_id": 1, "medio_pago": "efectivo", "items": [{"producto_id": product, "cantidad": 1}]})
    db.get(OrdenCobro, result.json()["orden_id"]).comprobante_venta.fecha_emision = dt.datetime(2026, 3, 20, 15, tzinfo=dt.timezone.utc); db.commit()
    for amount, date in [(7, "2026-03-15"), (100, "2026-02-15")]:
        assert http.post("/admin/operaciones/egresos", headers=headers[4], json={"categoria": "Servicios", "concepto": "Electricidad", "monto": amount, "fecha": date}).status_code == 201
    params = {"desde": "2026-03-01", "hasta": "2026-03-31"}
    data = http.get("/admin/operaciones/dashboard", headers=headers[4], params=params).json()
    assert Decimal(data["ventas"]) == 60
    assert {key: Decimal(data["finanzas"][key]) for key in ("cobros", "egresos", "resultado")} == {"cobros": 50, "egresos": 7, "resultado": 43}
    expenses = http.get("/admin/operaciones/egresos", headers=headers[4], params=params).json()
    assert len(expenses) == 1 and Decimal(expenses[0]["monto"]) == 7


def test_finance_expenses_require_create_permission_and_are_isolated_by_branch(operations):
    http, db, headers, start, _ = operations
    payload = {"categoria": "Servicios", "concepto": "Electricidad", "monto": 7, "fecha": dt.date.today().isoformat()}
    assert http.post("/admin/operaciones/egresos", headers=headers[4], json={**payload, "monto": -1}).status_code == 422
    assert http.post("/admin/operaciones/egresos", headers=headers[4], json=payload).status_code == 201
    db.add(Sucursal(id=2, nombre="Otra sede")); db.commit()
    assert http.get("/admin/operaciones/egresos", headers={**headers[4], "X-Sucursal-ID": "2"}, params=date_range(start)).json() == []
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="ventas", puede_ver=True, puede_crear=False)); db.commit()
    assert http.get("/admin/operaciones/egresos", headers=headers[4], params=date_range(start)).status_code == 200
    assert http.post("/admin/operaciones/egresos", headers=headers[4], json=payload).status_code == 403
    assert http.get("/admin/operaciones/egresos", headers=headers[1], params=date_range(start)).status_code == 403


def test_stock_alert_reaches_each_admin_and_reading_does_not_generate_repeats(operations):
    http, db, headers, _, product = operations
    db.add(Usuario(id=8, nombre="Segundo admin", correo="second-admin@example.com", contrasena="hash", tipo=TipoUsuario.ADMINISTRADOR)); db.commit()
    second = {"Authorization": f"Bearer {create_access_token(8)}"}
    assert http.patch(f"/admin/productos/{product}", headers=headers[4], json={"stock_minimo": 9}).status_code == 200
    payload = {"cliente_id": 1, "medio_pago": "efectivo", "items": [{"producto_id": product, "cantidad": 1}]}
    assert http.post("/api/ventas", headers=headers[5], json=payload).status_code == 201
    notices = http.get("/admin/notificaciones", headers=headers[4]).json()
    alert = next(row for row in notices if row["tipo"] == "stock_bajo")
    assert alert["usuario_id"] == 4 and not alert["leida"]
    assert len(http.get("/admin/notificaciones", headers=second).json()) == 1
    assert http.patch(f"/portal/notificaciones/{alert['id']}/leer", headers=headers[4]).status_code == 200
    assert http.get("/admin/notificaciones", headers=headers[4], params={"no_leidas": True}).json() == []
    assert http.post("/api/ventas", headers=headers[5], json=payload).status_code == 201
    assert len(db.scalars(select(Notificacion).where(Notificacion.tipo == "stock_bajo")).all()) == 2
    assert receive(http, headers[4], product, cantidad=4).status_code == 201
    payload["items"][0]["cantidad"] = 3
    assert http.post("/api/ventas", headers=headers[5], json=payload).status_code == 201
    assert len(db.scalars(select(Notificacion).where(Notificacion.tipo == "stock_bajo")).all()) == 4
