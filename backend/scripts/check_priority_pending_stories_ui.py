"""HU-032/097/066/100/101: preparación y seguimiento con API controlada en Edge."""
from functools import partial
from http.server import ThreadingHTTPServer
import json
from threading import Thread
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import expect, sync_playwright
from check_five_stories_ui import ASSETS, COMMUNICATION_STATUS, Handler, INSTITUTIONAL_POLICY, MODULES

FLOWS = [
    ("recordatorio_24h", "Recordatorio 24 h (HU-032 / HU-097)"),
    ("recordatorio_2h", "Recordatorio 2 h (HU-097)"),
    ("orden_creada", "Orden creada (HU-066)"),
    ("orden_recordatorio", "Orden sin comprobante (HU-100)"),
    ("pago_validado", "Pago y boleta PDF (HU-101)"),
]


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
                page = context.new_page(); errors, calls = [], []
                page.on("pageerror", lambda error: errors.append(str(error)))
                state = {"write": True, "role": "administrador"}
                expired = {"id": 99, "codigo": "OC-VENCIDA", "cliente_id": 1, "cliente_nombre": "María Pérez", "creador_nombre": "Caja", "proceso_id": None, "fecha": "2026-11-15T15:00:00Z", "estado": "vencida", "total": 40, "descuento": 0, "abonado": 0, "saldo": 40, "venta_id": None, "motivo_anulacion": None, "sin_comprobante": True, "detalles": [{"nombre": "Medicina", "cantidad": 2, "precio_unitario": 20, "subtotal": 40}], "abonos": []}
                communication = json.loads(json.dumps(COMMUNICATION_STATUS))
                outgoing = [{"id": i + 1, "evento": event, "destinatario": "51999888777", "estado": "cancelado" if event == "orden_recordatorio" else "error", "intentos": 1, "proveedor_id": None, "error": "La orden ya tiene comprobante; no reenviar." if event == "orden_recordatorio" else "Proveedor no disponible."} for i, (event, _) in enumerate(FLOWS)]

                def api(route):
                    request = route.request
                    if request.resource_type not in {"xhr", "fetch"}:
                        route.continue_(); return
                    parsed = urlsplit(request.url); path = parsed.path
                    body = request.post_data_json if request.post_data and "application/json" in request.headers.get("content-type", "") else None
                    calls.append((request.method, path, body, parsed.query))
                    if path == "/auth/me":
                        data = {"id": 1 if state["role"] == "cliente" else 4, "nombre": "Administración", "correo": "test@example.com", "tipo": state["role"], "activo": True, "sucursal_id": 1}
                    elif path == "/auth/me/permisos":
                        data = [{"modulo": module, "puede_ver": True, **{f"puede_{action}": state["write"] for action in ("crear", "editar", "eliminar", "aprobar")}} for module in MODULES]
                    elif path == "/admin/configuracion":
                        data = {"nombre": "SMP", "correo": "clinic@example.com", "telefono": "965939522", "direccion": "Av. Prueba", "umbral_stock_bajo": 8, "recordatorios_citas": True, "alertas_stock": True}
                    elif path == "/admin/operaciones/configuracion":
                        data = INSTITUTIONAL_POLICY
                    elif path == "/admin/operaciones/comunicaciones/estado":
                        data = communication
                    elif path.endswith("/vista-previa"):
                        event = path.split("/")[-2]
                        template = next(row for row in communication["plantillas"] if row["evento"] == event)
                        data = {"contenido": template["contenido"].format_map(body["valores"]), "parametros": [{"posicion": i + 1, "variable": variable, "valor": body["valores"][variable]} for i, variable in enumerate(template["variables"])], "encabezado": "documento PDF" if event == "pago_validado" else "sin documento", "alcance": "Vista previa guardada sin envío real."}
                    elif path.startswith("/admin/operaciones/plantillas/"):
                        assert state["write"]
                        event = path.rsplit("/", 1)[1]; data = {"evento": event, **body}
                        communication["plantillas"] = [data if row["evento"] == event else row for row in communication["plantillas"]]
                    elif path == "/admin/operaciones/mensajes":
                        query = parse_qs(parsed.query)
                        data = [row for row in outgoing if all(row[key] == query[key][0] for key in ("evento", "estado") if key in query)]
                    elif path == "/operaciones/mis-pagos":
                        data = {"ordenes": [expired], "ventas": [], "pedidos_web": []}
                    elif path == "/operaciones/ordenes/99":
                        data = expired
                    else:
                        data = []
                    route.fulfill(status=200, content_type="application/json", body=json.dumps(data))

                page.route("**/*", api)
                page.goto(base + "/admin/configuracion", wait_until="domcontentloaded")
                page.get_by_text("Preparar plantillas de cancelación y receta", exact=True).click()
                for event, label in FLOWS:
                    page.get_by_role("button", name=label, exact=True).click()
                    expect(page.get_by_role("combobox", name="Evento de comunicación", exact=True)).to_have_value(event)
                    expect(page.get_by_label("Plantilla a configurar", exact=True)).to_have_value(event)
                    expected_id = next(row["id"] for row in outgoing if row["evento"] == event)
                    expect(page.get_by_role("cell", name=f"{event} #{expected_id}", exact=True)).to_be_visible()
                    assert any(path.endswith("/mensajes") and parse_qs(query).get("evento") == [event] for _, path, _, query in calls)
                    count += 1
                    page.get_by_label("Nombre aprobado en Meta", exact=True).fill("approved_" + event)
                    page.get_by_role("button", name="Guardar plantilla " + event, exact=True).click()
                    expect(page.get_by_text("Plantilla guardada.", exact=False)).to_be_visible()
                    page.get_by_role("button", name="Ver vista previa guardada", exact=True).click()
                    expect(page.get_by_text("Vista previa guardada sin envío real.", exact=True)).to_be_visible()
                    if event == "pago_validado": expect(page.get_by_text("Encabezado: documento PDF", exact=True)).to_be_visible()
                    else: expect(page.get_by_text("Encabezado: sin documento", exact=True)).to_be_visible()
                    assert any(method == "PUT" and path.endswith("/plantillas/" + event) and body["nombre_proveedor"] == "approved_" + event for method, path, body, _ in calls)
                    count += 1
                page.get_by_role("button", name="Orden sin comprobante (HU-100)", exact=True).click()
                expect(page.get_by_text("La orden ya tiene comprobante; no reenviar.", exact=True)).to_be_visible()
                expect(page.get_by_role("button", name="Reintentar #4", exact=True)).to_have_count(0)
                count += 1
                page.get_by_role("combobox", name="Estado del envío", exact=True).select_option("error")
                page.get_by_role("button", name="Filtrar envíos", exact=True).click()
                expect(page.get_by_role("cell", name="Sin envíos para este filtro.", exact=True)).to_be_visible()
                count += 1
                state["write"] = False
                page.reload(wait_until="domcontentloaded")
                page.get_by_text("Preparar plantillas de cancelación y receta", exact=True).click()
                page.get_by_role("button", name="Pago y boleta PDF (HU-101)", exact=True).click()
                expect(page.get_by_label("Nombre aprobado en Meta", exact=True)).to_be_disabled()
                expect(page.get_by_role("button", name="Guardar plantilla pago_validado", exact=True)).to_have_count(0)
                page.get_by_role("button", name="Ver vista previa guardada", exact=True).click()
                expect(page.get_by_text("Encabezado: documento PDF", exact=True)).to_be_visible()
                count += 1
                state.update(role="cliente", write=True)
                page.goto(base + "/mis-pagos", wait_until="domcontentloaded")
                page.get_by_role("button", name="Ver detalle y pagos", exact=True).click()
                expect(page.get_by_text("Orden vencida por permanecer 48 horas sin pago ni comprobante.", exact=False)).to_be_visible()
                expect(page.get_by_role("button", name="Registrar pago", exact=True)).to_have_count(0)
                expect(page.get_by_role("button", name="Preparar envío de comprobante", exact=True)).to_have_count(0)
                assert not errors, errors
                count += 1
                print(f"OK: 14 comprobaciones de recordatorios/cobros, {viewport['width']}x{viewport['height']}; sin errores JavaScript")
                context.close()
            browser.close()
    finally:
        server.shutdown(); server.server_close()
    print(f"TOTAL: {count} comprobaciones con API controlada; no acredita recepción externa")


if __name__ == "__main__":
    run()
