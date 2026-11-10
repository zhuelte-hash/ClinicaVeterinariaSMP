# Compras web conectadas con caja

## 1. Análisis de la implementación anterior

- El catálogo público obtiene precios, imágenes y stock desde `/catalogo/productos`. `PublicProductsService` reconcilia el carrito con ese catálogo.
- El checkout tenía formulario, selección de Yape/Plin y vista previa, pero solo guardaba un `PedidoTemporal` y el nombre del archivo en `sessionStorage`.
- La autenticación real es `AuthService` + JWT + `/auth/me`. El checkout ahora usa esa identidad; sus rutas requieren el rol cliente mediante `clientGuard`.
- `CashierService` registra ventas físicas con bloqueo de caja y productos, idempotencia, cálculo de importes, descuento de existencias, incremento de ingresos y `ComprobanteVenta` con serie `B001`. `SalesService` permite consultar/anular esas ventas desde administración.
- Los pagos pendientes anteriores de caja pertenecen a órdenes ya asignadas a una caja y utilizan `ComprobantePagoWhatsApp`. No representan pedidos web anteriores a la venta y no se reutilizan como pedidos para evitar descontar stock anticipadamente.
- `Cliente.usuario_id` es la identidad del cliente. Los perfiles de cajero también utilizan el ID del usuario.
- Los adjuntos públicos existentes están en `/uploads`. Los comprobantes web usan almacenamiento privado independiente en PostgreSQL, sin URL pública.

## 2. Flujo implementado

1. Cliente autenticado completa el checkout con productos del catálogo.
2. Selecciona un método configurado, realiza el pago y adjunta JPG, PNG o PDF, máximo 5 MB.
3. Angular envía datos + archivo real en `multipart/form-data`. No envía precios aplicables ni estados.
4. El backend obtiene precios de productos activos, agrega cantidades repetidas, comprueba existencias, calcula importes y verifica que coincidan con el total que vio el cliente. Guarda pedido y comprobante juntos. **No genera venta ni descuenta stock.**
5. Caja o administración revisa el detalle y obtiene el comprobante mediante una petición autenticada.
6. Al aprobar, se bloquea el pedido y se utiliza la misma lógica de venta física. Caja y productos se bloquean en el mismo orden que las ventas presenciales. Se validan otra vez disponibilidad, stock y precios.
7. Venta, boleta, ingresos, stock, vínculo al pedido y datos del revisor se confirman en una sola transacción. Cualquier error revierte todo.
8. Al rechazar, se exige motivo; no se genera venta ni movimiento de inventario.
9. El cliente consulta el pedido desde **Mis compras**. Puede contactar por WhatsApp si existe un número válido configurado, usando `encodeURIComponent`.

El precio queda copiado en cada detalle. Si cambia antes de la aprobación, esta se bloquea para evitar cobrar o registrar un importe diferente al pagado: caja debe rechazar y coordinar con el cliente. No se reserva stock al registrar el pedido.

## 3. Frontend

### Creado

- `frontend/src/app/features/purchase/purchase-orders.component.ts`: listado compartido de cliente/caja/administrador, filtros, paginación, detalle, comprobante privado y revisión con confirmación y motivo.

### Modificados

- `frontend/src/app/core/services/local-purchase.service.ts`: se conserva el nombre del servicio existente; ahora consume HTTP y expone modelos tipados. Ya no guarda pedidos locales.
- `frontend/src/app/core/config/purchase.config.ts`: tipos y valores vacíos iniciales; recibe configuración pública del backend.
- `frontend/src/app/features/purchase/purchase-checkout.component.ts`
- `frontend/src/app/features/purchase/purchase-checkout.component.html`
- `frontend/src/app/features/purchase/purchase-confirmation.component.ts`
- `frontend/src/app/features/purchase/purchase-confirmation.component.html`
- `frontend/src/app/app.routes.ts`
- `frontend/src/app/components/navbar/navbar.component.ts`
- `frontend/src/app/features/cashier/cashier.routes.ts`
- `frontend/src/app/features/cashier/cashier-layout.component.ts`
- `frontend/src/app/features/admin/admin.routes.ts`
- `frontend/src/app/features/admin/layout/admin-layout.component.ts`

Rutas:

- Cliente: `/checkout`, `/compra/confirmacion?pedido=<id>`, `/mis-compras`.
- Cajero: `/caja/pedidos-web`.
- Administrador: `/admin/pedidos-web`.

La confirmación se recupera del backend incluso después de recargar. En `sessionStorage` solamente se guardan UUID de reintento indexados por una huella SHA-256 del contenido; no se guardan pedidos ni comprobantes. El carrito se vacía únicamente después de la respuesta exitosa.

## 4. Backend

### Creados

- `backend/app/models/purchase.py`
- `backend/app/schemas/purchase.py`
- `backend/app/services/purchase_service.py`
- `backend/app/routers/purchases.py`
- `backend/alembic/versions/20261109_22_pedidos_web.py`
- `backend/tests/test_purchase_flow_postgres.py`

### Modificados

