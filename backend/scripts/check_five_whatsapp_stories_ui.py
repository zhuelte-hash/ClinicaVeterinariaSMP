"""HU-067/098/104/105/106: Edge escritorio/móvil con API controlada."""
from functools import partial
from http.server import ThreadingHTTPServer
import json
from threading import Thread
from urllib.parse import parse_qs, quote, urlsplit

from playwright.sync_api import expect, sync_playwright
from check_five_stories_ui import ASSETS, COMMUNICATION_STATUS, Handler, INSTITUTIONAL_POLICY, MODULES


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
                page.on("pageerror", lambda error: errors.append(str(error)))
                state = {"role": "administrador", "write": True, "bad_phone": False}
                communication = json.loads(json.dumps(COMMUNICATION_STATUS))
                order = {"id": 1, "codigo": "OC-ABCDEF123456", "cliente_id": 1, "cliente_nombre": "María Pérez", "creador_nombre": "Caja", "proceso_id": None, "fecha": "2026-11-17T15:00:00Z", "estado": "pendiente", "total": 40, "descuento": 0, "abonado": 0, "saldo": 40, "venta_id": None, "motivo_anulacion": None, "sin_comprobante": True, "detalles": [{"nombre": "Medicina", "cantidad": 2, "precio_unitario": 20, "subtotal": 40}], "abonos": []}

                def api(route):
                    request = route.request
                    if request.resource_type not in {"xhr", "fetch"}:
                        route.continue_(); return
                    parsed = urlsplit(request.url); path = parsed.path
                    body = request.post_data_json if request.post_data and "application/json" in request.headers.get("content-type", "") else None
                    calls.append((request.method, path, body, parsed.query))
                    status = 200
                    if path == "/auth/me":
                        data = {"id": 1 if state["role"] == "cliente" else 4, "nombre": "María Pérez", "correo": "test@example.com", "tipo": state["role"], "activo": True, "sucursal_id": 1}
                    elif path == "/auth/me/permisos":
                        data = [{"modulo": module, "puede_ver": True, **{f"puede_{action}": state["write"] for action in ("crear", "editar", "eliminar", "aprobar")}} for module in MODULES]
                    elif path == "/admin/configuracion":
                        data = {"nombre": "SMP", "correo": "clinic@example.com", "telefono": "965939522", "direccion": "Av. Prueba", "umbral_stock_bajo": 8, "recordatorios_citas": True, "alertas_stock": True}
                    elif path == "/admin/operaciones/configuracion":
                        data = INSTITUTIONAL_POLICY
                    elif path == "/admin/operaciones/comunicaciones/estado":
                        data = communication
                    elif path.startswith("/admin/operaciones/plantillas/"):
                        assert state["write"]
                        event = path.rsplit("/", 1)[1]
                        data = {"evento": event, **body}
                        communication["plantillas"] = [data if row["evento"] == event else row for row in communication["plantillas"]]
                    elif path == "/admin/operaciones/mensajes":
                        query = parse_qs(parsed.query)
                        data = [{"id": 20, "evento": "veterinario_cancelacion", "destinatario": "51988777666", "estado": "entregado", "intentos": 1, "proveedor_id": "wamid.vet.cancel", "error": None}]
                        data = [row for row in data if all(row[key] == query[key][0] for key in ("evento", "estado") if key in query)]
                    elif path == "/admin/operaciones/mensajes-entrantes":
                        data = [{"id": 1, "proveedor_id": "wamid.in.proof", "telefono": "51999888777", "resultado": "comprobante_vinculado:OC-ABCDEF123456"}]
                    elif path == "/operaciones/mis-pagos":
                        data = {"ordenes": [order], "ventas": [], "pedidos_web": []}
                    elif path == "/operaciones/ordenes/1":
                        data = order
                    elif path == "/operaciones/ordenes/1/preparar-whatsapp":
                        if state["bad_phone"]:
                            status, data = 409, {"detail": "Actualiza el teléfono de tu perfil antes de enviar el comprobante"}
                        else:
                            caption = f"{order['codigo']} MONTO={float(body['monto']):.2f} MEDIO={body['medio']}"
                            if body.get("codigo_operacion"): caption += " OPERACION=" + body["codigo_operacion"]
                            data = {"leyenda": caption, "whatsapp_url": "https://wa.me/51965939522?text=" + quote(caption), "telefono_remitente": "999888777", "instrucciones": "Adjunta JPG, PNG o PDF de hasta 5 MB. Caja debe revisar y validar el pago."}
                    else:
                        data = []
                    route.fulfill(status=status, content_type="application/json", body=json.dumps(data))

                page.route("**/*", api)
                page.goto(base + "/admin/configuracion")
                page.get_by_text("Preparar plantillas de cancelación y receta", exact=True).click()
                for event in ("cita_confirmada", "cita_reprogramada", "veterinario_reprogramacion", "veterinario_cancelacion"):
                    page.get_by_label("Plantilla a configurar", exact=True).select_option(event)
                    page.get_by_label("Nombre aprobado en Meta", exact=True).fill("approved_" + event)
                    page.get_by_role("button", name="Guardar plantilla " + event, exact=True).click()
                    expect(page.get_by_text("Plantilla guardada.", exact=False)).to_be_visible()
                    assert any(method == "PUT" and path.endswith("/plantillas/" + event) and body["nombre_proveedor"] == "approved_" + event for method, path, body, _ in calls)
                    count += 1
                expect(page.get_by_role("cell", name="comprobante_vinculado:OC-ABCDEF123456", exact=True)).to_be_visible()
                count += 1
                page.get_by_label("Evento de comunicación").select_option("veterinario_cancelacion")
                page.get_by_label("Estado del envío").select_option("entregado")
                page.get_by_role("button", name="Filtrar envíos", exact=True).click()
                expect(page.get_by_role("cell", name="wamid.vet.cancel", exact=True)).to_be_visible()
                assert any(path.endswith("/mensajes") and parse_qs(query) == {"evento": ["veterinario_cancelacion"], "estado": ["entregado"]} for _, path, _, query in calls)
                count += 1
                state["write"] = False
                page.reload()
                page.get_by_text("Preparar plantillas de cancelación y receta", exact=True).click()
                page.get_by_label("Plantilla a configurar", exact=True).select_option("veterinario_cancelacion")
                expect(page.get_by_label("Nombre aprobado en Meta", exact=True)).to_be_disabled()
                expect(page.get_by_role("button", name="Guardar plantilla veterinario_cancelacion", exact=True)).to_have_count(0)
                count += 1
                state.update(role="cliente", write=True)
                page.goto(base + "/mis-pagos")
                page.get_by_role("button", name="Ver detalle y pagos", exact=True).click()
                page.get_by_label("Código de operación para WhatsApp", exact=True).fill("OP-123")
                page.get_by_role("button", name="Preparar envío de comprobante", exact=True).click()
                link = page.get_by_role("link", name="Abrir WhatsApp para adjuntar comprobante", exact=True)
                caption = "OC-ABCDEF123456 MONTO=40.00 MEDIO=yape OPERACION=OP-123"
                expect(link).to_have_attribute("href", "https://wa.me/51965939522?text=" + quote(caption))
                expect(page.get_by_label("Leyenda para pegar en el archivo", exact=True)).to_have_value(caption)
                assert not order["abonos"] and order["estado"] == "pendiente"
                count += 1
                page.get_by_label("Monto para WhatsApp (S/)", exact=True).fill("41")
                expect(link).to_have_count(0)
                expect(page.get_by_role("button", name="Preparar envío de comprobante", exact=True)).to_be_disabled()
                count += 1
                page.get_by_label("Monto para WhatsApp (S/)", exact=True).fill("40")
                state["bad_phone"] = True
                page.get_by_role("button", name="Preparar envío de comprobante", exact=True).click()
                expect(page.get_by_text("Actualiza el teléfono de tu perfil antes de enviar el comprobante", exact=True)).to_be_visible()
                assert not errors, errors
                count += 1
                print(f"OK: 10 recorridos de las cinco historias WhatsApp, {viewport['width']}x{viewport['height']}; sin errores JavaScript")
                context.close()
            browser.close()
    finally:
        server.shutdown(); server.server_close()
    print(f"TOTAL: {count} comprobaciones de las cinco historias con API controlada")


if __name__ == "__main__":
    run()
