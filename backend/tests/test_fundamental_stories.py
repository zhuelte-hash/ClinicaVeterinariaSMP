"""HU-095/116/039/093/114: aceptación HTTP/JWT con datos aislados."""
import datetime as dt
import hashlib
import hmac
import json
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import select

from test_admin_clinical_flows import clinic
from test_priority_stories import operations
from test_eleven_partial_stories import configure_phone
from app.config import get_settings
from app.models.clinic import Cita, EstadoCita, Mascota, Notificacion, Producto
from app.models.operations import LoteInventario, MensajeEntrante, MensajeSalida, MovimientoInventario, Sucursal
from app.models.user import PermisoRol, TipoUsuario, Usuario
from app.services import automation_service, backup_service, appointment_service
from app.routers import clinical_operations, messaging
from app.services.access_service import aware, now
from app.services.policy_service import ZONE


def signed_message(http, monkeypatch, message_id, body="ASISTIRE 1", phone="51999888777"):
    monkeypatch.setattr(get_settings(), "whatsapp_app_secret", "fundamental-test-secret")
    payload = {"entry": [{"changes": [{"value": {"messages": [{"id": message_id, "from": phone, "type": "text", "text": {"body": body}}]}}]}]}
    content = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(b"fundamental-test-secret", content, hashlib.sha256).hexdigest()
    return http.post("/whatsapp/webhook", content=content, headers={"X-Hub-Signature-256": signature, "Content-Type": "application/json"})


def backup_zip(http, headers):
    response = http.get("/admin/operaciones/respaldo", headers=headers[4])
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    return response.content


def mutate_backup(content, transform):
    with ZipFile(BytesIO(content)) as source:
        entries = {name: source.read(name) for name in source.namelist()}
    manifest = json.loads(entries["manifest.json"])
    transform(entries, manifest)
    entries["manifest.json"] = json.dumps(manifest).encode()
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as target:
        for name, value in entries.items():
            target.writestr(name, value)
    return output.getvalue()


def test_backup_download_and_restore_check_preserve_rows_binaries_and_files(operations, tmp_path, monkeypatch):
    http, db, headers, *_ = operations
    # El directorio aislado evita leer archivos particulares del desarrollador.
    backend = tmp_path / "backend"
    (backend / "clinical_private").mkdir(parents=True)
    (backend / "uploads").mkdir()
    (backend / "clinical_private" / "laboratorio.pdf").write_bytes(b"%PDF-1.4 prueba")
    (backend / "uploads" / "foto.png").write_bytes(b"imagen de prueba")
    monkeypatch.setattr(backup_service, "__file__", str(backend / "app" / "services" / "backup_service.py"))
    db.add(MensajeSalida(clave="backup-binary", canal="whatsapp", evento="receta", destinatario="51999888777", contenido="Receta", documento=b"%PDF documento privado")); db.commit()
    content = backup_zip(http, headers)
    with ZipFile(BytesIO(content)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["tablas"]["usuarios"]["registros"] == 5
        assert archive.read("archivos/clinical_private/laboratorio.pdf") == b"%PDF-1.4 prueba"
        rows = json.loads(archive.read("datos/mensajes_salida.json"))
        assert any(row["documento"] and row["documento"]["tipo"] == "binario" for row in rows)
    response = http.post("/admin/operaciones/respaldo/verificar", headers=headers[4], files={"archivo": ("backup.zip", content, "application/zip")})
    assert response.status_code == 200, response.text
    assert response.json()["valido"] and response.json()["archivos"] == 2
    assert response.json()["registros_restaurados"] > 5
    assert db.get(Mascota, 1).nombre == "Luna"


@pytest.mark.parametrize("damage", ["checksum", "relation", "extra", "path", "schema"])
def test_restore_rejects_damaged_or_inconsistent_backup(operations, damage):
    http, _db, headers, *_ = operations
    content = backup_zip(http, headers)
    def transform(entries, manifest):
        if damage in {"checksum", "relation"}:
            path = "datos/mascotas.json"
            rows = json.loads(entries[path]); rows[0]["cliente_id"] = 999999
            entries[path] = json.dumps(rows).encode()
            if damage == "relation":
                manifest["tablas"]["mascotas"]["sha256"] = hashlib.sha256(entries[path]).hexdigest()
        elif damage == "extra":
            entries["unexpected.txt"] = b"extra"
        elif damage == "path":
            entries["archivos/uploads/../escape"] = b"bad"
            manifest["archivos"]["archivos/uploads/../escape"] = hashlib.sha256(b"bad").hexdigest()
        else:
            manifest["version"] = 999
    response = http.post("/admin/operaciones/respaldo/verificar", headers=headers[4], files={"archivo": ("bad.zip", mutate_backup(content, transform), "application/zip")})
    assert response.status_code == 422, response.text


def test_backup_requires_admin_edit_permission_and_rejects_non_zip(operations):
    http, db, headers, *_ = operations
    for role in (1, 2, 5):
        assert http.get("/admin/operaciones/respaldo", headers=headers[role]).status_code == 403
    assert http.get("/admin/operaciones/respaldo").status_code == 401
    assert http.post("/admin/operaciones/respaldo/verificar", headers=headers[4], files={"archivo": ("bad.zip", b"not a zip")}).status_code == 422
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="usuarios", puede_ver=True, puede_editar=False)); db.commit()
    assert http.get("/admin/operaciones/respaldo", headers=headers[4]).status_code == 403