- `backend/app/config.py`
- `backend/app/main.py`
- `backend/app/models/__init__.py`
- `backend/app/models/clinic.py`
- `backend/app/schemas/cashier.py`
- `backend/app/services/cashier_service.py`
- `backend/requirements.txt`
- `backend/.env.example`

Nuevas dependencias: Pillow para validar imágenes reales y pypdf para analizar documentos PDF.

## 5. Modelos y migración

Migración `20261109_22`, basada en `20261019_21`, con upgrade y downgrade verificados en una base local de pruebas.

Tablas en `clinica_veterinaria`:

- `pedidos_web`: código único, cliente, fecha, importes, método, estados separados, datos de contacto/entrega/facturación, observaciones, número de operación, referencia y contenido privado del comprobante, UUID y huella de solicitud, revisión, motivo y venta asociada única.
- `detalle_pedido_web`: producto, nombre e imagen copiados, cantidad, precio aplicado y subtotal.

También se agrega `ordenes_cobro.costo_delivery`, por defecto cero para las ventas existentes. La boleta API lo expone expresamente. El envío se suma al importe de la venta web, sin convertirse en una salida de inventario.

Hay restricciones de integridad para importes, cantidades, estados válidos y asociación única de la venta al pedido aprobado. El archivo es `BYTEA` y se carga de forma diferida, de modo que los listados no consultan su contenido.

## 6. Endpoints

| Método | Ruta | Acceso / finalidad |
|---|---|---|
| GET | `/pedidos-web/configuracion` | Configuración pública de cobro, sin credenciales |
| POST | `/pedidos-web` | Cliente; campos multipart `datos` (JSON) y `comprobante` |
| GET | `/pedidos-web` | Cliente: propios; caja/admin: listado; filtros `estado`, `codigo`, `fecha`, `pagina` |
| GET | `/pedidos-web/{id}` | Propietario o personal autorizado |
| GET | `/pedidos-web/{id}/comprobante` | Archivo privado autenticado, sin caché |
| POST | `/pedidos-web/{id}/revision` | Caja/admin; `accion: APROBAR/RECHAZAR`, `motivo` |

Se reutilizan la autenticación, catálogo, `CashierService._create_sale`, `OrdenCobro`, sus detalles, `ComprobanteVenta`, el listado administrativo de ventas y la consulta de boleta existente. La venta web aprobada aparece en los informes actuales de ventas y en los ingresos digitales de caja.

## 7. Caja e inventario

La navegación incorpora **Pedidos web / Pagos pendientes**. La bandeja es compartida entre cajeros: el pedido se asigna a la caja de quien lo aprueba, no a la de quien simplemente lo consulta. El cajero debe tener caja abierta. Para administradores se reutiliza el comportamiento existente de ventas administrativas, que crea su caja cuando corresponde.

Los filtros incluyen pendientes, aprobados, rechazados, cancelados, fecha local de Lima y código. Cada detalle muestra contacto, DNI/RUC, entrega, observaciones, productos, importes, método, operación, comprobante, estados y datos de revisión.

Se conserva el comportamiento por defecto de `create_sale` para ventas presenciales. La variante interna sin commit permite que el pedido controle la transacción completa. El stock continúa descontándose exclusivamente en el código existente de caja.

## 8. Seguridad y estados

- JWT y roles existentes. Un cliente no puede crear pedidos con otra identidad ni asignar precios o estados.
- Un pedido/comprobante ajeno responde 404 al cliente.
- Administración respeta `ventas.puede_ver` y `ventas.puede_aprobar` de la matriz existente. Se preserva su comportamiento de acceso administrativo cuando aún no existe una fila configurada.
- Solo `PENDIENTE` puede pasar a `APROBADO` o `RECHAZADO`. Los estados terminales no pueden aprobarse de nuevo. No hay endpoint de edición arbitraria de estados.
- `CANCELADO` queda reservado en el esquema; no se ha habilitado una cancelación por cliente sin reglas comerciales definidas.
- UUID único y hash de datos + archivo permiten reintentos y detectan la reutilización de una clave con otro contenido.
- Bloqueo de fila del pedido y unicidad de venta protegen las confirmaciones simultáneas.
- Archivos con nombres generados en el servidor. Se valida contenido real, no la extensión ni el MIME del navegador. PDFs cifrados, inválidos o con acciones/anotaciones se rechazan.
- Los comprobantes no se publican bajo `/uploads`. El endpoint privado usa `Cache-Control: private, no-store`, `nosniff` y nombre seguro. Angular los muestra como Blob y revoca la URL al cerrar.

## 9. Configuración pendiente

Completar en `backend/.env` o en las variables del despliegue, según `backend/.env.example`:

```dotenv
PURCHASE_WHATSAPP_NUMBER=
PURCHASE_DELIVERY_COST=10.00
PURCHASE_YAPE_HOLDER=
PURCHASE_YAPE_PHONE=
PURCHASE_YAPE_QR_URL=
PURCHASE_PLIN_HOLDER=
PURCHASE_PLIN_PHONE=
PURCHASE_PLIN_QR_URL=
```

