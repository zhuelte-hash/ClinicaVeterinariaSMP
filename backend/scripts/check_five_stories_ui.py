"""Comprobaciones de interfaz E17 con API controlada (no usa datos operativos).

Requiere `npm run build` en frontend, Playwright para Python y Microsoft Edge.
Ejecutar desde la raíz: python backend/scripts/check_five_stories_ui.py
"""
import datetime as dt
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "frontend" / "dist" / "browser"
MODULES = ("productos", "inventario", "ventas", "usuarios", "citas", "mascotas", "historias_clinicas")
PRODUCT = {"id": 1, "sku": "MED-1", "nombre": "Medicina", "precio_venta": "20.00", "stock_actual": 2, "stock_minimo": 3, "activo": True, "imagen_url": "/logo.png", "categoria_id": 1, "categoria_nombre": "Medicamentos", "proveedor_id": 1, "descripcion": "Medicina de prueba", "especies": [], "unidad_medida": "unidad", "fraccionable": False, "requiere_vencimiento": True, "costo_unitario": "5.00"}
WEIGHT = {**PRODUCT, "id": 2, "sku": "KG-1", "nombre": "Alimento al peso", "stock_actual": 0.25, "stock_minimo": 0.125, "unidad_medida": "kg", "fraccionable": True, "requiere_vencimiento": False}
UNITS = [{"codigo": "unidad", "nombre": "Unidad", "dimension": "conteo", "factor_base": 1, "fraccionable": False}, {"codigo": "kg", "nombre": "Kilogramo", "dimension": "masa", "factor_base": 1000, "fraccionable": True}, {"codigo": "g", "nombre": "Gramo", "dimension": "masa", "factor_base": 1, "fraccionable": True}]
INSTITUTIONAL_POLICY = {"horarios": [], "excepciones": [], "galeria": [], "horas_cancelacion": 4, "horas_reprogramacion": 4, "dias_alerta_vencimiento": 30, "dias_recordatorio_vacuna": 3}
COMMUNICATION_STATUS = {
    "correo": {"configurado": False, "faltantes": ["SMTP_HOST", "MAIL_FROM"]},
    "whatsapp": {"configurado": False, "faltantes": ["WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_ACCESS_TOKEN"]},
    "webhook": {"configurado": False, "faltantes": ["WHATSAPP_APP_SECRET", "WHATSAPP_VERIFY_TOKEN"]},
    "telefono_clinica_valido": True,
    "plantillas": [
        {"evento": "cita_cancelada", "nombre_proveedor": "", "contenido": "Hola {nombre}, la cita de {mascota} fue cancelada: {motivo}", "variables": ["nombre", "mascota", "motivo"], "idioma": "es_PE", "activa": True},
        {"evento": "receta", "nombre_proveedor": "", "contenido": "Hola {nombre}, receta de {mascota}: {codigo}", "variables": ["nombre", "mascota", "codigo"], "idioma": "es_PE", "activa": True},
        {"evento": "cita_confirmada", "nombre_proveedor": "", "contenido": "Hola {nombre}, cita de {mascota}: {fecha}", "variables": ["nombre", "mascota", "fecha"], "idioma": "es_PE", "activa": True},
        {"evento": "cita_reprogramada", "nombre_proveedor": "", "contenido": "Hola {nombre}, nueva cita de {mascota}: {fecha}", "variables": ["nombre", "mascota", "fecha"], "idioma": "es_PE", "activa": True},
        {"evento": "veterinario_reprogramacion", "nombre_proveedor": "", "contenido": "Cita {cita} de {mascota}: {fecha}", "variables": ["cita", "mascota", "fecha"], "idioma": "es_PE", "activa": True},
        {"evento": "veterinario_cancelacion", "nombre_proveedor": "", "contenido": "Cita {cita} de {mascota} cancelada: {motivo}", "variables": ["cita", "mascota", "motivo"], "idioma": "es_PE", "activa": True},
        {"evento": "recordatorio_24h", "nombre_proveedor": "", "contenido": "Hola {nombre}, recuerda la cita de {mascota} para {fecha}. ASISTIRE {cita}", "variables": ["nombre", "mascota", "fecha", "cita"], "idioma": "es", "activa": True},
        {"evento": "recordatorio_2h", "nombre_proveedor": "", "contenido": "Hola {nombre}, la cita de {mascota} es a las {fecha}.", "variables": ["nombre", "mascota", "fecha"], "idioma": "es", "activa": True},
        {"evento": "orden_creada", "nombre_proveedor": "", "contenido": "Hola {nombre}, orden {codigo} por S/ {total}.", "variables": ["nombre", "codigo", "total"], "idioma": "es", "activa": True},
        {"evento": "orden_recordatorio", "nombre_proveedor": "", "contenido": "Hola {nombre}, orden {codigo} por S/ {total} sin comprobante.", "variables": ["nombre", "codigo", "total"], "idioma": "es", "activa": True},
        {"evento": "pago_validado", "nombre_proveedor": "", "contenido": "Hola {nombre}, pago de {codigo} validado. Adjuntamos boleta.", "variables": ["nombre", "codigo"], "idioma": "es", "activa": True},
    ],
    "alcance": "Configuración local sin conectar a proveedores. No acredita recepción externa ni worker activo.",
}


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if not Path(self.translate_path(self.path)).is_file():
            self.path = "/index.html"
        super().do_GET()

    def log_message(self, *_args):
        pass


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
                errors, requests = [], []
                page.on("pageerror", lambda error: errors.append(str(error)))

                def api(route):
                    request = route.request
                    if request.resource_type not in {"xhr", "fetch"}:
                        route.continue_(); return
                    path = urlsplit(request.url).path
                    requests.append((request.method, path, request.post_data))
                    status = 200
                    if path == "/auth/me":
                        data = {"id": 4, "nombre": "Administración", "correo": "admin@example.com", "tipo": "administrador", "activo": True, "sucursal_id": 1}
                    elif path == "/auth/me/permisos":
                        data = [{"modulo": module, **{f"puede_{action}": True for action in ("ver", "crear", "editar", "eliminar", "aprobar")}} for module in MODULES]
                    elif path == "/admin/operaciones/dashboard":
                        data = {"ventas": "40.00", "cantidad_ventas": 2, "citas_por_estado": {"confirmada": 2, "cancelada": 1, "atendida": 0}, "ordenes_pendientes": 3, "saldo_pendiente": "80.00", "pagos_por_validar": 1, "pagos_web_por_validar": 2, "stock_bajo": [{"id": 1, "nombre": "Medicina", "stock": 2, "minimo": 3}], "productos_mas_vendidos": [], "servicios_mas_atendidos": [], "finanzas": {"cobros": 40, "egresos": 0, "resultado": 40, "criterio": "Prueba"}}
                    elif path in {"/admin/productos", "/admin/inventario"}:
                        data = [PRODUCT, WEIGHT]
                    elif path == "/admin/productos/catalogo":
                        data = {"categorias": [{"id": 1, "nombre": "Medicamentos"}], "proveedores": [{"id": 1, "nombre": "Proveedor"}]}
                    elif path == "/admin/categorias":
                        data = [{"id": 1, "nombre": "Medicamentos", "productos": 2}]
                    elif path == "/admin/configuracion":
                        data = {"nombre": "SMP", "alertas_stock": True}
                    elif path == "/admin/operaciones/comunicaciones/estado":
                        data = COMMUNICATION_STATUS
                    elif path == "/admin/operaciones/mensajes":
                        data = []
                    elif path == "/admin/operaciones/mensajes-entrantes":
                        data = []
                    elif path in {"/publico/institucional", "/admin/operaciones/configuracion"}:
                        data = INSTITUTIONAL_POLICY
                    elif path == "/api/admin/ventas":
                        data = {"total": 0, "pagina": 1, "tamano_pagina": 4, "ventas": []}
                    elif path == "/api/admin/ventas/resumen":
                        data = {"total_ventas": "40.00", "cantidad_ventas": 2, "ticket_promedio": "20.00", "productos_vendidos": 2}
                    elif path in {"/admin/operaciones/unidades", "/admin/productos/unidades"}:
                        data = UNITS if request.method == "GET" else request.post_data_json
                        status = 200 if request.method == "GET" else 201
                    elif path == "/admin/operaciones/proveedores":
                        data = [{"id": 1, "razon_social": "Proveedor"}]
                    elif path == "/admin/operaciones/lotes":
                        data = [{"id": 1, "producto_id": 1, "producto_nombre": "Medicina", "codigo": "LOTE-1", "cantidad": "2.000", "costo_unitario": "5.0000", "vencimiento": "2000-01-01"}]
                    elif path == "/admin/operaciones/compras":
                        data, status = ([], 200) if request.method == "GET" else ({"id": 1}, 201)
                    elif path == "/admin/operaciones/auditoria":
                        data = [{"id": 1, "usuario_id": 4, "autor": "Administración", "fecha": "2026-11-14T12:00:00Z", "entidad": "productos", "registro_id": "1", "accion": "editar", "cambios": {"stock_minimo": {"antes": 1, "despues": 3}}}]
                    elif path == "/admin/productos/1" and request.method == "PATCH":
                        data = {**PRODUCT, **request.post_data_json}
                    elif path in {"/admin/notificaciones", "/portal/notificaciones", "/admin/citas", "/admin/ajustes-inventario"}:
                        data = []
                    else:
                        raise AssertionError(f"Petición inesperada: {request.method} {path}")
                    route.fulfill(status=status, content_type="application/json", body=json.dumps(data))

                page.route("**/*", api)
                page.goto(base + "/admin/dashboard")
                expect(page.get_by_text("Órdenes pendientes actuales", exact=True)).to_be_visible()
                expect(page.get_by_text("Saldo: S/ 80.00", exact=True)).to_be_visible()
                expect(page.get_by_text("confirmada:", exact=False)).to_be_visible()
                page.get_by_role("button", name="mes", exact=True).click()
                expect(page.get_by_role("heading", name="Citas por estado · este mes")).to_be_visible()
                count += 1

                page.goto(base + "/admin/productos")
                page.get_by_role("button", name="Editar", exact=True).first.click()
                page.locator("input[name=minimo]").fill("4")
                page.get_by_role("button", name="Guardar producto", exact=True).click()
                expect(page.get_by_role("heading", name="Editar producto", exact=True)).to_have_count(0)
                assert any(method == "PATCH" and json.loads(body)["stock_minimo"] == 4 for method, path, body in requests if path == "/admin/productos/1")
                count += 1

                page.goto(base + "/admin/inventario")
                expect(page.get_by_text("EXISTENCIAS POR UNIDAD", exact=True)).to_be_visible()
                expect(page.get_by_text("2 unidad · 0.25 kg", exact=True)).to_be_visible()
                page.get_by_text("Solo bajo stock", exact=True).click()
                expect(page.locator("tbody").first.get_by_text("Alimento al peso", exact=True)).to_have_count(0)
                count += 1

                page.goto(base + "/admin/auditoria")
                expect(page.get_by_text("productos #1", exact=True)).to_be_visible()
                page.get_by_text("Ver antes / después", exact=True).click()
                expect(page.locator("pre")).to_contain_text('"antes": 1')
                page.locator("input[name=user]").fill("4")
                page.locator("select[name=entity]").select_option("productos")
                page.get_by_role("button", name="Consultar", exact=True).click()
                expect(page.get_by_text("productos #1", exact=True)).to_be_visible()
                count += 1

                page.goto(base + "/admin/recepciones")
                expect(page.get_by_text("Vencido · no vendible", exact=True)).to_be_visible()
                page.locator("select[name=supplier]").select_option(label="Proveedor")
                page.locator("input[name=document]").fill("FACT-UI")
                article = page.get_by_role("group", name="Artículo 1", exact=True)
                article.locator("select").nth(0).select_option(label="Medicina (unidad)")
                article.get_by_label("Lote", exact=True).fill("LOTE-UI")
                expect(page.get_by_role("button", name="Registrar recepción", exact=True)).to_be_disabled()
                article.locator("input[type=date]").fill((dt.date.today() + dt.timedelta(days=90)).isoformat())
                page.get_by_role("button", name="Registrar recepción", exact=True).click()
                expect(page.get_by_text("Recepción registrada. Existencias, lotes y egreso actualizados.", exact=True)).to_be_visible()
                count += 1

                article.locator("select").nth(0).select_option(label="Alimento al peso (kg)")
                article.locator("select").nth(1).select_option(label="Gramo (g)")
                article.locator("input[type=number]").nth(0).fill("500")
                expect(page.get_by_text("Ingreso: 0.5 kg.", exact=True)).to_be_visible()
                page.locator("input[name=code]").fill("litro")
                page.locator("input[name=name]").fill("Litro")
                page.locator("select[name=dimension]").select_option("volumen")
                page.locator("input[name=factor]").fill("1000")
                page.get_by_role("button", name="Crear unidad", exact=True).click()
                expect(page.get_by_text("Unidad creada; ya puede asignarse desde Productos.", exact=True)).to_be_visible()
                assert not errors, errors
                count += 1
                print(f"OK: 6 recorridos, viewport {viewport['width']}x{viewport['height']}; sin errores JavaScript")
                context.close()
            browser.close()
    finally:
        server.shutdown(); server.server_close()
    print(f"TOTAL: {count} comprobaciones de interfaz aprobadas con API controlada")


if __name__ == "__main__":
    run()