def test_booking_policy_uses_citas_permission_and_preserves_other_settings(operations):
    http, db, headers, *_ = operations
    before = http.get("/publico/institucional").json()
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="usuarios", puede_ver=False, puede_editar=False)); db.commit()
    response = http.put("/admin/operaciones/politicas-citas", headers=headers[4], json={"horas_cancelacion": 12, "horas_reprogramacion": 24})
    assert response.status_code == 200, response.text
    after = http.get("/publico/institucional").json()
    assert after["horas_cancelacion"] == 12 and after["horas_reprogramacion"] == 24
    assert all(after[key] == value for key, value in before.items() if key not in {"horas_cancelacion", "horas_reprogramacion"})
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="citas", puede_ver=True, puede_editar=False)); db.commit()
    assert http.put("/admin/operaciones/politicas-citas", headers=headers[4], json={"horas_cancelacion": 0, "horas_reprogramacion": 4}).status_code == 403


@pytest.mark.parametrize("payload", [
    {"horas_cancelacion": -1, "horas_reprogramacion": 4},
    {"horas_cancelacion": 0, "horas_reprogramacion": 3},
    {"horas_cancelacion": 169, "horas_reprogramacion": 4},
    {"horas_cancelacion": 0, "horas_reprogramacion": 4, "galeria": []},
])
def test_booking_policy_rejects_invalid_or_unrelated_fields(operations, payload):
    http, _db, headers, *_ = operations
    assert http.put("/admin/operaciones/politicas-citas", headers=headers[4], json=payload).status_code == 422