- QR: URL HTTPS oficial o ruta del archivo público del frontend, por ejemplo una ruta propia una vez que exista el archivo real.
- Cada método se habilita únicamente al tener titular, teléfono/cuenta y QR.
- WhatsApp debe incluir código de país, sin `+` ni espacios. El botón de consulta del pedido se oculta si está vacío o es inválido. El botón flotante preexistente tiene otro número hardcodeado: verificar con la clínica cuál es el oficial antes de completar la nueva configuración.
- El delivery conserva el importe previo de S/ 10.00, ahora calculado desde backend. Confirmar la tarifa real antes de publicar.
- No se inventaron datos de pago y no se configuró envío automático por WhatsApp.
- Se eligieron variables de despliegue porque los módulos actuales no tienen persistencia de configuración de cobro. No se añadió una pantalla administrativa que aparente guardar datos sin persistencia.
- La solicitud de factura se conserva como datos del pedido; la emisión usa el mecanismo interno de comprobantes existente. Esto no agrega integración fiscal/SUNAT.

Tras modificar variables, recrear el backend para que Docker vuelva a cargar `env_file`.

## 10. Entornos y hallazgo de Neon

El contenedor encendido al iniciar apuntaba a Neon y esa base reportaba `20261019_22`, revisión que no existe en este repositorio. El primer intento de Alembic se detuvo sin aplicar la nueva migración. **No se alteró ni se marcó artificialmente el historial de Neon.**

Se dejó el backend conectado al PostgreSQL local definido por `compose.yaml`, con migración aplicada hasta `20261109_22`. El frontend existente sigue activo en Docker. Las pruebas de concurrencia y persistencia se ejecutan en otra base local, `test_web_purchase`.

Para desplegar en Neon se debe recuperar y revisar la migración faltante y reconciliar su cadena de revisiones con la de este repositorio antes de ejecutar `upgrade head`. No usar `alembic stamp` para ocultar la discrepancia. La implementación de pedidos y almacenamiento es compatible con PostgreSQL/Neon, pero la migración en esa base concreta queda bloqueada por su historial previo.

## 11. Verificaciones

- Suite backend completa con `TEST_DATABASE_URL`: **36 aprobadas, 1 omitida**.
- La omitida es la prueba existente de citas que exige `TEST_APPOINTMENT_DATABASE_URL` y un host de prueba específico. No se simuló su ejecución.
- Pruebas nuevas: creación y reintento, comprobante real, consulta de caja, aprobación/venta única, rechazo/motivo, permisos y propiedad, importes manipulados, archivos inválidos/grandes, stock agotado, precio cambiado, rollback después de crear venta/boleta, confirmaciones simultáneas, reintentos simultáneos, competencia de dos pedidos por las últimas existencias, delivery, caja cerrada, permisos administrativos, PDF y JPEG.
- Prueba previa de venta presencial, reintento y anulación aprobada.
- Migración completa desde una BD vacía y downgrade/upgrade de la nueva revisión aprobados en la BD de pruebas.
- `npm run build`: aprobado. Hay advertencias del módulo veterinario, dependencias CommonJS de PDF y presupuesto inicial de bundle; no bloquean el build.
- `npm test`: no puede ejecutar pruebas porque `angular.json` no define un objetivo `test` (`Cannot determine project or target for command`). No se presenta como éxito.
- Frontend HTTP 200, backend `/health` HTTP 200 y configuración pública respondiendo.
- No se ejecutó una prueba automatizada de navegador del recorrido visual completo ni una operación bancaria real. La integración HTTP y las transacciones se verificaron con FastAPI TestClient y PostgreSQL real.

## 12. Comandos

Desde la raíz, para backend + PostgreSQL local:

```powershell
docker compose -f compose.yaml up -d --build database backend
docker compose -f compose.yaml exec backend alembic upgrade head
docker compose -f compose.yaml exec backend alembic current
```

El frontend ya encendido sigue en `http://localhost:4200`. Para ejecutarlo sin ese contenedor, liberar antes el puerto 4200 y, desde `frontend/`:

```powershell
npm ci
npm start -- --host 0.0.0.0
```

Base aislada de pruebas (crear una sola vez):

```powershell
docker compose -f compose.yaml exec database psql -U postgres -d postgres -c "CREATE DATABASE test_web_purchase;"
docker compose -f compose.yaml exec -e DATABASE_URL=postgresql://postgres:postgres@database:5432/test_web_purchase backend alembic upgrade head
docker compose -f compose.yaml exec -e TEST_DATABASE_URL=postgresql://postgres:postgres@database:5432/test_web_purchase backend python -m pytest -q
```

Build frontend desde `frontend/`:

```powershell
npm run build
```

Neon, únicamente después de reconciliar la migración faltante y configurar sus variables:

```powershell
docker compose -f compose.neon.yaml build backend
docker compose -f compose.neon.yaml run --rm backend alembic upgrade head
docker compose -f compose.neon.yaml up -d --build
```
