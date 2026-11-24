"""Catálogo en Edge con FastAPI/JWT reales y SQLite aislada; nunca conecta a Neon.

Primero compilar frontend. Ejecutar desde raíz con backend/.venv/Scripts/python.exe.
Solo se puentea el transporte del navegador a TestClient; no hay respuestas de negocio simuladas.
"""
from functools import partial
from decimal import Decimal
from http.server import ThreadingHTTPServer
from pathlib import Path
import json
import os
import sys
import tempfile
from threading import Thread
from urllib.parse import urlsplit
import datetime as dt

# Evitar incluso la creación de un engine remoto en este proceso de pruebas.
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['SECRET_KEY'] = 'catalog-ui-isolated-tests-only'
os.environ['DEBUG'] = 'false'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))

import pytest
from playwright.sync_api import expect, sync_playwright
from sqlalchemy import select

from check_five_stories_ui import ASSETS, Handler
from test_admin_clinical_flows import clinic
from app.main import app
from app.models.clinic import Producto, Proveedor
from app.security import create_access_token, get_current_active_user
from app.services.veterinary_catalog_data import load_catalog
from app.services.veterinary_catalog_import import import_catalog


@pytest.mark.parametrize('width,height', [(1440, 1000), (390, 844)])
def test_catalog_in_browser(clinic, width, height):
    http, db, *_ = clinic
    assert (ASSETS / 'index.html').is_file(), 'Primero ejecuta npm run build'
    import_catalog(db, load_catalog())
    db.add(Proveedor(id=1, razon_social='Proveedor exclusivamente de prueba'))
    db.commit()
    products = {p.catalogo_origen['codigo']: p for p in db.scalars(select(Producto)).all()}
    app.dependency_overrides.pop(get_current_active_user, None)
    token = create_access_token(4)
    headers = {'Authorization': 'Bearer ' + token}
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(ASSETS)))
    Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    errors = []
    screenshots = Path(tempfile.gettempdir()) / 'opencode'
    screenshots.mkdir(exist_ok=True)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel='msedge', headless=True)

            def session(admin=False):
                context = browser.new_context(viewport={'width': width, 'height': height})
                if admin:
                    context.add_init_script(f"localStorage.setItem('clinic_access_token', {json.dumps(token)})")
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))

                def bridge(route):
                    request = route.request
                    parsed = urlsplit(request.url)
                    if request.resource_type in ('xhr', 'fetch') and parsed.hostname in ('localhost', '127.0.0.1'):
                        path = parsed.path + ('?' + parsed.query if parsed.query else '')
                        forwarded = {key: value for key, value in request.headers.items() if key in ('authorization', 'content-type', 'x-sucursal-id')}
                        response = http.request(request.method, path, headers=forwarded, content=request.post_data_buffer)
                        route.fulfill(status=response.status_code, headers={**response.headers, 'access-control-allow-origin': '*'}, body=response.content)
                    elif parsed.hostname not in ('127.0.0.1', 'localhost'):
                        route.abort()  # Las fotos del catálogo son locales.
                    else:
                        route.continue_()

                page.route('**/*', bridge)
                return context, page

            context, page = session()
            page.goto(base + '/productos', wait_until='domcontentloaded')
            cards = page.locator('app-product-card')
            expect(cards).to_have_count(50)
            expect(page.get_by_text('Precio por confirmar', exact=True)).to_have_count(4)
            expect(cards.get_by_role('button', name='Agregar al carrito')).to_have_count(50)
            assert all(button.is_disabled() for button in cards.get_by_role('button', name='Agregar al carrito').all())
            page.get_by_role('searchbox', name='Buscar productos', exact=True).fill('Vetoquinol')
            expect(cards).to_have_count(1)
            expect(cards.get_by_text(products['MED-001'].nombre, exact=True)).to_be_visible()
            page.get_by_role('searchbox', name='Buscar productos', exact=True).fill('Monge Fruit')
            expect(cards).to_have_count(3)
            for image in cards.locator('img').all():
                image.scroll_into_view_if_needed()
                expect(image).to_have_js_property('complete', True)
                assert image.evaluate('(image) => image.naturalWidth > 0 && image.src.includes("/catalogo/productos/")')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(screenshots / f'catalog-commercial-{width}.png'), full_page=True)

            page.goto(base + '/farmacia', wait_until='domcontentloaded')
            expect(page.locator('app-product-card')).to_have_count(32)
            page.get_by_role('searchbox', name='Buscar en farmacia', exact=True).fill('Cardial')
            expect(page.locator('app-product-card')).to_have_count(1)
            expect(page.get_by_text('Precio por confirmar', exact=True)).to_be_visible()

            page.goto(base + f'/productos/{products["MED-002"].id}', wait_until='domcontentloaded')
            expect(page.get_by_text('Para: Especie por confirmar', exact=True)).to_be_visible()
            page.goto(base + f'/productos/{products["MED-003"].id}', wait_until='domcontentloaded')
            expect(page.get_by_text('Precio por confirmar', exact=True)).to_be_visible()
            expect(page.get_by_role('button', name='Agregar al carrito', exact=True)).to_be_disabled()

            product = products['PER-007']
            receipt = http.post('/admin/operaciones/compras', headers=headers, json={
                'proveedor_id': 1, 'documento': f'UI-CATALOGO-{width}', 'detalles': [{
                    'producto_id': product.id, 'cantidad': 3, 'costo_unitario': '6.30',
                    'lote': f'LOTE-UI-{width}', 'vencimiento': (dt.date.today() + dt.timedelta(days=365)).isoformat(),
                }],
            })
            assert receipt.status_code == 201, receipt.text
            page.goto(base + f'/productos/{product.id}', wait_until='domcontentloaded')
            expect(page.get_by_text('3 unidades disponibles', exact=True)).to_be_visible()
            page.get_by_role('button', name='Agregar al carrito', exact=True).click()
            cart = page.evaluate("JSON.parse(sessionStorage.getItem('clinic_cart_v1'))")
            assert len(cart) == 1 and cart[0]['precio'] == 9 and cart[0]['cantidad'] == 1
            # Reemplazo por recurso local también cuando falla una foto verificada.
            page.route('**/catalogo/productos/per-007.webp', lambda route: route.fulfill(status=404, body=''))
            page.reload(wait_until='domcontentloaded')
            image = page.locator('app-product-detail img')
            expect(image).to_have_attribute('src', '/catalogo/producto-sin-foto.svg')
            expect(image).to_have_js_property('complete', True)
            assert image.evaluate('(image) => image.naturalWidth > 0')
            context.close()

            context, page = session(admin=True)
            page.goto(base + '/admin/productos', wait_until='domcontentloaded')
            expect(page.locator('tbody tr')).to_have_count(50)
            missing_photos = page.get_by_role('checkbox', name='Solo productos con foto pendiente')
            missing_photos.check()
            expect(page.locator('tbody tr')).to_have_count(46)
            expect(page.locator('tbody tr').filter(has_text='VET-PER-007')).to_have_count(0)
            missing_photos.uncheck()
            expect(page.locator('tbody tr')).to_have_count(50)
            page.get_by_placeholder('Buscar por nombre, SKU o categoría').fill('VET-MED-003')
            row = page.locator('tbody tr').filter(has_text='VET-MED-003')
            expect(row).to_be_visible()
            expect(row.get_by_text('Precio por confirmar', exact=True)).to_be_visible()
            row.get_by_role('button', name='Ver', exact=True).click()
            expect(page.get_by_text('Datos de origen, no una recepción real', exact=True)).to_be_visible()
            page.get_by_role('button', name='Cerrar', exact=True).click()
            row.get_by_role('button', name='Editar', exact=True).click()
            expect(page.get_by_role('spinbutton', name='Precio de venta (vacío = por confirmar)', exact=True)).to_have_value('')
            expect(page.get_by_role('combobox', name='Proveedor', exact=True)).to_have_value('0: null')
            page.get_by_role('spinbutton', name='Precio de venta (vacío = por confirmar)', exact=True).fill('85.50')
            page.get_by_role('button', name='Guardar producto', exact=True).click()
            expect(row.get_by_text('S/ 85.50', exact=True)).to_be_visible()
            db.expire_all()
            assert db.get(Producto, products['MED-003'].id).precio_venta == Decimal('85.50')
            page.goto(base + '/admin/inventario', wait_until='domcontentloaded')
            page.get_by_placeholder('Buscar producto o SKU').fill('VET-PER-007')
            inventory_row = page.locator('tbody tr').filter(has_text='VET-PER-007').filter(has=page.get_by_role('button', name='Ajustar', exact=True))
            expect(inventory_row).to_contain_text('3 unidad')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            context.close()
            browser.close()
        assert not errors, errors
        print(f'Edge {width}x{height}: 50 productos; farmacia 32; NULL, marca, presentación, fotos locales/fallback, recepción, carrito, edición persistida e inventario; API/JWT reales y SQLite aislada; sin errores JS.')
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-q', '-s']))