@pytest.mark.parametrize("hours,expected", [(11.99, 409), (12, 200)])
def test_configured_cancellation_threshold_is_enforced_at_boundary(operations, monkeypatch, hours, expected):
    http, _db, headers, start, _ = operations
    assert http.put("/admin/operaciones/politicas-citas", headers=headers[4], json={"horas_cancelacion": 12, "horas_reprogramacion": 24}).status_code == 200
    class Clock(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return start - dt.timedelta(hours=hours)
    monkeypatch.setattr(appointment_service.datetime, "datetime", Clock)
    response = http.patch("/portal/citas/1/cancelar", headers=headers[1], json={"motivo": "Cambio de planes"})
    assert response.status_code == expected, response.text


def test_configured_reprogramming_applies_to_request_and_proposal_acceptance(operations, monkeypatch):
    http, db, headers, start, _ = operations
    assert http.put("/admin/operaciones/politicas-citas", headers=headers[4], json={"horas_cancelacion": 4, "horas_reprogramacion": 24}).status_code == 200
    monkeypatch.setattr(clinical_operations, "now", lambda: start - dt.timedelta(hours=23))
    response = http.post("/portal/citas/1/reprogramacion", headers=headers[1], json={"fecha_propuesta": (start + dt.timedelta(hours=4)).isoformat(), "motivo": "Cambio de planes", "canal": "web"})
    assert response.status_code == 409
    appointment = db.get(Cita, 1)
    appointment.estado = EstadoCita.REQUIERE_OTRO_HORARIO; appointment.fecha_hora_propuesta = start + dt.timedelta(hours=4); db.commit()
    class Clock(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return start - dt.timedelta(hours=23)
    monkeypatch.setattr(appointment_service.datetime, "datetime", Clock)
    assert http.patch("/portal/citas/1/aceptar-horario", headers=headers[1]).status_code == 409


def test_legacy_policy_cannot_bypass_four_hour_minimum_when_accepting_proposal(operations, monkeypatch):
    http, db, headers, start, _ = operations
    policy = http.get("/publico/institucional").json(); policy["horas_reprogramacion"] = 0
    assert http.put("/admin/operaciones/configuracion", headers=headers[4], json=policy).status_code == 200
    appointment = db.get(Cita, 1)
    appointment.estado = EstadoCita.REQUIERE_OTRO_HORARIO; appointment.fecha_hora_propuesta = start + dt.timedelta(hours=4); db.commit()
    class Clock(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return start - dt.timedelta(hours=3)
    monkeypatch.setattr(appointment_service.datetime, "datetime", Clock)
    response = http.patch("/portal/citas/1/aceptar-horario", headers=headers[1])
    assert response.status_code == 409
    assert aware(db.get(Cita, 1).fecha_hora_programada) == start


def prepare_attendance(db):
    configure_phone(db)
    appointment = db.get(Cita, 1)
    tomorrow = now().astimezone(ZONE).date() + dt.timedelta(days=1)
    appointment.fecha_hora_programada = dt.datetime.combine(tomorrow, dt.time(10), ZONE)
    appointment.fecha_hora_fin_programada = appointment.fecha_hora_programada + dt.timedelta(minutes=30)
    appointment.estado = EstadoCita.CONFIRMADA
    db.commit()


def test_attendance_link_does_not_confirm_and_signed_message_is_visible_to_roles(operations, monkeypatch):
    http, db, headers, *_ = operations
    prepare_attendance(db)
    response = http.get("/portal/citas/1/asistencia-whatsapp", headers=headers[1])
    assert response.status_code == 200, response.text
    from app.services.attendance_service import attendance_code
    command = f"ASISTIRE 1 {attendance_code(db, db.get(Cita, 1))}"
    assert parse_qs(urlsplit(response.json()["whatsapp_url"]).query)["text"] == [command]
    assert db.get(Cita, 1).asistencia_confirmada_en is None
    assert signed_message(http, monkeypatch, "attendance-1").status_code == 200
    instant = aware(db.get(Cita, 1).asistencia_confirmada_en)
    assert instant is not None
    for path, role in [("/portal/citas", 1), ("/portal/veterinario/solicitudes", 2), ("/admin/citas", 4)]:
        response = http.get(path, headers=headers[role]); assert response.status_code == 200
        assert next(row for row in response.json() if row["id"] == 1)["asistencia_confirmada_en"]
    # Repetición del proveedor y mensaje diferente con el mismo comando no duplican avisos.
    for message_id in ("attendance-1", "attendance-2"):
        assert signed_message(http, monkeypatch, message_id).status_code == 200
    assert aware(db.get(Cita, 1).asistencia_confirmada_en) == instant
    assert len(db.scalars(select(Notificacion).where(Notificacion.tipo == "asistencia_confirmada")).all()) == 1


@pytest.mark.parametrize("kind", ["wrong_phone", "past", "distant", "cancelled", "arrived"])
def test_attendance_rejects_wrong_sender_and_ineligible_appointments(operations, monkeypatch, kind):
    http, db, headers, *_ = operations
    prepare_attendance(db)
    appointment = db.get(Cita, 1)
    if kind == "past":
        appointment.fecha_hora_programada = now() - dt.timedelta(minutes=1)
    elif kind == "distant":
        appointment.fecha_hora_programada = now() + dt.timedelta(days=5)
    elif kind == "cancelled":
        appointment.estado = EstadoCita.CANCELADA
    elif kind == "arrived":
        appointment.fecha_hora_llegada = now()
    db.commit()
    assert signed_message(http, monkeypatch, "rejected-1", phone="51900000000" if kind == "wrong_phone" else "51999888777").status_code == 200
    assert db.get(Cita, 1).asistencia_confirmada_en is None
    incoming = db.scalar(select(MensajeEntrante).where(MensajeEntrante.proveedor_id == "rejected-1"))
    assert incoming.resultado != "asistencia_confirmada"
    if kind != "wrong_phone":
        assert http.get("/portal/citas/1/asistencia-whatsapp", headers=headers[1]).status_code == 409


def test_rescheduling_clears_previous_attendance_confirmation(operations):
    http, db, headers, start, _ = operations
    appointment = db.get(Cita, 1); appointment.estado = EstadoCita.CONFIRMADA; appointment.asistencia_confirmada_en = now(); db.commit()
    response = http.patch("/admin/citas/1", headers=headers[4], json={"fecha_hora_programada": (start + dt.timedelta(hours=4)).isoformat()})
    assert response.status_code == 200, response.text
    assert response.json()["asistencia_confirmada_en"] is None


def test_expiry_alerts_are_automatic_scoped_and_not_repeated(operations, monkeypatch):
    http, db, headers, _, product = operations
    monkeypatch.setattr(get_settings(), "whatsapp_access_token", "")
    today = now().astimezone(ZONE).date()
    db.add(Sucursal(id=2, nombre="Otra sede")); db.flush()
    db.add_all([
        Usuario(id=7, nombre="Admin otra sede", correo="branch2@test.com", tipo=TipoUsuario.ADMINISTRADOR, contrasena="hash", sucursal_id=2),
        Usuario(id=8, nombre="Admin inactivo", correo="inactive@test.com", tipo=TipoUsuario.ADMINISTRADOR, contrasena="hash", activo=False),
    ])
    db.add_all([LoteInventario(producto_id=product, codigo=code, cantidad=qty, costo_unitario=2, vencimiento=date) for code, qty, date in [
        ("SOON", 2, today + dt.timedelta(days=1)), ("EXPIRED", 1, today - dt.timedelta(days=1)),
        ("FAR", 1, today + dt.timedelta(days=90)), ("EMPTY", 0, today), ("NO-DATE", 1, None),
    ]]); db.commit()
    filtered = http.get("/admin/operaciones/lotes", headers=headers[4], params={"por_vencer": True}).json()
    assert {row["codigo"] for row in filtered} == {"SOON", "EXPIRED"}
    assert {row["estado_vencimiento"] for row in filtered} == {"por_vencer", "vencido"}
    for _ in range(2):
        automation_service.run_automations(db)
    alerts = db.scalars(select(Notificacion).where(Notificacion.tipo == "vencimiento")).all()
    assert len(alerts) == 2 and {row.usuario_id for row in alerts} == {4}
    assert http.get("/admin/operaciones/lotes", headers={**headers[4], "X-Sucursal-ID": "2"}, params={"por_vencer": True}).json() == []
    alerts[0].leida = True; db.commit()
    automation_service.run_automations(db)
    assert len(db.scalars(select(Notificacion).where(Notificacion.tipo == "vencimiento")).all()) == 2
    monkeypatch.setattr(automation_service, "now", lambda: dt.datetime.combine(today + dt.timedelta(days=3), dt.time(10), ZONE))
    automation_service.run_automations(db)
    assert len(db.scalars(select(Notificacion).where(Notificacion.tipo == "vencimiento")).all()) == 3


def test_expiry_policy_preserves_other_fields_and_requires_inventory_edit(operations):
    http, db, headers, *_ = operations
    before = http.get("/publico/institucional").json()
    response = http.put("/admin/operaciones/politicas-vencimiento", headers=headers[4], json={"dias_alerta_vencimiento": 15})
    assert response.status_code == 200
    assert response.json() == {**before, "dias_alerta_vencimiento": 15}
    assert http.put("/admin/operaciones/politicas-vencimiento", headers=headers[4], json={"dias_alerta_vencimiento": 0}).status_code == 422
    db.add(PermisoRol(rol=TipoUsuario.ADMINISTRADOR, modulo="inventario", puede_ver=True, puede_editar=False)); db.commit()
    assert http.put("/admin/operaciones/politicas-vencimiento", headers=headers[4], json={"dias_alerta_vencimiento": 20}).status_code == 403


def test_kardex_unifies_purchase_sale_adjustment_return_with_balances_and_authors(operations):
    http, db, headers, _, product = operations
    response = http.post("/admin/operaciones/compras", headers=headers[4], json={"proveedor_id": 1, "documento": "KARDEX-1", "detalles": [{"producto_id": product, "cantidad": 2, "costo_unitario": 5, "lote": "K-1"}]})
    assert response.status_code == 201, response.text
    sale = http.post("/api/ventas", headers=headers[5], json={"cliente_id": 1, "medio_pago": "efectivo", "items": [{"producto_id": product, "cantidad": 3}]})
    assert sale.status_code == 201, sale.text
    response = http.patch(f"/admin/inventario/{product}", headers=headers[4], json={"stock_actual": 8, "stock_anterior": 9, "motivo": "Merma verificada"})
    assert response.status_code == 200, response.text
    response = http.post(f"/operaciones/ventas/{sale.json()['orden_id']}/anular", headers=headers[5], json={"motivo": "Venta equivocada"})
    assert response.status_code == 200, response.text
    rows = http.get(f"/admin/operaciones/kardex/{product}", headers=headers[4]).json()
    assert {row["tipo"] for row in rows} == {"ingreso", "compra", "venta", "ajuste", "devolucion"}
    chronological = list(reversed(rows))
    assert float(chronological[0]["saldo_anterior"]) == 0
    for previous, current in zip(chronological, chronological[1:]):
        assert previous["saldo_nuevo"] == current["saldo_anterior"]
    assert float(rows[0]["saldo_nuevo"]) == float(db.get(Producto, product).stock_actual) == 11
    assert next(row for row in rows if row["tipo"] == "compra")["usuario_nombre"] == "Administración"
    assert next(row for row in rows if row["tipo"] == "venta")["usuario_nombre"] == "Caja"
    assert http.get(f"/admin/operaciones/kardex/{product}", headers=headers[1]).status_code == 403
    db.add(Sucursal(id=2, nombre="Otra sede")); db.commit()
    assert http.get(f"/admin/operaciones/kardex/{product}", headers={**headers[4], "X-Sucursal-ID": "2"}).status_code in {403, 404}
    assert http.post(f"/admin/operaciones/kardex/{product}", headers=headers[4], json={}).status_code == 405


def test_kardex_filters_use_inclusive_peru_dates_and_preserve_original_balance(operations):
    http, db, headers, _, product = operations
    movement = db.scalar(select(MovimientoInventario).where(MovimientoInventario.producto_id == product))
    movement.fecha = dt.datetime(2026, 11, 17, 4, 59, tzinfo=dt.timezone.utc); db.commit()  # 16/11 en Perú.
    url = f"/admin/operaciones/kardex/{product}"
    assert len(http.get(url, headers=headers[4], params={"desde": "2026-11-16", "hasta": "2026-11-16", "tipo": "ingreso"}).json()) == 1
    assert http.get(url, headers=headers[4], params={"desde": "2026-11-17"}).json() == []
    assert http.get(url, headers=headers[4], params={"desde": "2026-11-17", "hasta": "2026-11-16"}).status_code == 422
