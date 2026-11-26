"""E34: WhatsApp manual en Edge con frontend compilado, API/JWT reales y SQLite aislada.

No envía mensajes externos. Se abre por proxy Playwright la aplicación real con
sus permisos, persistencia y PDF; la fotografía procede del asset real del usuario.
"""
import datetime as dt
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
import re
import sys
from threading import Thread
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from playwright.sync_api import expect, sync_playwright

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "tests"))
sys.path.insert(0, str(BACKEND))
from test_admin_clinical_flows import clinic
from test_priority_stories import operations
from test_manual_whatsapp import manual
from test_next_five_stories import start_attention
from test_priority_communications import prescribe, close
from check_five_stories_ui import ASSETS, Handler
from scripts.set_clinic_whatsapp import set_phone
from app.main import app
from app.routers import operations as operations_routes
from app.models.clinic import AplicacionPreventiva, Cita, EstadoCita, ProcesoAtencion, ProcesoAtencionMedica, Producto
from app.models.operations import MensajeSalida
from app.security import create_access_token
from app.services.access_service import now
from app.services.policy_service import ZONE
from sqlalchemy import select


@pytest.mark.parametrize("width,height", [(1440, 1000), (390, 844)])
def test_manual_stories_browser(operations, manual, monkeypatch, tmp_path, width, height):
    http, db, headers, _, product = operations
    set_phone(db, "938304590")
    process = start_attention(http, db, headers); prescribe(http, headers, process, product)
    assert close(http, headers, process).status_code == 200
    recipe = db.scalar(select(MensajeSalida).where(MensajeSalida.evento == "receta"))
    appointment = db.get(Cita, 2)
    tomorrow = now().astimezone(ZONE).date() + dt.timedelta(days=1)
    appointment.fecha_hora_programada = dt.datetime.combine(tomorrow, dt.time(10), ZONE)
    appointment.fecha_hora_fin_programada = appointment.fecha_hora_programada + dt.timedelta(minutes=30)
    appointment.estado = EstadoCita.CONFIRMADA
    db.commit()
    uploads = tmp_path / "uploads"; installations = uploads / "instalaciones"; installations.mkdir(parents=True)
    monkeypatch.setattr(operations_routes, "INSTALLATIONS_DIR", installations)
    public_uploads = next(route.app for route in app.routes if getattr(route, "path", "") == "/uploads")
    monkeypatch.setattr(public_uploads, "all_directories", [str(uploads)])
    photo = http.post("/admin/operaciones/instalaciones", headers=headers[4], files={"archivo": ("fachada.jpg", (BACKEND / "assets/instalaciones/fachada-san-martin-de-porres.jpg").read_bytes(), "image/jpeg")})
    assert photo.status_code == 200
    assert http.put("/admin/operaciones/galeria", headers=headers[4], json={"galeria": [{"url": photo.json()["url"], "titulo": "Fachada y entrada de la Clínica Veterinaria San Martín de Porres"}]}).status_code == 200
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(ASSETS)))
    Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    errors, contexts = [], []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True, downloads_path=str(tmp_path / "downloads"))

            def session(user=None):
                context = browser.new_context(viewport={"width": width, "height": height}, accept_downloads=True)
                contexts.append(context)
                if user:
                    context.add_init_script(f"localStorage.setItem('clinic_access_token', '{create_access_token(user)}')")
                page = context.new_page(); page.on("pageerror", lambda error: errors.append(str(error)))

                def api(route):
                    request = route.request; parsed = urlsplit(request.url)
                    if request.resource_type not in {"xhr", "fetch"} and not parsed.path.startswith("/uploads/"):
                        route.continue_(); return
                    path = parsed.path + ("?" + parsed.query if parsed.query else "")
                    forwarded = {key: value for key, value in request.headers.items() if key in {"authorization", "content-type", "x-sucursal-id"}}
                    response = http.request(request.method, path, headers=forwarded, content=request.post_data_buffer)
                    route.fulfill(status=response.status_code, headers={**response.headers, "access-control-allow-origin": "*"}, body=response.content)
                page.route("**/*", api)
                return page

            public = session()
            public.goto(base + "/inicio", wait_until="domcontentloaded")
            expect(public.locator('a[href="tel:+51938304590"]').first).to_have_attribute("href", "tel:+51938304590")
            expect(public.get_by_role("link", name="Contactar por WhatsApp", exact=True)).to_have_attribute("href", re.compile(r"https://wa.me/51938304590\?"))
            image = public.locator('app-installations-gallery img').first
            image.scroll_into_view_if_needed()
            expect(image).to_have_attribute("alt", "Fachada y entrada de la Clínica Veterinaria San Martín de Porres")
            expect(image).to_have_js_property("complete", True)
            assert image.evaluate("image => image.naturalWidth") > 0
            assert public.evaluate("document.documentElement.scrollWidth <= innerWidth")
            public.screenshot(path=str(tmp_path / f"galeria-{width}.png"))
            public.goto(base + "/servicios", wait_until="domcontentloaded")
            expect(public.get_by_role("link", name="Consultar por WhatsApp", exact=True).first).to_have_attribute("href", re.compile(r"https://wa.me/51938304590\?"))
            public.goto(base + "/contacto", wait_until="domcontentloaded")
            public.get_by_label("Tu nombre", exact=False).fill("María & José")
            public.get_by_label("Celular / WhatsApp", exact=False).fill("938304590")
            public.get_by_label("Tu mensaje", exact=False).fill("Consulta + vacuna #1")
            public.evaluate("window.open = url => { window.__preparedWhatsappUrl = url; return null; }")
            public.get_by_role("button", name="Enviar por WhatsApp", exact=True).click()
            contact_link = public.evaluate("window.__preparedWhatsappUrl")
            assert urlsplit(contact_link).path == "/51938304590"
            assert "María & José" in parse_qs(urlsplit(contact_link).query)["text"][0]

            client = session(1)
            client.goto(base + "/reservar-cita", wait_until="domcontentloaded")
            attendance = client.locator("app-attendance-confirmation")
            attendance.get_by_role("button", name="Preparar confirmación", exact=True).click()
            prepared = attendance.get_by_role("link", name="Abrir WhatsApp para enviar", exact=True)
            expect(prepared).to_be_visible()
            reference = parse_qs(urlsplit(prepared.get_attribute("href")).query)["text"][0]
            assert "ASISTIRE 2 " in reference and urlsplit(prepared.get_attribute("href")).path == "/51938304590"
            assert appointment.asistencia_confirmada_en is None

            admin = session(4)
            admin.goto(base + "/admin/citas", wait_until="domcontentloaded")
            admin.get_by_role("button", name="Limpiar", exact=True).click()
            admin.get_by_role("button", name="Registrar asistencia recibida #2", exact=True).click()
            admin.get_by_label("Teléfono del mensaje recibido", exact=True).fill("999888777")
            admin.get_by_label("Referencia o mensaje de confirmación recibido", exact=True).fill(reference)
            admin.get_by_role("button", name="Registrar confirmación de asistencia", exact=True).click()
            expect(admin.get_by_text("Asistencia confirmada por WhatsApp ·", exact=False).first).to_be_visible()
            assert appointment.asistencia_confirmada_en is not None
            admin.locator('a[href*="tipo=cita"][href*="referencia=2"]').click()
            expect(admin.get_by_text("Cita #2", exact=True)).to_be_visible()
            admin.get_by_role("button", name="Ver todos los avisos", exact=True).click()
            expect(admin.get_by_role("button", name="Ver todos los avisos", exact=True)).to_have_count(0)
            attendance.get_by_role("button", name="Actualizar confirmación registrada por la clínica", exact=True).click()
            expect(attendance.get_by_text("Asistencia confirmada por WhatsApp", exact=True)).to_be_visible()

            vet = session(2)
            vet.goto(base + f"/veterinario/comunicaciones?tipo=atencion&referencia={process}", wait_until="domcontentloaded")
            expect(vet.get_by_role("heading", name="WhatsApp manual", exact=True)).to_be_visible()
            expect(vet.get_by_text(f"Atención #{process}", exact=True).first).to_be_visible()
            assert not errors, errors
            vet.get_by_label("Tipo de aviso", exact=True).select_option("receta")
            vet.get_by_role("button", name="Filtrar bandeja manual", exact=True).click()
            vet.get_by_role("button", name=f"Preparar aviso #{recipe.id}", exact=True).click()
            assert "OC-" in vet.get_by_label("Texto para WhatsApp", exact=True).input_value()
            expect(vet.get_by_role("link", name="Abrir chat de WhatsApp", exact=True)).to_have_attribute("href", re.compile(r"https://wa.me/51999888777\?"))
            vet.evaluate("window.open = () => ({opener: null, location: {replace: url => {window.__openedWhatsappUrl = url;}}, close: () => {window.__closedWhatsappPopup = true;}})")
            vet.get_by_role("button", name=f"Abrir WhatsApp #{recipe.id}", exact=True).click()
            expect(vet.get_by_label("Texto para WhatsApp", exact=True)).to_be_visible()
            assert urlsplit(vet.evaluate("window.__openedWhatsappUrl")).path == "/51999888777"
            vet.evaluate("Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {writeText: async text => {window.__copiedWhatsappText = text;}}})")
            vet.get_by_role("button", name="Copiar mensaje", exact=True).click()
            expect(vet.get_by_text("Mensaje copiado.", exact=True)).to_be_visible()
            assert vet.evaluate("window.__copiedWhatsappText") == vet.get_by_label("Texto para WhatsApp", exact=True).input_value()
            with vet.expect_download() as download:
                vet.get_by_role("button", name="Descargar PDF del aviso", exact=True).click()
            assert download.value.suggested_filename == f"aviso-{recipe.id}.pdf"
            vet.get_by_role("button", name="Registrar gestión manual", exact=True).click()
            expect(vet.get_by_text("Gestión manual registrada.", exact=False)).to_be_visible()
            assert recipe.estado == "gestionado_manual" and recipe.enviado_en is None

            order = http.get("/operaciones/ordenes", headers=headers[5]).json()[0]
            paid = http.post(f"/operaciones/ordenes/{order['id']}/abonos", headers=headers[5], json={"monto": "90.00", "medio": "efectivo", "canal": "caja", "clave_idempotencia": str(uuid4())})
            assert paid.status_code == 201 and paid.json()["estado"] == "pagada"
            cashier = session(5)
            cashier.goto(base + "/caja/ordenes", wait_until="domcontentloaded")
            cashier.get_by_role("button", name="Ver detalle y pagos", exact=True).first.click()
            cashier.get_by_role("link", name="Enviar orden, recordatorio o boleta por WhatsApp", exact=True).click()
            expect(cashier.get_by_text(f"Orden #{order['id']}", exact=True)).to_be_visible()
            cashier.get_by_label("Tipo de aviso", exact=True).select_option("pago_validado")
            cashier.get_by_role("button", name="Filtrar bandeja manual", exact=True).click()
            receipt = db.scalar(select(MensajeSalida).where(MensajeSalida.evento == "pago_validado"))
            cashier.get_by_role("button", name=f"Preparar aviso #{receipt.id}", exact=True).click()
            with cashier.expect_download() as download:
                cashier.get_by_role("button", name="Descargar PDF del aviso", exact=True).click()
            assert download.value.suggested_filename == f"aviso-{receipt.id}.pdf"
            assert db.get(Producto, product).stock_actual == 8

            followup = ProcesoAtencion(mascota_id=1, tipo="medica", estado="cerrada", fecha_cierre=now() - dt.timedelta(hours=25))
            db.add(followup); db.flush(); db.add(ProcesoAtencionMedica(proceso_id=followup.id, veterinario_id=2))
            db.add(AplicacionPreventiva(proceso_id=followup.id, veterinario_id=2, tipo="vacuna", producto="Vacuna anual", proxima_fecha=now().astimezone(ZONE).date() + dt.timedelta(days=3))); db.commit()
            admin.goto(base + "/admin/comunicaciones", wait_until="domcontentloaded")
            admin.get_by_role("button", name="Preparar avisos programados ahora", exact=True).click()
            expect(admin.get_by_text("Avisos programados actualizados.", exact=False)).to_be_visible()
            admin.get_by_label("Tipo de aviso", exact=True).select_option("encuesta")
            admin.get_by_role("button", name="Filtrar bandeja manual", exact=True).click()
            survey = db.scalar(select(MensajeSalida).where(MensajeSalida.evento == "encuesta"))
            admin.get_by_role("button", name=f"Preparar aviso #{survey.id}", exact=True).click()
            survey_text = admin.get_by_label("Texto para WhatsApp", exact=True).input_value()
            assert base + "/encuesta/" in survey_text
            token = re.search(r"/encuesta/([A-Za-z0-9_-]+)", survey_text)[1]
            public.goto(base + "/encuesta/" + token, wait_until="domcontentloaded")
            public.get_by_role("combobox").select_option(label="5 · Excelente")
            public.get_by_label("Comentario opcional", exact=True).fill("Prueba funcional de la encuesta")
            public.get_by_role("button", name="Enviar valoración", exact=True).click()
            expect(public.get_by_text("Gracias. Tu respuesta ya fue registrada.", exact=True)).to_be_visible()
            assert http.post(f"/encuestas/{token}", json={"valoracion": 1}).status_code == 409
            assert not errors, errors
            assert vet.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert cashier.evaluate("document.documentElement.scrollWidth <= innerWidth")
            for context in contexts:
                context.close()
            browser.close()
        print(f"Edge {width}x{height}: teléfono público, galería real, contacto, asistencia persistida, bandejas por rol, receta/boleta PDF y encuesta única; API/JWT reales, SQLite aislada, sin envíos externos.")
    finally:
        server.shutdown(); server.server_close()


if __name__ == "__main__":
    assert (ASSETS / "index.html").is_file(), "Primero ejecuta npm run build en frontend"
    raise SystemExit(pytest.main([__file__, "-q", "-s", "--tb=short", *sys.argv[1:]]))
