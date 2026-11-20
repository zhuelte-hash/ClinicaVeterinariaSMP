"""E18: interfaz HU-035/086/096/102 en Edge con API controlada.

Requiere el build de frontend y Playwright para Python. No utiliza la API real.
Ejecutar: python backend/scripts/check_four_stories_ui.py
"""
import datetime as dt
import json
from functools import partial
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlencode, urlsplit

from playwright.sync_api import expect, sync_playwright

from check_five_stories_ui import ASSETS, Handler, MODULES, PRODUCT, WEIGHT


def run():
    assert (ASSETS / "index.html").is_file(), "Primero ejecuta npm run build"
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(ASSETS)))
    Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    count = 0
    start = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=8)).replace(hour=15, minute=0, second=0, microsecond=0)
    proposed = start + dt.timedelta(hours=4)
    pet = {"id": 1, "nombre": "Luna", "especie": "Perro", "raza": None}
    service = {"id": 1, "codigo": "consulta", "nombre": "Consulta", "descripcion": "Consulta veterinaria", "precio_referencial": "50.00", "duracion_estimada_min": 30}
    appointment = {"id": 1, "fecha_hora_programada": start.isoformat(), "estado": "confirmada", "es_urgente": False, "motivo": None, "veterinario_id": 2, "mascota": pet, "servicio": service, "fecha_hora_propuesta": None}
    policy = {"horarios": [{"dia": i, "cerrado": False, "inicio": "08:00", "fin": "20:00", "descanso_inicio": None, "descanso_fin": None} for i in range(7)], "excepciones": [], "horas_reprogramacion": 4, "horas_cancelacion": 4}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            for viewport in ({"width": 1440, "height": 1000}, {"width": 390, "height": 844}):
                context = browser.new_context(viewport=viewport)
                context.add_init_script("localStorage.setItem('clinic_access_token', 'controlled-ui-session')")
                page = context.new_page()
                errors, calls, requests = [], [], []
                state = {"role": "administrador", "can_create": True, "read": False, "expense": False}
                page.on("pageerror", lambda error: errors.append(str(error)))

                def api(route):
                    request = route.request
                    if request.resource_type not in {"xhr", "fetch"}:
                        route.continue_(); return
                    url = urlsplit(request.url)
                    path = url.path
                    calls.append((request.method, path, parse_qs(url.query), request.post_data))
                    status = 200
                    if path == "/auth/me":
                        data = {"id": 4 if state["role"] == "administrador" else 1, "nombre": "Administración" if state["role"] == "administrador" else "María Pérez", "correo": "user@example.com", "tipo": state["role"], "activo": True, "sucursal_id": 1}
                    elif path == "/auth/me/permisos":
                        data = [{"modulo": module, "puede_ver": True, "puede_crear": state["can_create"], "puede_editar": True, "puede_eliminar": True, "puede_aprobar": True} for module in MODULES]
                    elif path == "/admin/operaciones/dashboard":
                        extra = 3 if state["expense"] else 0
                        data = {"desde": parse_qs(url.query)["desde"][0], "hasta": parse_qs(url.query)["hasta"][0], "ventas": "60.00", "cantidad_ventas": 2, "citas_por_estado": {"atendida": 1, "cancelada": 1}, "ordenes_pendientes": 0, "saldo_pendiente": 0, "pagos_por_validar": 0, "pagos_web_por_validar": 0, "stock_bajo": [], "productos_mas_vendidos": [{"id": 1, "nombre": "Medicina", "cantidad": "2.500"}], "servicios_mas_solicitados": [{"id": 1, "nombre": "Consulta", "cantidad": 2}], "servicios_mas_atendidos": [{"id": 1, "nombre": "Consulta", "cantidad": 1}], "finanzas": {"cobros": 50, "egresos": 7 + extra, "resultado": 43 - extra, "criterio": "Cobros efectivos y egresos registrados"}}
                    elif path == "/admin/operaciones/egresos":
                        data = [{"id": 1, "categoria": "Servicios", "concepto": "Electricidad", "monto": 7, "fecha": "2026-11-14"}]
                        if request.method == "POST":
                            state["expense"] = True
                            data, status = {"id": 2, **request.post_data_json}, 201
                        elif state["expense"]:
                            data.append({"id": 2, "categoria": "Servicios", "concepto": "Internet", "monto": 3, "fecha": "2026-11-14"})
                    elif path in {"/admin/notificaciones", "/portal/notificaciones"}:
                        data = [{"id": 1, "usuario_id": 4, "usuario_nombre": "Administración", "tipo": "stock_bajo", "titulo": "Reabastecimiento necesario", "mensaje": "Medicina: stock 2; mínimo 3.", "leida": state["read"], "fecha_creacion": "2026-11-14T12:00:00Z"}]
                    elif path == "/portal/notificaciones/1/leer":
                        state["read"] = True
                        data = {"id": 1, "leida": True}
                    elif path in {"/admin/productos", "/admin/inventario"}:
                        data = [PRODUCT, WEIGHT]
                    elif path == "/admin/categorias":
                        data = [{"id": 1, "nombre": "Medicamentos", "productos": 2}]
                    elif path == "/admin/configuracion":
                        data = {"nombre": "SMP", "alertas_stock": True}
                    elif path == "/api/admin/ventas":
                        data = {"total": 0, "pagina": 1, "tamano_pagina": 4, "ventas": []}
                    elif path == "/api/admin/ventas/resumen":
                        data = {"total_ventas": "60.00", "cantidad_ventas": 2, "ticket_promedio": "30.00", "productos_vendidos": 2.5}
                    elif path == "/publico/institucional":
                        data = policy
                    elif path == "/portal/servicios":
                        data = [service]
                    elif path == "/portal/mascotas":
                        data = [pet]
                    elif path == "/portal/citas":
                        data = [appointment, {**appointment, "id": 2, "estado": "atendida"}, {**appointment, "id": 3, "fecha_hora_programada": (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=2)).isoformat()}]
                    elif path == "/portal/disponibilidad":
                        data = [{"fecha_hora": instant.isoformat(), "veterinario_id": 2, "veterinario_nombre": "Dra. Ana"} for instant in (start, proposed)]
                    elif path in {"/portal/reprogramaciones", "/admin/operaciones/reprogramaciones"}:
                        data = requests
                    elif path == "/portal/citas/1/reprogramacion":
                        item = {"id": 1, "cita_id": 1, "cliente_id": 1, "estado": "pendiente", **request.post_data_json}
                        requests.append(item)
                        data, status = {**item, "whatsapp_url": "https://wa.me/51965939522?" + urlencode({"text": "Solicito reprogramar la cita #1. Motivo: Cambio por trabajo."})}, 201
                    elif path == "/admin/operaciones/reprogramaciones/1/resolver":
                        requests[0]["estado"] = "aceptada" if request.post_data_json["aceptar"] else "rechazada"
                        data = requests[0]
                    elif path == "/admin/citas/veterinarios":
                        data = [{"id": 2, "nombre": "Dra. Ana"}]
                    elif path == "/admin/citas":
                        data = []
                    else:
                        raise AssertionError(f"Petición inesperada: {request.method} {path}")
                    route.fulfill(status=status, content_type="application/json", body=json.dumps(data))

                page.route("**/*", api)
                page.route("**/publico/sucursales", lambda route: route.fulfill(content_type="application/json", body="[]"))
                page.goto(base + "/admin/dashboard")
                expect(page.get_by_role("heading", name="Servicios más solicitados", exact=True)).to_be_visible()
                for title, quantity in [("Productos más vendidos", "2.500"), ("Servicios más solicitados", "2"), ("Servicios más atendidos", "1")]:
                    article = page.locator("article").filter(has=page.get_by_role("heading", name=title, exact=True))
                    expect(article.locator("b")).to_have_text(quantity)
                page.locator("input[type=month]").fill("2026-10")
                expect(page.get_by_role("heading", name="Citas por estado · 2026-10", exact=True)).to_be_visible()
                assert any(path == "/admin/operaciones/dashboard" and query == {"desde": ["2026-10-01"], "hasta": ["2026-10-31"]} for method, path, query, body in calls)
                count += 1

                page.goto(base + "/admin/finanzas")
                expect(page.get_by_role("heading", name="Resultado estimado", exact=True)).to_be_visible()
                expect(page.locator("article").filter(has=page.get_by_role("heading", name="Resultado estimado", exact=True)).locator("b")).to_contain_text("43.00")
                page.locator("input[name=category]").fill("Servicios")
                page.locator("input[name=concept]").fill("Internet")
                page.locator("input[name=amount]").fill("3")
                page.get_by_role("button", name="Registrar egreso", exact=True).click()
                expect(page.get_by_text("Egreso registrado.", exact=True)).to_be_visible()
                expect(page.get_by_role("cell", name="Internet", exact=True)).to_be_visible()
                expect(page.locator("article").filter(has=page.get_by_role("heading", name="Resultado estimado", exact=True)).locator("b")).to_contain_text("40.00")
                count += 1

                page.goto(base + "/admin/notificaciones")
                expect(page.get_by_text("Medicina: stock 2; mínimo 3.", exact=True)).to_be_visible()
                page.get_by_role("button", name="Marcar leída", exact=True).click()
                expect(page.get_by_text("Leída", exact=True)).to_be_visible()
                page.get_by_role("button", name="Solo no leídas (0)", exact=True).click()
                expect(page.get_by_text("No hay notificaciones pendientes.", exact=True)).to_be_visible()
                count += 1

                state["role"] = "cliente"
                page.goto(base + "/reservar-cita")
                form = page.locator("app-reschedule-request")
                expect(form.get_by_role("heading", name="Solicitar reprogramación por WhatsApp", exact=True)).to_be_visible()
                expect(form.locator("select[name=appointment] option")).to_have_count(2)
                form.locator("select[name=appointment]").select_option(index=1)
                form.locator("input[name=day]").fill(start.date().isoformat())
                expect(form.locator("select[name=slot] option")).to_have_count(2)
                form.locator("select[name=slot]").select_option(index=1)
                form.locator("textarea[name=reason]").fill("Cambio por trabajo")
                form.get_by_role("button", name="Registrar solicitud y preparar WhatsApp", exact=True).click()
                link = form.get_by_role("link", name="Abrir WhatsApp con mi solicitud", exact=True)
                expect(link).to_have_attribute("href", "https://wa.me/51965939522?" + urlencode({"text": "Solicito reprogramar la cita #1. Motivo: Cambio por trabajo."}))
                expect(form.get_by_text("pendiente", exact=True)).to_be_visible()
                page.reload()
                expect(form.get_by_text("pendiente", exact=True)).to_be_visible()
                expect(form.locator("select[name=appointment] option")).to_have_count(1)
                count += 1

                state["role"] = "administrador"
                page.goto(base + "/admin/horarios")
                section = page.locator("section").filter(has=page.get_by_role("heading", name="Solicitudes de reprogramación", exact=True))
                section.locator("input").fill("Confirmado con el cliente")
                section.get_by_role("button", name="Aceptar horario", exact=True).click()
                expect(section.get_by_text("Solicitud #1 · Cita #1 · aceptada", exact=True)).to_be_visible()
                count += 1

                state["can_create"] = False
                page.goto(base + "/admin/finanzas")
                expect(page.get_by_text("Acceso de consulta:", exact=False)).to_be_visible()
                expect(page.get_by_role("button", name="Registrar egreso", exact=True)).to_have_count(0)
                expect(page.get_by_role("heading", name="Resultado estimado", exact=True)).to_be_visible()
                assert not errors, errors
                count += 1
                print(f"OK: 6 recorridos E18, viewport {viewport['width']}x{viewport['height']}; sin errores JavaScript")
                context.close()
            browser.close()
    finally:
        server.shutdown(); server.server_close()
    print(f"TOTAL: {count} comprobaciones de interfaz aprobadas con API controlada")


if __name__ == "__main__":
    run()
