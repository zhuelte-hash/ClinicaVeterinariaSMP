"""E30: recorridos Edge escritorio/móvil de cinco historias, API controlada."""
from functools import partial
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlsplit
import json

from playwright.sync_api import expect, sync_playwright
from check_five_stories_ui import ASSETS, Handler, MODULES, PRODUCT, INSTITUTIONAL_POLICY


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
                context = browser.new_context(viewport=viewport, accept_downloads=True)
                context.add_init_script("localStorage.setItem('clinic_access_token', 'controlled-ui-session')")
                page = context.new_page(); errors, calls = [], []
                page.on("pageerror", lambda error: errors.append(str(error)))
                state = {"role": "administrador", "write": True, "valuation_error": False, "pdf_error": False, "history_error": False}
                totals = {"fondo_inicial": "100", "ingresos_efectivo": "40", "ingresos_digitales": "20", "efectivo_esperado": "140", "efectivo_contado": "138", "diferencia": "-2"}
                valuation = {"metodo": "Costo promedio ponderado móvil", "criterio": "Incluye inactivos. Costo cero para revisión.", "total": "62.25", "sin_costo": 1, "productos": [{"id": 1, "producto": "Medicina", "sku": "MED-1", "activo": False, "cantidad": "20", "unidad": "unidad", "costo": "3", "valor": "60.00", "costo_pendiente": False}, {"id": 2, "producto": "Alimento fraccionado", "sku": "KG-1", "activo": True, "cantidad": "1.125", "unidad": "kg", "costo": "2.0044", "valor": "2.25", "costo_pendiente": False}, {"id": 3, "producto": "Sin costo", "sku": "ZERO", "activo": True, "cantidad": "2", "unidad": "unidad", "costo": "0", "valor": "0.00", "costo_pendiente": True}]}

                def api(route):
                    request = route.request
                    if request.resource_type not in {"xhr", "fetch"}:
                        route.continue_(); return
                    parsed = urlsplit(request.url); path = parsed.path; query = parse_qs(parsed.query)
                    calls.append((request.method, path, query)); status = 200
                    if path == "/auth/me":
                        data = {"id": 4 if state["role"] == "administrador" else 1, "nombre": "Usuario prueba", "correo": "test@example.test", "tipo": state["role"], "activo": True, "sucursal_id": 1}
                    elif path == "/auth/me/permisos":
                        data = [{"modulo": module, "puede_ver": True, **{f"puede_{action}": state["write"] for action in ("crear", "editar", "eliminar", "aprobar")}} for module in MODULES]
                    elif path == "/admin/citas/veterinarios":
                        data = [{"id": 2, "nombre": "Dra. Ana"}, {"id": 3, "nombre": "Dr. Luis"}]
                    elif path == "/admin/citas/reporte":
                        data = {"fecha_inicial": "2026-11-01", "fecha_final": "2026-11-30", "total": 2, "urgentes": 0, "por_estado": {"confirmada": 1, "cancelada": 1}}
                    elif path == "/admin/citas":
                        start = query.get("fecha_inicial", ["2026-11-01"])[0]; month = start[:7]
                        data = [{"id": 1, "cliente_nombre": "María Pérez", "mascota_nombre": "Luna", "servicio_nombre": "Consulta", "veterinario_id": 2, "veterinario_nombre": "Dra. Ana", "estado": "confirmada", "fecha_hora_programada": f"{month}-15T15:00:00Z", "nota_coordinacion": "Consulta mensual"}, {"id": 2, "cliente_nombre": "José", "mascota_nombre": "Sol", "servicio_nombre": "Vacuna", "veterinario_id": 3, "veterinario_nombre": "Dr. Luis", "estado": "cancelada", "fecha_hora_programada": f"{month}-16T16:00:00Z"}]
                    elif path.endswith("/historial"):
                        if state["history_error"]:
                            status = 503; data = {"detail": "Historial temporalmente no disponible"}
                        else:
                            data = {"cantidad": 1, "reprogramaciones": 1, "cancelaciones": 0, "alcance": "No reconstruye cambios anteriores.", "eventos": [{"id": 1, "autor": "Administración", "accion": "reprogramada", "fecha": "2026-11-01T15:00:00Z", "motivo": "Cambio por trabajo", "anterior": {"fecha_hora_programada": "2026-11-14T15:00:00Z"}, "actual": {"fecha_hora_programada": "2026-11-15T15:00:00Z"}}]}
                    elif path == "/admin/operaciones/cierres":
                        data = {"cantidad": 1, "criterio": "Cierres por día de Perú", "totales": totals, "por_dia": [{"fecha": "2026-11-01", "cantidad": 1, **totals}], "cierres": [{"id": 7, "cajero_id": 5, "cajero": "Caja principal", "fecha_apertura": "2026-11-01T13:00:00Z", "fecha_cierre": "2026-11-02T04:59:00Z", **totals}]}
                    elif path == "/admin/operaciones/cierres/7":
                        data = {"id": 7, "cajero": "Caja principal", "movimientos": [{"referencia": "Abono #12", "medio": "efectivo", "monto": "40.00", "motivo": "Cobro de orden", "fecha": "2026-11-01T16:00:00Z"}]}
                    elif path == "/admin/operaciones/valorizacion":
                        data = valuation if not state["valuation_error"] else {"detail": "Valorización temporalmente no disponible"}
                        status = 503 if state["valuation_error"] else 200
                    elif path == "/admin/inventario":
                        data = [PRODUCT]
                    elif path == "/publico/institucional":
                        data = INSTITUTIONAL_POLICY
                    elif path == "/portal/mascotas":
                        data = [{"id": 1, "nombre": "Luna", "especie": "Perro", "raza": None}]
                    elif path == "/portal/mascotas/1/carnet":
                        if not state["pdf_error"]:
                            route.fulfill(content_type="application/pdf", body=b"%PDF-1.4 controlled download"); return
                        status = 503; data = {"detail": "Error PDF controlado"}
                    elif path in {"/admin/notificaciones", "/portal/notificaciones", "/admin/ajustes-inventario"}:
                        data = []
                    else:
                        raise AssertionError(f"Petición inesperada: {path}")
                    route.fulfill(status=status, content_type="application/json", body=json.dumps(data))

                page.route("**/*", api)
                page.goto(base + "/admin/citas", wait_until="domcontentloaded")
                page.get_by_label("Mes del calendario", exact=True).fill("2026-11")
                calendar = page.locator("app-appointment-calendar")
                expect(calendar.get_by_role("button", name="10:00 · Luna", exact=False)).to_be_visible()
                expect(calendar.get_by_role("button", name="11:00 · Sol", exact=False)).to_be_visible()
                count += 1
                page.get_by_role("combobox", name="Veterinario del calendario", exact=False).select_option(label="Dra. Ana")
                expect(calendar.get_by_role("button", name="11:00 · Sol", exact=False)).to_have_count(0)
                count += 1
                calendar.get_by_role("button", name="10:00 · Luna", exact=False).click()
                dialog = page.get_by_role("dialog")
                expect(dialog.get_by_text("Cambio por trabajo", exact=False)).to_be_visible()
                expect(dialog.get_by_text("1 reprogramaciones · 0 cancelaciones · 1 eventos", exact=True)).to_be_visible()
                dialog.get_by_role("button", name="Cerrar detalle", exact=True).click()
                count += 1
                page.get_by_role("button", name="Mes siguiente", exact=True).click()
                expect(page.get_by_label("Mes del calendario", exact=True)).to_have_value("2026-12")
                expect(calendar.get_by_role("button", name="10:00 · Luna", exact=False)).to_be_visible()
                assert any(query.get("fecha_final") == ["2026-12-31"] for _, path, query in calls if path == "/admin/citas")
                count += 1
                state["history_error"] = True
                page.get_by_role("combobox", name="Cita del listado", exact=False).select_option(index=1)
                expect(page.get_by_text("Historial temporalmente no disponible", exact=True)).to_be_visible()
                state["history_error"] = False
                page.get_by_role("button", name="Reintentar historial", exact=True).click()
                expect(page.get_by_text("Cambio por trabajo", exact=False)).to_be_visible()
                count += 1
                state["write"] = False
                page.reload(wait_until="domcontentloaded")
                expect(page.get_by_role("button", name="Gestionar", exact=True)).to_have_count(0)
                expect(page.get_by_role("heading", name="Calendario mensual administrativo", exact=True)).to_be_visible()
                count += 1
                page.goto(base + "/admin/cierres", wait_until="domcontentloaded")
                expect(page.get_by_role("heading", name="Consolidado diario", exact=True)).to_be_visible()
                expect(page.get_by_text("S/ -2.00", exact=True)).to_be_visible()
                page.get_by_role("button", name="Ver caja #7", exact=True).click()
                expect(page.get_by_role("cell", name="Abono #12", exact=True)).to_be_visible()
                count += 1
                page.get_by_label("ID del cajero (opcional)", exact=True).fill("5")
                page.get_by_role("button", name="Consultar cierres", exact=True).click()
                expect(page.get_by_role("button", name="Consultar cierres", exact=True)).to_be_enabled()
                assert any(query.get("cajero_id") == ["5"] for _, path, query in calls if path == "/admin/operaciones/cierres")
                count += 1
                page.goto(base + "/admin/inventario", wait_until="domcontentloaded")
                valuation_section = page.locator("app-inventory-valuation")
                expect(valuation_section.get_by_text("S/ 62.25", exact=True)).to_be_visible()
                expect(valuation_section.get_by_text("Inactivo", exact=True)).to_be_visible()
                page.get_by_label("Buscar en valorización", exact=True).fill("KG-1")
                expect(valuation_section.get_by_role("cell", name="1.125", exact=True)).to_be_visible()
                expect(valuation_section.get_by_text("Subtotal del filtro: S/ 2.25 · 1 productos", exact=True)).to_be_visible()
                count += 1
                page.get_by_label("Buscar en valorización", exact=True).fill("")
                page.get_by_label("Solo costo pendiente de revisión", exact=True).check()
                expect(valuation_section.get_by_role("cell", name="Sin costo · ZERO", exact=True)).to_be_visible()
                expect(valuation_section.get_by_role("cell", name="Medicina · MED-1", exact=True)).to_have_count(0)
                count += 1
                state["valuation_error"] = True
                page.get_by_role("button", name="Actualizar valorización", exact=True).click()
                expect(page.get_by_text("Valorización temporalmente no disponible", exact=True)).to_be_visible()
                state["valuation_error"] = False
                page.get_by_role("button", name="Actualizar valorización", exact=True).click()
                expect(valuation_section.get_by_text("S/ 62.25", exact=True)).to_be_visible()
                count += 1
                state["role"] = "cliente"
                page.goto(base + "/mis-mascotas", wait_until="domcontentloaded")
                with page.expect_download() as result:
                    page.get_by_role("button", name="Descargar carnet de Luna", exact=True).click()
                assert result.value.suggested_filename == "carnet-1.pdf"
                count += 1
                state["pdf_error"] = True
                page.get_by_role("button", name="Descargar carnet de Luna", exact=True).click()
                expect(page.get_by_text("No se pudo descargar el carnet. Intenta nuevamente.", exact=True)).to_be_visible()
                expect(page.get_by_role("button", name="Descargar carnet de Luna", exact=True)).to_be_enabled()
                count += 1
                assert not errors, errors
                assert all(method == "GET" for method, _, _ in calls), calls
                print(f"OK: 13 comprobaciones, {viewport['width']}x{viewport['height']}; sin errores JavaScript")
                context.close()
            browser.close()
    finally:
        server.shutdown(); server.server_close()
    print(f"TOTAL: {count} comprobaciones Edge con API controlada; backend real verificado en pytest por separado")


if __name__ == "__main__":
    run()
