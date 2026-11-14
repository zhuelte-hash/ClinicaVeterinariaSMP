"""E19: HU-006/009/010/081/084 en Edge con API controlada.

Requiere `npm run build`, Playwright para Python y Microsoft Edge.
Ejecutar desde la raíz: python backend/scripts/check_delivery_stories_ui.py
"""
import json
from functools import partial
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

from check_five_stories_ui import ASSETS, Handler, MODULES


def run():
    assert (ASSETS / "index.html").is_file(), "Primero ejecuta npm run build"
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(ASSETS)))
    Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    count = 0
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            for viewport in ({"width": 1440, "height": 1000}, {"width": 390, "height": 844}):
                context = browser.new_context(viewport=viewport)
                context.add_init_script("localStorage.setItem('clinic_access_token', 'controlled-ui-session')")
                page = context.new_page()
                errors, calls = [], []
                state = {"role": "cliente", "can_write": True, "attempts": 0, "name": "María Pérez", "phone": "999888777", "address": "Av. Inicial"}
                staff = {"id": 2, "nombre": "Dra. Ana", "correo": "vet@example.com", "tipo": "veterinario", "activo": True, "telefono": "999888777", "colegiatura": "VET-2", "especialidad": "General", "sucursal_id": 1}
                services = [{"id": 1, "codigo": "consulta", "nombre": "Consulta", "descripcion": "Consulta general", "precio_referencial": "50.00", "duracion_estimada_min": 30, "activo": True, "tipo": "medica", "tipo_medico": "consulta_general"}]
                order = {"id": 1, "codigo": "OC-UI", "cliente_id": 1, "cliente_nombre": "María Pérez", "creador_nombre": "Caja", "proceso_id": None, "fecha": "2026-11-14T12:00:00Z", "estado": "pendiente", "total": 40, "descuento": 0, "abonado": 0, "saldo": 40, "venta_id": None, "motivo_anulacion": None, "sin_comprobante": False, "detalles": [{"servicio_id": 1, "cantidad": 1, "nombre": "Consulta", "precio_unitario": 40, "subtotal": 40}], "abonos": [{"id": 1, "monto": 10, "medio": "yape", "canal": "web", "estado": "enviado", "fecha": "2026-11-14T12:00:00Z", "codigo_operacion": "OP-1", "tiene_comprobante": True, "motivo": None, "registrado_por_nombre": "María Pérez", "validado_por_nombre": None}]}
                page.on("pageerror", lambda error: errors.append(str(error)))

                def user():
                    return {"id": 1 if state["role"] == "cliente" else 4, "nombre": state["name"] if state["role"] == "cliente" else "Administración", "correo": "user@example.com", "tipo": state["role"], "activo": True, "telefono": state["phone"], "direccion": state["address"], "sucursal_id": 1}

                def permissions():
                    return [{"modulo": module, "puede_ver": True, "puede_crear": state["can_write"], "puede_editar": state["can_write"], "puede_eliminar": state["can_write"], "puede_aprobar": state["can_write"]} for module in MODULES]

                def credit(amount):
                    order["abonado"] += amount
                    order["saldo"] = order["total"] - order["abonado"]
                    order["estado"] = "parcial" if order["saldo"] else "pagada"
                    if not order["saldo"]:
                        order["venta_id"] = 1

                def api(route):
                    request = route.request
                    if request.resource_type not in {"xhr", "fetch"}:
                        route.continue_(); return
                    path = urlsplit(request.url).path
                    calls.append((request.method, path, request.post_data))
                    status = 200
                    if path == "/auth/me":
                        if request.method == "PATCH":
                            payload = request.post_data_json
                            state.update(name=" ".join(payload["nombre"].split()), phone=payload["telefono"].strip(), address=payload["direccion"].strip())
                        data = user()
                    elif path == "/auth/me/permisos":
                        data = permissions()
                    elif path == "/auth/login":
                        state["attempts"] += 1
                        status = 423 if state["attempts"] >= 5 else 401
                        data = {"detail": "Cuenta bloqueada temporalmente por intentos fallidos." if status == 423 else "Correo o contraseña incorrectos"}
                    elif path == "/usuarios":
                        data = [{**user(), "tipo": "administrador"}, staff]
                    elif path == "/usuarios/2/estado":
                        staff["activo"] = request.post_data_json["activo"]
                        data = staff
                    elif path == "/admin/permisos":
                        data = [{**permission, "rol": role} for role in ("administrador", "cajero", "cliente", "veterinario") for permission in permissions()]
                    elif path == "/admin/operaciones/servicios":
                        if request.method == "POST":
                            services.append({"id": len(services) + 1, **request.post_data_json})
                            data, status = services[-1], 201
                        else:
                            data = services
                    elif path.startswith("/admin/operaciones/servicios/"):
                        id = int(path.rsplit("/", 1)[1])
                        data = {"id": id, **request.post_data_json}
                        services[:] = [data if item["id"] == id else item for item in services]
                    elif path in {"/admin/notificaciones", "/portal/notificaciones", "/operaciones/descuentos", "/operaciones/ventas"}:
                        data = []
                    elif path == "/operaciones/catalogo":
                        data = {"clientes": [{"id": 1, "nombre": "María Pérez"}], "productos": [], "servicios": [{"id": 1, "nombre": "Consulta", "precio": 40}]}
                    elif path == "/operaciones/ordenes":
                        data = [order]
                    elif path == "/operaciones/ordenes/1":
                        data = order
                    elif path == "/operaciones/pagos/1/validar":
                        order["abonos"][0]["estado"] = "validado"
                        credit(10)
                        data = order
                    elif path == "/operaciones/ordenes/1/abonos":
                        payload = request.post_data_json
                        amount = float(payload["monto"])
                        credit(amount)
                        order["abonos"].append({**order["abonos"][0], **payload, "id": len(order["abonos"]) + 1, "estado": "validado", "tiene_comprobante": False})
                        data, status = order, 201
                    else:
                        raise AssertionError(f"Petición inesperada: {request.method} {path}")
                    route.fulfill(status=status, content_type="application/json", body=json.dumps(data))

                page.route("**/*", api)
                page.goto(base + "/mi-perfil")
                expect(page.get_by_role("heading", name="Mi perfil", exact=True)).to_be_visible()
                page.locator("input[name=nombre]").fill(" María   Actualizada ")
                page.locator("input[name=telefono]").fill("999111222")
                page.locator("input[name=direccion]").fill("Av. Actualizada 123")
                page.get_by_role("button", name="Guardar perfil", exact=True).click()
                expect(page.get_by_text("Perfil actualizado.", exact=True)).to_be_visible()
                expect(page.locator("input[name=nombre]")).to_have_value("María Actualizada")
                page.reload()
                expect(page.locator("input[name=direccion]")).to_have_value("Av. Actualizada 123")
                count += 1

                page.goto(base + "/login")
                page.locator("#email").fill("owner@example.com")
                page.locator("#password").fill("Incorrecta123")
                for attempt in range(5):
                    page.get_by_role("button", name="Iniciar sesión", exact=True).click()
                    expect(page.get_by_role("alert")).to_contain_text("incorrectos" if attempt < 4 else "bloqueada temporalmente")
                assert state["attempts"] == 5
                count += 1

                state["role"] = "administrador"
                page.goto(base + "/admin/usuarios")
                row = page.get_by_role("row").filter(has=page.get_by_role("cell", name="vet@example.com", exact=True))
                row.get_by_role("button", name="Desactivar", exact=True).click()
                expect(row.get_by_text("Inactivo", exact=True)).to_be_visible()
                expect(page.get_by_text("Cuenta desactivada.", exact=False)).to_be_visible()
                page.reload()
                expect(row.get_by_role("button", name="Activar", exact=True)).to_be_visible()
                row.get_by_role("button", name="Activar", exact=True).click()
                expect(row.get_by_text("Activo", exact=True)).to_be_visible()
                count += 1

                page.goto(base + "/admin/ordenes")
                page.get_by_role("button", name="Ver detalle y pagos", exact=True).click()
                page.get_by_role("button", name="Validar pago", exact=True).click()
                expect(page.locator("input[name=monto]")).to_have_value("30.00")
                page.locator("select[name=canal]").select_option("caja")
                page.locator("select[name=medio]").select_option("efectivo")
                page.locator("input[name=monto]").fill("10")
                page.get_by_role("button", name="Registrar pago", exact=True).click()
                expect(page.get_by_text("Abono registrado. Saldo pendiente: S/ 20.00.", exact=True)).to_be_visible()
                expect(page.locator("input[name=monto]")).to_have_value("20.00")
                page.get_by_role("button", name="Registrar pago", exact=True).click()
                expect(page.get_by_role("button", name="Descargar boleta de venta", exact=True)).to_be_visible()
                expect(page.get_by_role("button", name="Registrar pago", exact=True)).to_have_count(0)
                count += 1

                page.goto(base + "/admin/servicios")
                page.get_by_role("button", name="Nuevo servicio", exact=True).click()
                page.locator("input[name=nombre]").fill("Consulta nueva")
                page.locator("input[name=codigo]").fill("consulta-nueva")
                page.locator("textarea[name=descripcion]").fill("Evaluación clínica")
                page.locator("input[name=precio]").fill("75.50")
                page.locator("input[name=duracion]").fill("45")
                page.get_by_role("button", name="Guardar servicio", exact=True).click()
                row = page.get_by_role("row").filter(has=page.get_by_text("Consulta nueva", exact=True))
                expect(row.get_by_role("cell", name="S/ 75.50", exact=True)).to_be_visible()
                row.get_by_role("button", name="Editar", exact=True).click()
                page.locator("input[name=precio]").fill("80")
                page.get_by_role("button", name="Guardar servicio", exact=True).click()
                expect(row.get_by_role("cell", name="S/ 80.00", exact=True)).to_be_visible()
                row.get_by_role("button", name="Desactivar", exact=True).click()
                expect(row).to_have_count(0)
                page.get_by_text("Mostrar inactivos", exact=True).click()
                expect(row.get_by_role("cell", name="Inactivo", exact=True)).to_be_visible()
                count += 1

                state["can_write"] = False
                page.reload()
                expect(page.get_by_role("button", name="Nuevo servicio", exact=True)).to_have_count(0)
                expect(page.get_by_role("button", name="Editar", exact=True)).to_have_count(0)
                expect(page.get_by_text("Solo consulta", exact=True)).to_be_visible()
                assert any(method == "PATCH" and path == "/auth/me" for method, path, body in calls)
                assert any(method == "POST" and path == "/operaciones/ordenes/1/abonos" for method, path, body in calls)
                assert not errors, errors
                count += 1
                print(f"OK: 6 recorridos E19, viewport {viewport['width']}x{viewport['height']}; sin errores JavaScript")
                context.close()
            browser.close()
    finally:
        server.shutdown(); server.server_close()
    print(f"TOTAL: {count} comprobaciones de interfaz aprobadas con API controlada")


if __name__ == "__main__":
    run()
