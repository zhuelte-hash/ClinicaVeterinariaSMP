"""HU-095/116/039/093/114 en Edge, escritorio/móvil, con API controlada."""
import datetime as dt
import json
from functools import partial
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

from playwright.sync_api import expect, sync_playwright
from check_five_stories_ui import ASSETS, Handler, MODULES, PRODUCT, UNITS, COMMUNICATION_STATUS


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
                page = context.new_page()
                errors, calls = [], []
                page.on("pageerror", lambda error: errors.append(str(error)))
                zone = ZoneInfo("America/Lima")
                tomorrow = dt.datetime.combine(dt.datetime.now(zone).date() + dt.timedelta(days=1), dt.time(10), zone).isoformat()
                state = {"role": "administrador", "write": True, "confirmed": False, "bad_restore": False}
                communication = json.loads(json.dumps(COMMUNICATION_STATUS))
                outgoing = [{"id": 10, "evento": "receta", "destinatario": "51999888777", "estado": "error", "intentos": 2, "proveedor_id": None, "error": "Proveedor no disponible"}]
                policy = {"horarios": [{"dia": i, "cerrado": i == 6, "inicio": "08:00", "fin": "20:00", "descanso_inicio": "12:00", "descanso_fin": "13:00"} for i in range(7)], "excepciones": [], "galeria": [], "horas_cancelacion": 4, "horas_reprogramacion": 4, "dias_alerta_vencimiento": 30, "dias_recordatorio_vacuna": 3}
                pet = {"id": 1, "cliente_id": 1, "nombre": "Luna", "especie": "Perro", "raza": "Mestiza", "sexo": "hembra", "foto_url": None}
                service = {"id": 1, "codigo": "consulta", "nombre": "Consulta", "descripcion": "Consulta", "precio_referencial": "50.00", "duracion_estimada_min": 30}

                def appointment():
                    return {"id": 1, "estado": "confirmada", "fecha_hora_programada": tomorrow, "fecha_hora_fin_programada": tomorrow, "fecha_creacion": tomorrow, "fecha_actualizacion": tomorrow, "es_urgente": False, "motivo": "Control", "fecha_hora_llegada": None, "asistencia_confirmada_en": tomorrow if state["confirmed"] else None, "cancelacion_automatica_at": None, "fecha_hora_propuesta": None, "telefono_contacto": "999888777", "preferencia_contacto": "whatsapp", "nota_coordinacion": None, "veterinario_id": 2, "mascota": pet, "servicio": service, "cliente_nombre": "María Pérez", "mascota_nombre": "Luna", "servicio_nombre": "Consulta", "veterinario_nombre": "Dra. Ana"}

                def api(route):
                    request = route.request
                    if request.resource_type not in {"xhr", "fetch"}:
                        route.continue_(); return
                    parsed = urlsplit(request.url); path = parsed.path
                    body = request.post_data_json if "application/json" in request.headers.get("content-type", "") and request.post_data else None
                    calls.append((request.method, path, body, parsed.query))
                    status = 200
                    if path == "/auth/me":
                        data = {"id": 1 if state["role"] == "cliente" else 4, "nombre": "María Pérez" if state["role"] == "cliente" else "Administración", "correo": "test@example.com", "tipo": state["role"], "activo": True, "telefono": "999888777", "sucursal_id": 1}
                    elif path == "/auth/me/permisos":
                        data = [{"modulo": module, "puede_ver": True, **{f"puede_{action}": state["write"] for action in ("crear", "editar", "eliminar", "aprobar")}} for module in MODULES]
                    elif path in {"/publico/institucional", "/admin/operaciones/configuracion"}:
                        data = policy
                    elif path == "/admin/configuracion":
                        data = {"nombre": "Clínica SMP", "correo": "clinica@example.com", "telefono": "965939522", "direccion": "Av. Prueba", "umbral_stock_bajo": 8, "recordatorios_citas": True, "alertas_stock": True}
                    elif path == "/admin/operaciones/comunicaciones/estado":
                        data = communication
                    elif path == "/admin/operaciones/mensajes-entrantes":
                        data = []
                    elif path.startswith("/admin/operaciones/plantillas/"):
                        assert state["write"]
                        event = path.rsplit("/", 1)[1]
                        data = {"evento": event, **body}
                        communication["plantillas"] = [data if row["evento"] == event else row for row in communication["plantillas"]]
                    elif path == "/admin/operaciones/mensajes":
                        query = parse_qs(parsed.query)
                        data = [row for row in outgoing if all(row[key] == query[key][0] for key in ("evento", "estado") if key in query)]
                    elif path == "/admin/operaciones/mensajes/10/reintentar":
                        assert state["write"]
                        outgoing[0].update(estado="pendiente", intentos=0)
                        data = {"estado": "pendiente"}
                    elif path == "/admin/operaciones/respaldo":
                        route.fulfill(status=200, content_type="application/zip", body=b"PK controlled backup"); return
                    elif path == "/admin/operaciones/respaldo/verificar":
                        assert b'name="archivo"' in request.post_data_buffer
                        if state["bad_restore"]:
                            data, status = {"detail": "No se pudo verificar la restauración: integridad inválida"}, 422
                        else:
                            data = {"valido": True, "tablas": 50, "registros_restaurados": 123, "archivos": 2, "verificacion": "Restauración lógica en SQLite aislado verificada."}
                    elif path in {"/admin/operaciones/politicas-citas", "/admin/operaciones/politicas-vencimiento"}:
                        assert state["write"]
                        policy.update(body); data = policy
                    elif path in {"/admin/productos", "/admin/inventario"}:
                        data = [PRODUCT]
                    elif path == "/admin/operaciones/unidades":
                        data = UNITS
                    elif path == "/admin/operaciones/proveedores":
                        data = [{"id": 1, "razon_social": "Proveedor"}]
                    elif path == "/admin/operaciones/lotes":
                        data = [{"id": 1, "producto_id": 1, "producto_nombre": "Medicina", "codigo": "LOT-SOON", "cantidad": "2.000", "costo_unitario": "5.00", "vencimiento": tomorrow[:10], "estado_vencimiento": "por_vencer"}]
                    elif path == "/admin/operaciones/kardex/1":
                        data = [{"id": 1, "fecha": tomorrow, "tipo": "compra", "cantidad": 2, "saldo_anterior": 10, "saldo_nuevo": 12, "motivo": "Recepción FAC-1", "referencia": "FAC-1", "usuario_nombre": "Administración", "lote_codigo": "LOT-SOON"}]
                    elif path == "/admin/citas/veterinarios":
                        data = [{"id": 2, "nombre": "Dra. Ana"}]
                    elif path == "/admin/citas/reporte":
                        data = {"fecha_inicial": tomorrow[:10], "fecha_final": tomorrow[:10], "total": 1, "urgentes": 0, "por_estado": {"confirmada": 1}}
                    elif path in {"/admin/citas", "/portal/citas"}:
                        data = [appointment()]
                    elif path == "/portal/servicios":
                        data = [service]
                    elif path == "/portal/mascotas":
                        data = [pet]
                    elif path == "/portal/citas/1/asistencia-whatsapp":
                        data = {"whatsapp_url": "https://wa.me/51965939522?text=ASISTIRE%201"}
                    else:
                        data = []
                    route.fulfill(status=status, content_type="application/json", body=json.dumps(data))

                page.route("**/*", api)
                page.goto(base + "/admin/configuracion")
                expect(page.get_by_role("heading", name="Comunicaciones de la primera entrega")).to_be_visible()
                expect(page.get_by_text("SMTP_HOST", exact=True)).to_be_visible()
                expect(page.get_by_text("No acredita recepción externa", exact=False)).to_be_visible()
                count += 1
                page.get_by_text("Preparar plantillas de cancelación y receta", exact=True).click()
                recipe = page.locator('form').filter(has=page.get_by_role("heading", name="Receta PDF (HU-050)"))
                recipe.get_by_label("Nombre aprobado en Meta").fill("receta_pdf")
                recipe.get_by_label("Variables del cuerpo en orden (separadas por coma)").fill("codigo, nombre, mascota")
                page.get_by_role("button", name="Guardar plantilla receta", exact=True).click()
                expect(page.get_by_text("Plantilla guardada.", exact=False)).to_be_visible()
                assert any(method == "PUT" and path.endswith("/plantillas/receta") and body["variables"] == ["codigo", "nombre", "mascota"] for method, path, body, _ in calls)
                count += 1
                page.get_by_label("Evento de comunicación").select_option("receta")
                page.get_by_label("Estado del envío").select_option("error")
                page.get_by_role("button", name="Filtrar envíos", exact=True).click()
                expect(page.get_by_role("button", name="Reintentar #10", exact=True)).to_be_visible()
                assert any(path.endswith("/mensajes") and parse_qs(query) == {"evento": ["receta"], "estado": ["error"]} for _, path, _, query in calls)
                count += 1
                page.get_by_role("button", name="Reintentar #10", exact=True).click()
                expect(page.get_by_text("Reintento preparado.", exact=False)).to_be_visible()
                expect(page.get_by_role("button", name="Reintentar #10", exact=True)).to_have_count(0)
                count += 1
                expect(page.get_by_role("heading", name="Respaldo de información")).to_be_visible()
                with page.expect_download() as download:
                    page.get_by_role("button", name="Descargar respaldo ZIP").click()
                assert download.value.suggested_filename.startswith("respaldo-clinica-")
                count += 1
                page.locator('input[type="file"][accept=".zip,application/zip"]').set_input_files({"name": "respaldo.zip", "mimeType": "application/zip", "buffer": b"PK controlled backup"})
                page.get_by_role("button", name="Verificar restauración aislada").click()
                expect(page.get_by_text("Restauración lógica verificada", exact=True)).to_be_visible()
                expect(page.get_by_text("50 tablas · 123 registros · 2 archivos.")).to_be_visible()
                count += 1
                state["bad_restore"] = True
                page.get_by_role("button", name="Verificar restauración aislada").click()
                expect(page.get_by_text("No se pudo verificar la restauración: integridad inválida")).to_be_visible()
                count += 1
                state["write"] = False
                page.reload(wait_until="domcontentloaded")
                expect(page.get_by_text("Acceso de consulta. Generar y verificar respaldos requiere edición de Usuarios.")).to_be_visible()
                expect(page.get_by_role("button", name="Descargar respaldo ZIP")).to_have_count(0)
                count += 1
                expect(page.get_by_role("button", name="Guardar plantilla receta", exact=True)).to_have_count(0)
                expect(page.get_by_role("button", name="Reintentar #10", exact=True)).to_have_count(0)
                page.get_by_text("Preparar plantillas de cancelación y receta", exact=True).click()
                expect(page.get_by_label("Nombre aprobado en Meta").first).to_be_disabled()
                count += 1

                state["write"] = True
                page.goto(base + "/admin/horarios")
                page.get_by_label("Horas mínimas para cancelar").fill("12")
                page.get_by_label("Horas mínimas para reprogramar").fill("24")
                page.get_by_role("button", name="Guardar anticipación", exact=True).click()
                expect(page.get_by_text("Anticipación guardada y aplicada a cancelaciones y reprogramaciones.")).to_be_visible()
                assert any(method == "PUT" and path.endswith("/politicas-citas") and body == {"horas_cancelacion": 12, "horas_reprogramacion": 24} for method, path, body, _ in calls)
                page.get_by_label("Horas mínimas para reprogramar").fill("3")
                expect(page.get_by_role("button", name="Guardar anticipación", exact=True)).to_be_disabled()
                count += 1
                state["write"] = False
                page.reload(wait_until="domcontentloaded")
                expect(page.get_by_label("Horas mínimas para cancelar")).to_be_disabled()
                expect(page.get_by_role("button", name="Guardar anticipación", exact=True)).to_have_count(0)
                count += 1

                state["write"] = True
                page.goto(base + "/admin/recepciones")
                expect(page.get_by_role("cell", name="Próximo a vencer", exact=True)).to_be_visible()
                page.get_by_label("Anticipación de alertas (días)").fill("15")
                page.get_by_role("button", name="Guardar plazo de vencimiento").click()
                expect(page.get_by_text("Plazo de vencimiento guardado. Las alertas se generan al ejecutar el worker.")).to_be_visible()
                page.get_by_label("Solo vencidos / próximos a vencer").check()
                assert any(path.endswith("/lotes") and parse_qs(query).get("por_vencer") == ["true"] for _, path, _, query in calls)
                count += 1

                page.goto(base + "/admin/inventario")
                page.get_by_label("Producto del Kardex").select_option(label="Medicina · unidad")
                expect(page.get_by_role("cell", name="Recepción FAC-1 · FAC-1", exact=True)).to_be_visible()
                page.locator('[name="kardexStart"]').fill(tomorrow[:10]); page.locator('[name="kardexEnd"]').fill(tomorrow[:10])
                page.locator('[name="kardexKind"]').select_option("compra")
                page.get_by_role("button", name="Consultar Kardex").click()
                expect(page.get_by_role("button", name="Consultar Kardex")).to_be_enabled()
                assert any(path.endswith("/kardex/1") and parse_qs(query).get("tipo") == ["compra"] and parse_qs(query).get("desde") == [tomorrow[:10]] for _, path, _, query in calls)
                count += 1
                page.locator('[name="kardexStart"]').fill("2030-12-31"); page.locator('[name="kardexEnd"]').fill("2030-01-01")
                page.get_by_role("button", name="Consultar Kardex").click()
                expect(page.get_by_text("La fecha inicial no puede ser posterior a la final.")).to_be_visible()
                count += 1

                state["role"] = "cliente"
                page.goto(base + "/reservar-cita")
                page.get_by_role("button", name="Preparar confirmación", exact=True).click()
                link = page.get_by_role("link", name="Abrir WhatsApp para enviar")
                expect(link).to_have_attribute("href", "https://wa.me/51965939522?text=ASISTIRE%201")
                assert not state["confirmed"]
                count += 1
                state["confirmed"] = True
                page.get_by_role("button", name="Ya envié el mensaje: actualizar asistencia", exact=True).click()
                expect(page.get_by_text("Asistencia confirmada por WhatsApp", exact=True)).to_be_visible()
                expect(page.get_by_role("button", name="Preparar confirmación", exact=True)).to_have_count(0)
                count += 1
                state["role"] = "administrador"
                page.goto(base + "/admin/citas")
                expect(page.get_by_text("Asistencia confirmada por WhatsApp ·", exact=False)).to_be_visible()
                count += 1
                assert not errors, errors
                print(f"OK: 17 recorridos fundamentales y comunicaciones, {viewport['width']}x{viewport['height']}; sin errores JavaScript")
                context.close()
            browser.close()
    finally:
        server.shutdown(); server.server_close()
    print(f"TOTAL: {count} comprobaciones fundamentales con API controlada")


if __name__ == "__main__":
    run()
