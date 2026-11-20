"""HU-018/056/103/104/105 en Edge; API y fotografías sintéticas controladas."""
from functools import partial
from http.server import ThreadingHTTPServer
from io import BytesIO
import json
from threading import Thread
from urllib.parse import urlsplit

from PIL import Image
from playwright.sync_api import expect, sync_playwright
from check_five_stories_ui import ASSETS, COMMUNICATION_STATUS, Handler, INSTITUTIONAL_POLICY, MODULES


def run():
    assert (ASSETS / "index.html").is_file(), "Primero ejecuta npm run build"
    buffer = BytesIO(); Image.new("RGB", (40, 30), "green").save(buffer, "PNG")
    image = buffer.getvalue()
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
                policy = json.loads(json.dumps(INSTITUTIONAL_POLICY))
                communication = json.loads(json.dumps(COMMUNICATION_STATUS))
                state = {"write": True, "uploads": 0, "public_error": False}

                def api(route):
                    request = route.request; path = urlsplit(request.url).path
                    if request.resource_type == "image":
                        route.fulfill(status=200, content_type="image/png", body=image); return
                    if request.resource_type not in {"xhr", "fetch"}:
                        route.continue_(); return
                    body = request.post_data_json if request.post_data and "application/json" in request.headers.get("content-type", "") else None
                    calls.append((request.method, path, body)); status = 200
                    if path == "/auth/me":
                        data = {"id": 4, "nombre": "Administración", "correo": "test@example.com", "tipo": "administrador", "activo": True, "sucursal_id": 1}
                    elif path == "/auth/me/permisos":
                        data = [{"modulo": module, "puede_ver": True, **{f"puede_{action}": state["write"] for action in ("crear", "editar", "eliminar", "aprobar")}} for module in MODULES]
                    elif path == "/admin/configuracion":
                        data = {"nombre": "SMP", "correo": "clinic@example.com", "telefono": "965939522", "direccion": "Av. Prueba", "umbral_stock_bajo": 8, "recordatorios_citas": True, "alertas_stock": True}
                    elif path in {"/publico/institucional", "/admin/operaciones/configuracion"}:
                        status = 503 if path == "/publico/institucional" and state["public_error"] else 200
                        data = policy if status == 200 else {"detail": "Temporalmente no disponible"}
                    elif path == "/admin/operaciones/instalaciones":
                        assert state["write"]
                        state["uploads"] += 1; data = {"url": f"/uploads/instalaciones/{state['uploads']:032x}.png"}
                    elif path in {"/admin/operaciones/galeria", "/admin/operaciones/politicas-vacunas"}:
                        assert state["write"]
                        policy.update(body); data = policy
                    elif path == "/admin/operaciones/comunicaciones/estado":
                        data = communication
                    elif path.endswith("/vista-previa"):
                        event = path.split("/")[-2]
                        template = next(t for t in communication["plantillas"] if t["evento"] == event)
                        data = {"contenido": template["contenido"].format_map(body["valores"]), "parametros": [{"posicion": i + 1, "variable": variable, "valor": body["valores"][variable]} for i, variable in enumerate(template["variables"])], "encabezado": "sin documento", "alcance": "Vista previa guardada, sin envío real."}
                    elif path == "/admin/operaciones/mensajes":
                        data = [{"id": 20, "evento": "veterinario_reprogramacion", "destinatario": "51988777666", "estado": "entregado", "intentos": 1, "proveedor_id": "wamid.vet.reschedule", "error": None, "entregado_en": "2026-11-17T19:00:00Z"}]
                    else:
                        data = []
                    route.fulfill(status=status, content_type="application/json", body=json.dumps(data))

                page.route("**/*", api)
                page.route("**/publico/sucursales", lambda route: route.fulfill(content_type="application/json", body="[]"))
                page.goto(base + "/admin/configuracion", wait_until="domcontentloaded")
                for title in ("Consultorio principal", "Recepción de la clínica"):
                    page.get_by_label("Título de la nueva fotografía", exact=True).fill(title)
                    page.get_by_label("Fotografía real JPG o PNG (máximo 5 MB)", exact=True).set_input_files({"name": "synthetic.png", "mimeType": "image/png", "buffer": image})
                    page.get_by_role("button", name="Subir fotografía", exact=True).click()
                    expect(page.get_by_text("Fotografía subida. Guarda la galería para publicarla.", exact=True)).to_be_visible()
                    expect(page.get_by_role("img", name=title, exact=True)).to_be_visible()
                assert policy["galeria"] == []
                count += 1
                page.get_by_role("button", name="Subir posición de Recepción de la clínica", exact=True).click()
                page.get_by_role("button", name="Guardar galería pública", exact=True).click()
                expect(page.get_by_text("Galería pública guardada.", exact=True)).to_be_visible()
                assert [p["titulo"] for p in policy["galeria"]] == ["Recepción de la clínica", "Consultorio principal"]
                count += 1
                page.get_by_label("Días de anticipación de vacuna", exact=True).fill("31")
                expect(page.get_by_role("button", name="Guardar plazo de vacunas", exact=True)).to_be_disabled()
                count += 1
                page.get_by_label("Días de anticipación de vacuna", exact=True).fill("0")
                page.get_by_role("button", name="Guardar plazo de vacunas", exact=True).click()
                expect(page.get_by_text("Plazo de vacunas guardado.", exact=False)).to_be_visible()
                assert policy["dias_recordatorio_vacuna"] == 0 and len(policy["galeria"]) == 2
                count += 1
                page.get_by_text("Preparar plantillas de cancelación y receta", exact=True).click()
                page.get_by_label("Plantilla a configurar", exact=True).select_option("veterinario_reprogramacion")
                page.get_by_role("button", name="Ver vista previa guardada", exact=True).click()
                expect(page.get_by_text("Cita 123 de Mascota de prueba: 20/11/2026 10:00", exact=True)).to_be_visible()
                assert any(path.endswith("/veterinario_reprogramacion/vista-previa") for _, path, _ in calls)
                count += 1
                expect(page.get_by_text("Entrega: 2026-11-17T19:00:00Z", exact=True)).to_be_visible()
                count += 1
                state["write"] = False
                page.reload(wait_until="domcontentloaded")
                expect(page.get_by_label("Título de la nueva fotografía", exact=True)).to_be_disabled()
                expect(page.get_by_label("Días de anticipación de vacuna", exact=True)).to_be_disabled()
                expect(page.get_by_role("button", name="Guardar galería pública", exact=True)).to_have_count(0)
                count += 1
                page.get_by_text("Preparar plantillas de cancelación y receta", exact=True).click()
                page.get_by_label("Plantilla a configurar", exact=True).select_option("veterinario_reprogramacion")
                page.get_by_role("button", name="Ver vista previa guardada", exact=True).click()
                expect(page.get_by_text("Vista previa guardada, sin envío real.", exact=True)).to_be_visible()
                count += 1
                page.goto(base + "/", wait_until="domcontentloaded")
                gallery = page.locator('app-installations-gallery')
                expect(gallery.get_by_role("img", name="Recepción de la clínica", exact=True)).to_be_visible()
                expect(gallery.locator("figcaption")).to_have_text(["Recepción de la clínica", "Consultorio principal"])
                count += 1
                policy["galeria"] = []; state["public_error"] = True
                page.reload(wait_until="domcontentloaded")
                expect(gallery.get_by_text("No pudimos cargar las instalaciones.", exact=True)).to_be_visible()
                state["public_error"] = False
                gallery.get_by_role("button", name="Reintentar galería", exact=True).click()
                expect(gallery.get_by_text("Próximamente compartiremos fotografías de nuestras instalaciones.", exact=True)).to_be_visible()
                assert not errors, errors
                count += 1
                print(f"OK: 10 comprobaciones de otras cinco parciales, {viewport['width']}x{viewport['height']}; sin errores JavaScript")
                context.close()
            browser.close()
    finally:
        server.shutdown(); server.server_close()
    print(f"TOTAL: {count} comprobaciones con API/fotografías controladas; no acredita instalaciones reales ni WhatsApp externo")


if __name__ == "__main__":
    run()
