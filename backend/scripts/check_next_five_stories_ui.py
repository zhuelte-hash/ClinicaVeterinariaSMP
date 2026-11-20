"""E20: HU-002/004/036/061/120 en escritorio y móvil con API controlada.

Requiere npm run build, Playwright para Python y Microsoft Edge.
Ejecutar desde la raíz: backend/.venv/Scripts/python.exe backend/scripts/check_next_five_stories_ui.py
Las entregas SMTP se comprueban por separado en test_next_five_stories.py.
"""
import datetime as dt
import json
import re
from copy import deepcopy
from functools import partial
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlencode, urlsplit

from playwright.sync_api import expect, sync_playwright

from check_five_stories_ui import ASSETS, Handler, MODULES, PRODUCT, UNITS


def run():
    assert (ASSETS / "index.html").is_file(), "Primero ejecuta npm run build"
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(ASSETS)))
    Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    total = 0
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            for viewport in ({"width": 1440, "height": 1000}, {"width": 390, "height": 844}):
                context = browser.new_context(viewport=viewport)
                page = context.new_page()
                errors, calls = [], []
                page.on("pageerror", lambda error: errors.append(str(error)))
                date = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=8)).replace(hour=15, minute=0, second=0, microsecond=0).isoformat()
                pet = {"id": 1, "nombre": "Luna", "especie": "Perro", "raza": "Mestiza", "sexo": "hembra", "cliente_id": 1,
                       "peso_actual": "4.50", "fecha_nacimiento": "2024-01-01", "caracteristicas": "", "alergias": "", "condiciones_especiales": "", "foto_url": None}
                service = {"id": 1, "codigo": "consulta", "nombre": "Consulta", "descripcion": "Evaluación clínica", "precio_referencial": "50.00", "duracion_estimada_min": 30}
                appointment = {"id": 1, "estado": "confirmada", "mascota": pet, "servicio": service, "fecha_hora_programada": date,
                               "fecha_creacion": date, "fecha_actualizacion": date, "motivo": "Control", "es_urgente": False, "veterinario_id": 2,
                               "fecha_hora_llegada": None, "cancelacion_automatica_at": None, "fecha_hora_propuesta": None,
                               "telefono_contacto": "999888777", "preferencia_contacto": "whatsapp", "nota_coordinacion": None,
                               "cliente_id": 1, "cliente_nombre": "María Pérez", "cliente_correo": "owner@example.com"}
                record = {"id": 1, "cita_id": 1, "mascota_id": 1, "tipo": "medica", "fecha_inicio": date, "fecha_fin": None,
                          "estado": "en_atencion", "fecha_cierre": None, "observaciones": "Examen público", "motivo_consulta": "Control",
                          "anamnesis": "Revisión", "diagnostico": "Control", "tratamiento": "Reposo", "peso": "4.50", "temperatura": None,
                          "historial_alergias": "", "vacunas": "", "desparasitaciones": "", "medicamentos": "", "procedimientos": "",
                          "examenes_resultados": "", "proxima_fecha_control": None, "veterinario_id": 2, "veterinario_nombre": "Dra. Ana",
                          "servicio_nombre": "Consulta", "archivos": [], "diagnosticos": [], "ordenes_examen": [], "receta": None,
                          "procedimientos_realizados": [], "aplicaciones_preventivas": []}
                state = {"role": "cliente", "smtp": False, "write": True, "notes": {1: "Nota interna inicial"}, "records": {1: record},
                         "receipts": [], "lots": [], "product": {**PRODUCT, "stock_actual": 10}}

                def user():
                    role = state["role"]
                    return {"id": {"cliente": 1, "veterinario": 2, "administrador": 4}[role], "nombre": "María Pérez" if role == "cliente" else "Dra. Ana" if role == "veterinario" else "Administración",
                            "correo": "owner@example.com", "tipo": role, "activo": True, "telefono": "999888777", "direccion": "", "sucursal_id": 1}

                def api(route):
                    request = route.request
                    if request.resource_type not in {"xhr", "fetch"}:
                        route.continue_(); return
                    path = urlsplit(request.url).path
                    body = request.post_data_json if request.post_data else None
                    calls.append((request.method, path, body))
                    status = 200
                    if path == "/auth/me":
                        data = user()
                    elif path == "/auth/me/permisos":
                        data = [{"modulo": module, "puede_ver": True, **{f"puede_{action}": state["write"] for action in ("crear", "editar", "eliminar", "aprobar")}} for module in MODULES]
                    elif path == "/auth/register":
                        status = 201 if state["smtp"] else 503
                        data = {"access_token": "", "verification_required": True, "user": user()} if state["smtp"] else {"detail": "El envío de correo de la clínica aún no está configurado."}
                    elif path == "/auth/verificar-correo":
                        status = 200 if body["codigo"] == "123456" else 400
                        data = {"access_token": "controlled-ui-session", "user": user()} if status == 200 else {"detail": "El código o enlace es inválido"}
                    elif path == "/auth/recuperar-clave":
                        data, status = {"mensaje": "Si existe una cuenta activa, recibirás un enlace de recuperación."}, 202
                    elif path == "/auth/restablecer-clave":
                        if body["token"].startswith("expired"):
                            data, status = {"detail": "El código o enlace es inválido, fue usado o ha caducado"}, 400
                        else:
                            assert parse_qs(urlsplit(request.url).query)["correo"] == ["owner+reset@example.com"]
                            data, status = None, 204
                    elif path == "/portal/servicios":
                        data = [service]
                    elif path == "/portal/mascotas":
                        data = [pet]
                    elif path == "/portal/citas":
                        data = [appointment]
                    elif path == "/portal/disponibilidad":
                        data = []
                    elif path == "/portal/reprogramaciones":
                        data = []
                    elif path == "/publico/institucional":
                        data = {"horarios": [{"dia": i, "cerrado": i == 6, "inicio": "08:00", "fin": "20:00", "descanso_inicio": "12:00", "descanso_fin": "13:00"} for i in range(7)], "excepciones": [], "galeria": [], "horas_cancelacion": 4, "horas_reprogramacion": 4, "dias_alerta_vencimiento": 30, "dias_recordatorio_vacuna": 3}
                    elif path == "/portal/citas/1/cancelar":
                        assert body == {"motivo": "Viaje familiar"}
                        appointment.update(estado="cancelada", nota_coordinacion=body["motivo"])
                        data = appointment
                    elif path == "/portal/veterinario/solicitudes":
                        data = [{**appointment, "estado": "confirmada"}]
                    elif re.fullmatch(r"/portal/veterinario/mascotas/1/historial", path):
                        data = list(state["records"].values())
                    elif path == "/portal/veterinario/mascotas/1":
                        data = {**pet, "cliente_nombre": "María Pérez", "cliente_correo": "owner@example.com", "telefono_contacto": "999888777", "direccion": "", "total_atenciones": len(state["records"]), "ultima_atencion": date}
                    elif path == "/portal/veterinario/solicitudes/1/atencion/iniciar":
                        data, status = state["records"][1], 201
                    elif re.fullmatch(r"/portal/veterinario/atenciones/\d+/ordenes-examen", path):
                        data = []
                    elif match := re.fullmatch(r"/portal/veterinario/atenciones/(\d+)/notas-privadas", path):
                        id = int(match[1])
                        if request.method == "PUT":
                            assert set(body) == {"notas"}
                            state["notes"][id] = body["notas"]
                        data = {"notas": state["notes"].get(id, "")}
                    elif path == "/portal/veterinario/clientes":
                        data = [{"id": 1, "nombre": "María Pérez", "correo": "owner@example.com", "telefono": "999888777", "direccion": "", "mascotas": 1}]
                    elif path == "/portal/veterinario/clientes/1/mascotas":
                        data = [pet]
                    elif path == "/portal/veterinario/servicios":
                        data = [service]
                    elif path == "/portal/veterinario/atenciones/iniciar":
                        data, status = {**appointment, "id": 3}, 201
                    elif path == "/portal/veterinario/solicitudes/3/atencion":
                        assert "notas_privadas" not in body and "Nota de atención presencial" not in json.dumps(body)
                        state["records"][3] = {**state["records"].get(3, deepcopy(record)), **body, "id": 3, "cita_id": 3}
                        data = state["records"][3]
                    elif path in {"/admin/notificaciones", "/portal/notificaciones", "/catalogo/productos"}:
                        data = []
                    elif path == "/admin/inventario":
                        data = [state["product"]]
                    elif path == "/admin/operaciones/proveedores":
                        data = [{"id": 1, "razon_social": "Proveedor"}]
                    elif path == "/admin/operaciones/unidades":
                        data = UNITS
                    elif path == "/admin/operaciones/lotes":
                        data = state["lots"]
                    elif path == "/admin/operaciones/compras":
                        if request.method == "GET":
                            data = state["receipts"]
                        else:
                            document = " ".join(body["documento"].split()).upper()
                            if any(row["documento"] == document for row in state["receipts"]):
                                data, status = {"detail": "Este documento del proveedor ya fue recibido"}, 409
                            else:
                                data = {**body, "id": 1, "documento": document, "proveedor_nombre": "Proveedor", "usuario_nombre": "Administración", "fecha": date,
                                        "total": sum(float(line["cantidad"]) * float(line["costo_unitario"]) for line in body["detalles"])}
                                state["receipts"].append(data)
                                for line in body["detalles"]:
                                    state["product"]["stock_actual"] += float(line["cantidad"])
                                    state["lots"].append({"id": len(state["lots"]) + 1, "producto_id": line["producto_id"], "producto_nombre": "Medicina", "codigo": line["lote"], "cantidad": line["cantidad"], "costo_unitario": line["costo_unitario"], "vencimiento": line["vencimiento"]})
                                status = 201
                    else:
                        errors.append(f"Petición inesperada: {request.method} {path}")
                        data, status = {"detail": "Petición inesperada"}, 500
                    route.fulfill(status=status, content_type="application/json", body="" if status == 204 else json.dumps(data))

                page.route("**/*", api)
                page.route("**/publico/sucursales", lambda route: route.fulfill(content_type="application/json", body="[]"))
                page.goto(base + "/registro")
                for name, value in {"nombre": "María Pérez", "correo": "owner@example.com", "telefono": "999888777", "password": "Inicial123", "confirmPassword": "Inicial123"}.items():
                    page.locator(f"input[formcontrolname={name}]").fill(value)
                page.get_by_role("button", name="Crear cuenta", exact=True).click()
                expect(page.get_by_role("alert")).to_contain_text("aún no está configurado")
                total += 1

                state["smtp"] = True
                page.get_by_role("button", name="Crear cuenta", exact=True).click()
                expect(page.get_by_role("heading", name="Verificar correo", exact=True)).to_be_visible()
                expect(page.get_by_role("button", name=re.compile("Reenviar en"))).to_be_disabled()
                page.locator("input[name=codigo]").fill("000000")
                page.get_by_role("button", name="Verificar y entrar", exact=True).click()
                expect(page.get_by_role("alert")).to_contain_text("inválido")
                page.locator("input[name=codigo]").fill("123456")
                page.get_by_role("button", name="Verificar y entrar", exact=True).click()
                expect(page).to_have_url(base + "/inicio")
                assert page.evaluate("localStorage.getItem('clinic_access_token')") == "controlled-ui-session"
                total += 1

                page.goto(base + "/recuperar-clave")
                page.locator("input[name=correo]").fill("owner+reset@example.com")
                page.get_by_role("button", name="Enviar enlace", exact=True).click()
                expect(page.get_by_role("status")).to_contain_text("recibirás el enlace")
                page.goto(base + "/recuperar-clave?" + urlencode({"token": "a" * 48, "correo": "owner+reset@example.com"}))
                page.locator("input[name=clave]").fill("Actualizada123")
                page.locator("input[name=confirmacion]").fill("Diferente123")
                expect(page.get_by_role("button", name="Guardar contraseña", exact=True)).to_be_disabled()
                page.locator("input[name=confirmacion]").fill("Actualizada123")
                page.get_by_role("button", name="Guardar contraseña", exact=True).click()
                expect(page.get_by_role("status")).to_contain_text("Contraseña actualizada")
                expect(page.get_by_role("link", name="Iniciar sesión", exact=True).last).to_be_visible()
                expect(page.locator("input[name=clave]")).to_have_count(0)
                total += 1

                page.goto(base + "/recuperar-clave?" + urlencode({"token": "expired" + "a" * 40, "correo": "owner+reset@example.com"}))
                page.locator("input[name=clave]").fill("Actualizada123")
                page.locator("input[name=confirmacion]").fill("Actualizada123")
                page.get_by_role("button", name="Guardar contraseña", exact=True).click()
                expect(page.get_by_role("alert")).to_contain_text("ha caducado")
                total += 1

                page.evaluate("localStorage.setItem('clinic_access_token', 'controlled-ui-session')")
                page.goto(base + "/reservar-cita")
                page.get_by_role("button", name=re.compile("^Cancelar")).click()
                dialog = page.get_by_role("dialog")
                expect(dialog.get_by_role("heading", name="Cancelar cita de Luna")).to_be_visible()
                expect(dialog.get_by_role("button", name="Confirmar cancelación")).to_be_disabled()
                dialog.locator("textarea").fill("Viaje familiar")
                dialog.get_by_role("button", name="Confirmar cancelación").click()
                expect(dialog).to_have_count(0)
                expect(page.get_by_text("Cancelada", exact=True)).to_be_visible()
                assert any(method == "PATCH" and path == "/portal/citas/1/cancelar" and body == {"motivo": "Viaje familiar"} for method, path, body in calls)
                total += 1

                state["role"] = "veterinario"
                page.goto(base + "/veterinario/atencion/1")
                notes = page.locator("#private-notes-1")
                expect(notes).to_have_value("Nota interna inicial")
                notes.fill("Nota clínica reservada actualizada")
                page.get_by_role("button", name="Guardar notas privadas", exact=True).click()
                expect(page.get_by_text("Notas privadas guardadas.", exact=True)).to_be_visible()
                page.reload()
                expect(notes).to_have_value("Nota clínica reservada actualizada")
                state["write"] = False
                page.reload()
                expect(notes).to_have_attribute("readonly", "")
                expect(page.get_by_role("button", name="Guardar notas privadas", exact=True)).to_have_count(0)
                state["write"] = True
                page.goto(base + "/veterinario/mascota/1?tab=historia")
                page.get_by_role("button", name="Ver detalle", exact=True).click()
                expect(page.locator("#private-notes-1")).to_have_value("Nota clínica reservada actualizada")
                total += 1

                page.goto(base + "/veterinario/nueva-atencion?cliente=1&mascota=1")
                page.get_by_role("button").filter(has_text="Evaluación clínica").click()
                page.get_by_role("button", name="Abrir ficha clínica", exact=True).click()
                page.get_by_role("textbox", name="Anamnesis y antecedentes", exact=True).fill("Control presencial")
                page.locator("#new-private-notes").fill("Nota de atención presencial")
                page.locator("form").last.locator("button").last.click()
                expect(page.get_by_text("Paso 1 de 4", exact=True)).to_be_visible()
                assert state["notes"][3] == "Nota de atención presencial" and state["records"][3]["estado"] == "cerrada"
                total += 1

                state["role"] = "administrador"
                page.goto(base + "/admin/recepciones")

                def fill_receipt():
                    page.locator("select[name=supplier]").select_option(label="Proveedor")
                    page.locator("input[name=document]").fill("fact-ui")
                    article = page.get_by_role("group", name="Artículo 1", exact=True)
                    article.locator("select").nth(0).select_option(label="Medicina (unidad)")
                    article.locator("input[type=number]").nth(0).fill("2")
                    article.locator("input[type=number]").nth(1).fill("3")
                    article.get_by_label("Lote", exact=True).fill("LOTE-UI")
                    article.locator("input[type=date]").fill((dt.date.today() + dt.timedelta(days=90)).isoformat())

                fill_receipt()
                page.get_by_role("button", name="Registrar recepción", exact=True).click()
                expect(page.get_by_text("Recepción registrada. Existencias, lotes y egreso actualizados.", exact=True)).to_be_visible()
                page.reload()
                row = page.get_by_role("row").filter(has=page.get_by_role("cell", name="FACT-UI", exact=True))
                expect(row.get_by_role("cell", name="S/ 6.00", exact=True)).to_be_visible()
                row.get_by_role("button", name="Ver detalle", exact=True).click()
                expect(page.get_by_text("Medicina · 2 unidad", exact=False)).to_be_visible()
                assert state["product"]["stock_actual"] == 12
                total += 1

                fill_receipt()
                page.get_by_role("button", name="Registrar recepción", exact=True).click()
                expect(page.get_by_role("alert")).to_contain_text("ya fue recibido")
                assert len(state["receipts"]) == 1 and state["product"]["stock_actual"] == 12
                state["write"] = False
                page.reload()
                expect(page.get_by_text("Acceso de solo consulta.", exact=False)).to_be_visible()
                expect(page.get_by_role("button", name="Registrar recepción", exact=True)).to_have_count(0)
                assert not errors, errors
                total += 1
                print(f"OK: 9 recorridos E20, {viewport['width']}x{viewport['height']}; sin errores JavaScript")
                context.close()
            browser.close()
    finally:
        server.shutdown(); server.server_close()
    print(f"TOTAL: {total} comprobaciones E20 con API controlada")


if __name__ == "__main__":
    run()
