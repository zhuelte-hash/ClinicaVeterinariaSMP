"""E32: cinco parciales en Edge, API/JWT reales, SMTP TCP y Meta controlado.

Desde la raíz: backend/.venv/Scripts/python.exe backend/scripts/check_priority_partials_ui.py
Primero compilar frontend. Se usan exclusivamente datos SQLite aislados.
"""
import datetime as dt
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
import re
import sys
from threading import Thread
from urllib.parse import parse_qs, urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_admin_clinical_flows import clinic
from test_priority_stories import operations
from test_next_five_stories import mailbox, register, start_attention
from test_priority_communications import prescribe, close, messages
from test_priority_partial_progress import signed_command
from test_fundamental_stories import configure_phone
from check_five_stories_ui import ASSETS, Handler
from app.models.clinic import Cita, EstadoCita
from app.models.user import Usuario
from app.security import create_access_token
from app.services.access_service import now
from app.services.messaging_service import MessagingService
from app.services.policy_service import ZONE


@pytest.mark.parametrize("width,height", [(1440, 1000), (390, 844)])
def test_five_priority_partials_in_browser(operations, mailbox, monkeypatch, width, height):
    http, db, headers, _, product = operations
    account, code, _ = register(http, mailbox, "progress+ui@example.com")
    process = start_attention(http, db, headers); prescribe(http, headers, process, product)
    assert close(http, headers, process).status_code == 200
    MessagingService(db).deliver(messages(db, "receta")[0]); db.commit()
    configure_phone(db)
    appointment = db.get(Cita, 2)
    tomorrow = now().astimezone(ZONE).date() + dt.timedelta(days=1)
    appointment.fecha_hora_programada = dt.datetime.combine(tomorrow, dt.time(10), ZONE)
    appointment.fecha_hora_fin_programada = appointment.fecha_hora_programada + dt.timedelta(minutes=30)
    db.commit()
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(ASSETS)))
    Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    errors = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)

            def session(user=None):
                context = browser.new_context(viewport={"width": width, "height": height}, accept_downloads=True)
                if user:
                    context.add_init_script(f"localStorage.setItem('clinic_access_token', '{create_access_token(user)}')")
                page = context.new_page(); page.on("pageerror", lambda error: errors.append(str(error)))

                def api(route):
                    request = route.request
                    if request.resource_type not in {"xhr", "fetch"}:
                        route.continue_(); return
                    parsed = urlsplit(request.url)
                    path = parsed.path + ("?" + parsed.query if parsed.query else "")
                    forwarded = {key: value for key, value in request.headers.items() if key in {"authorization", "content-type", "x-sucursal-id"}}
                    response = http.request(request.method, path, headers=forwarded, content=request.post_data_buffer)
                    route.fulfill(status=response.status_code, headers={**response.headers, "access-control-allow-origin": "*"}, body=response.content)

                page.route("**/*", api)
                return context, page

            context, page = session()
            page.goto(base + "/verificar-correo?correo=progress%2Bui%40example.com&enviado=1&returnUrl=/reservar-cita", wait_until="domcontentloaded")
            page.get_by_label("Código", exact=True).fill(code)
            page.get_by_role("button", name="Verificar y entrar", exact=True).click()
            expect(page.get_by_role("heading", name="Mis citas", exact=True)).to_be_visible()
            assert db.get(Usuario, account["user"]["id"]).correo_verificado
            old_token = page.evaluate("localStorage.getItem('clinic_access_token')")
            page.goto(base + "/recuperar-clave?correo=progress%2Bui%40example.com", wait_until="domcontentloaded")
            page.get_by_role("button", name="Enviar enlace", exact=True).click()
            expect(page.get_by_role("button", name=re.compile("Solicitar otro enlace en"))).to_be_disabled()
            received = mailbox[0].get(timeout=5)
            link = re.search(r"http://\S+", received.get_content())[0].rstrip(".")
            query = parse_qs(urlsplit(link).query)
            page.goto(base + "/recuperar-clave?token=" + query["token"][0] + "&correo=progress%2Bui%40example.com", wait_until="domcontentloaded")
            expect(page.get_by_role("heading", name="Nueva contraseña", exact=True)).to_be_visible()
            assert query["token"][0] not in page.url
            page.get_by_label("Nueva contraseña", exact=True).fill("NuevaClave123")
            page.get_by_label("Repetir nueva contraseña", exact=True).fill("NuevaClave123")
            page.get_by_role("button", name="Guardar contraseña", exact=True).click()
            expect(page.get_by_text("Contraseña actualizada.", exact=False)).to_be_visible()
            assert http.get("/auth/me", headers={"Authorization": "Bearer " + old_token}).status_code == 401
            assert http.post("/auth/login", json={"identifier": "progress+ui@example.com", "password": "NuevaClave123"}).status_code == 200
            context.close()

            context, page = session(1)
            page.goto(base + "/reservar-cita", wait_until="domcontentloaded")
            attendance = page.locator("app-attendance-confirmation")
            attendance.get_by_role("button", name="Preparar confirmación", exact=True).click()
            prepared = attendance.get_by_role("link", name="Abrir WhatsApp para enviar", exact=True)
            expect(prepared).to_be_visible()
            command = parse_qs(urlsplit(prepared.get_attribute("href")).query)["text"][0]
            assert command.startswith("ASISTIRE 2 ") and db.get(Cita, 2).asistencia_confirmada_en is None
            assert signed_command(http, monkeypatch, command, "browser-attendance").status_code == 200
            attendance.get_by_role("button", name="Ya envié el mensaje: actualizar asistencia", exact=True).click()
            expect(attendance.get_by_text("Asistencia confirmada por WhatsApp", exact=True)).to_be_visible()
            assert http.patch("/portal/citas/2/cancelar", headers=headers[1], json={"motivo": "Cambio de planes UI"}).status_code == 200
            MessagingService(db).deliver(messages(db, "cita_cancelada")[0]); db.commit()
            page.get_by_role("button", name="Actualizar", exact=True).click()
            tracking = page.locator("app-appointment-communications")
            tracking.get_by_role("combobox", name="Cita a consultar", exact=False).select_option(label="#2 · Luna · cancelada")
            tracking.get_by_role("button", name="Consultar comunicaciones", exact=True).click()
            expect(tracking.get_by_text("Confirmación de cancelación", exact=True)).to_be_visible()
            expect(tracking.get_by_text("La clínica debe completar la configuración del envío", exact=True)).to_be_visible()
            tracking.get_by_role("combobox", name="Cita a consultar", exact=False).select_option(label="#1 · Luna · atendida")
            tracking.get_by_role("button", name="Consultar comunicaciones", exact=True).click()
            expect(tracking.get_by_text("Receta por WhatsApp", exact=True)).to_be_visible()
            expect(tracking.get_by_text("S/ 90.00", exact=False)).to_be_visible()
            with page.expect_download() as download:
                tracking.get_by_role("button", name="Descargar receta PDF", exact=True).click()
            assert download.value.suggested_filename == "receta-cita-1.pdf"
            context.close(); browser.close()
        assert not errors, errors
        print(f"Edge {width}x{height}: correo SMTP/verificación, recuperación/cooldown/token retirado/sesión revocada, asistencia versionada y webhook firmado, cancelación/seguimiento y receta PDF/orden; API/JWT reales y SQLite aislada.")
    finally:
        server.shutdown(); server.server_close()


if __name__ == "__main__":
    assert (ASSETS / "index.html").is_file(), "Primero ejecuta npm run build"
    raise SystemExit(pytest.main([__file__, "-q", "-s", "--tb=short"]))
