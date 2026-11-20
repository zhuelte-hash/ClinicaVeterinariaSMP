"""Edge escritorio/móvil contra FastAPI/JWT y SQLite aislada, sin API simulada.

Desde la raíz: backend/.venv/Scripts/python.exe backend/scripts/check_six_stories_ui.py
Compilar primero frontend. Ninguna petición usa la base operativa ni proveedores.
"""
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit
import sys

import pytest
from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_admin_clinical_flows import clinic
from test_priority_stories import operations
from test_next_five_stories import start_attention
from test_six_remaining_stories import prepare_survey
from check_five_stories_ui import ASSETS, Handler
from app.config import get_settings
from app.security import create_access_token
from app.models.operations import PlantillaMensaje
from sqlalchemy import select


@pytest.mark.parametrize("width,height", [(1440, 1000), (390, 844)])
def test_six_story_browser_flows(operations, monkeypatch, width, height):
    http, db, headers, start, _ = operations
    monkeypatch.setattr(get_settings(), "whatsapp_access_token", "")
    process = start_attention(http, db, headers)
    _, _, survey_token = prepare_survey(db, monkeypatch)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(ASSETS)))
    Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    errors, calls = [], []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)

            def open_session(user):
                context = browser.new_context(viewport={"width": width, "height": height})
                if user:
                    context.add_init_script(f"localStorage.setItem('clinic_access_token', '{create_access_token(user)}')")
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))

                def api(route):
                    request = route.request
                    if request.resource_type not in {"xhr", "fetch"}:
                        route.continue_(); return
                    parsed = urlsplit(request.url)
                    path = parsed.path + ("?" + parsed.query if parsed.query else "")
                    request_headers = {key: value for key, value in request.headers.items() if key in {"authorization", "content-type", "x-sucursal-id"}}
                    response = http.request(request.method, path, headers=request_headers, content=request.post_data_buffer)
                    calls.append((request.method, path, response.status_code, request_headers))
                    route.fulfill(status=response.status_code, headers={**response.headers, "access-control-allow-origin": "*"}, body=response.content)

                page.route("**/*", api)
                return context, page

            admin_context, page = open_session(4)
            page.goto(base + "/admin/ocupacion", wait_until="domcontentloaded")
            page.get_by_label("Desde", exact=True).fill(str(start.date()))
            page.get_by_label("Hasta", exact=True).fill(str(start.date()))
            page.get_by_role("button", name="Consultar ocupación", exact=True).click()
            expect(page.get_by_text("Capacidad disponible: 1320 min", exact=False)).to_be_visible()
            page.get_by_role("combobox", name="Veterinario", exact=True).select_option("2")
            page.get_by_role("button", name="Consultar ocupación", exact=True).click()
            expect(page.get_by_text("Capacidad disponible: 660 min", exact=False)).to_be_visible()
            page.goto(base + "/admin/sucursales", wait_until="domcontentloaded")
            page.get_by_label("Nombre de sucursal", exact=True).fill("Sede Norte UI")
            page.get_by_label("Dirección de sucursal", exact=True).fill("Av. Norte 123")
            page.get_by_role("button", name="Guardar sucursal", exact=True).click()
            expect(page.get_by_role("button", name="Trabajar en Sede Norte UI", exact=True)).to_be_visible()
            page.get_by_role("button", name="Trabajar en Sede Norte UI", exact=True).click()
            expect(page.get_by_role("combobox", name="Sede de trabajo", exact=True).locator("option:checked")).to_have_text("Sede Norte UI")
            page.goto(base + "/admin/ocupacion", wait_until="domcontentloaded")
            expect(page.get_by_text("No hay capacidad disponible en el período seleccionado.", exact=True)).to_be_visible()
            assert any("ocupacion" in path and h.get("x-sucursal-id") == "2" for _, path, _, h in calls)
            page.get_by_role("combobox", name="Sede de trabajo", exact=True).select_option(label="Sede de pruebas")
            page.goto(base + "/admin/configuracion", wait_until="domcontentloaded")
            page.get_by_text("Preparar plantillas de cancelación y receta", exact=True).click()
            for event in ("bienvenida", "laboratorio", "encuesta"):
                page.get_by_label("Plantilla a configurar", exact=True).select_option(event)
                page.get_by_label("Nombre aprobado en Meta", exact=True).fill("ui_" + event)
                page.get_by_label("Idioma aprobado", exact=True).fill("es")
                page.get_by_role("button", name="Guardar plantilla " + event, exact=True).click()
                expect(page.get_by_text("Plantilla guardada.", exact=False)).to_be_visible()
                page.get_by_role("button", name="Ver vista previa guardada", exact=True).click()
                expect(page.get_by_text("Encabezado: sin documento", exact=True)).to_be_visible()
                assert db.scalar(select(PlantillaMensaje).where(PlantillaMensaje.evento == event)).nombre_proveedor == "ui_" + event
            admin_context.close()

            vet_context, page = open_session(2)
            page.goto(base + "/veterinario/derivaciones", wait_until="domcontentloaded")
            expect(page.get_by_role("heading", name="Derivaciones clínicas", exact=True)).to_be_visible()
            page.get_by_role("combobox", name="Atención a derivar", exact=False).select_option(label=f"#{process} · Luna · Consulta")
            page.get_by_role("combobox", name="Especialista receptor", exact=False).select_option(label="Dr. Luis · General")
            page.get_by_label("Motivo de derivación", exact=True).fill("Evaluación por especialista UI")
            page.get_by_role("button", name="Enviar derivación", exact=True).click()
            expect(page.get_by_text("Derivación enviada.", exact=True)).to_be_visible()
            expect(page.get_by_text("Evaluación por especialista UI", exact=True)).to_be_visible()
            vet_context.close()
            recipient_context, page = open_session(3)
            page.goto(base + "/veterinario/derivaciones", wait_until="domcontentloaded")
            page.get_by_label("Respuesta a derivación #1", exact=True).fill("Acepto continuar la evaluación UI")
            page.get_by_role("button", name="Aceptar derivación #1", exact=True).click()
            expect(page.get_by_role("link", name="Continuar caso de Luna", exact=True)).to_be_visible()
            page.get_by_role("link", name="Continuar caso de Luna", exact=True).click()
            expect(page.get_by_role("tab", name="Historia clínica", exact=True)).to_be_visible()
            recipient_context.close()

            visitor_context, page = open_session(None)
            page.goto(base + "/encuesta/" + survey_token, wait_until="domcontentloaded")
            page.get_by_role("combobox").select_option(label="5 · Excelente")
            page.get_by_label("Comentario opcional", exact=True).fill("Excelente atención UI")
            page.get_by_role("button", name="Enviar valoración", exact=True).click()
            expect(page.get_by_text("Gracias. Tu respuesta ya fue registrada.", exact=True)).to_be_visible()
            page.goto(base + "/encuesta/" + survey_token, wait_until="domcontentloaded")
            expect(page.get_by_text("Gracias. Tu respuesta ya fue registrada.", exact=True)).to_be_visible()
            page.goto(base + "/encuesta/no-valida", wait_until="domcontentloaded")
            expect(page.get_by_role("alert")).to_contain_text("caducado")
            visitor_context.close(); browser.close()
        assert not errors, errors
        print(f"Edge {width}x{height}: ocupación/filtros, sucursal/contexto, tres plantillas/vistas previas, derivación/aceptación/continuidad y encuesta/uso único/caducidad; API/JWT reales y SQLite aislada.")
    finally:
        server.shutdown(); server.server_close()


if __name__ == "__main__":
    assert (ASSETS / "index.html").is_file(), "Primero ejecuta npm run build"
    raise SystemExit(pytest.main([__file__, "-q", "-s", "--tb=short"]))
