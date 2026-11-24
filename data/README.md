# Catálogo comercial veterinario: integración y operación

## Estado actual — cierre del 24/11/2026

- Catálogo activo: **47 productos `VET-`, todos con imagen asignada**.
- Se desactivaron 32 productos de ejemplo, «jabon» (SKU `355`), `VET-MED-013`,
  `VET-ACC-001` y `VET-ACC-002`, conservando sus referencias históricas.
  Registro: `productos_desactivados_20261124.json`.
- A solicitud del usuario se cargaron **724 unidades estimadas** para los 47
  productos, con mínimos, lotes y movimientos consistentes. Las existencias están
  marcadas como demostración; los vencimientos asignados son de ejemplo. Esta carga
  no representa una compra ni un conteo físico. Detalle: `stock_estimado_20261124.json`.
- Las imágenes proporcionadas se descargaron como WEBP locales; fuentes en
  `fotografias_manuales.json` y los archivos `fotos_usuario_20261124*.json`.
- Administración → Productos permite pegar y guardar URL directamente y filtrar
  fotos pendientes. El header muestra las opciones personales solo a clientes
  autenticados; Contacto usa fotos reales y el footer contiene el mapa de ubicación.
- La sección pública de servicios muestra información sin precios referenciales.
- La migración `20261124_27` y la carga inicial del catálogo ya se aplicaron en el
  entorno configurado. Los registros siguientes documentan etapas anteriores.

### Reproducción de las operaciones posteriores

Desde la raíz, con el entorno y la base configurados:

```powershell
# Importa las imágenes proporcionadas; conserva las fuentes y las copias locales.
.\backend\.venv\Scripts\python.exe backend/scripts/set_catalog_photo.py --batch data/fotos_usuario_20261124.json
.\backend\.venv\Scripts\python.exe backend/scripts/set_catalog_photo.py --batch data/fotos_usuario_20261124_lote2.json
# Vista previa; --apply desactiva únicamente los SKU documentados.
.\backend\.venv\Scripts\python.exe backend/scripts/clean_demo_catalog.py
# Vista previa; --apply carga una sola vez el stock estimado de los 47 activos.
.\backend\.venv\Scripts\python.exe backend/scripts/populate_estimated_stock.py
```

Las modificaciones de datos ya realizadas residen en la base del entorno; subir
el código a Git no ejecuta estas operaciones en otra base automáticamente.

## Registro histórico de la integración

## Revisión de fotos posterior — 24/11/2026

Se recuperaron y asociaron también `VET-ACC-003` (Juguete Pulpo) y `VET-ACC-005`
(Plato Cara de Gato). Se agregó después Aurizon 20 ml (`VET-MED-001`) con la URL
de ConVet proporcionada por el usuario, registrada en `fotografias_manuales.json`.
También se agregaron las fotos proporcionadas para Cardial, Prednisolona,
Cefavet, Apoquel y Antalvet 100 ml. El estado actual es **33 de los 50 productos
VET con foto y 17 pendientes**. Las candidatas recibidas para Broncopet,
Dolordog y Antalvet 50 ml difieren de la presentación registrada; véase
`fotos_recibidas_medicamentos.json`.
Administración → Productos incluye el filtro de foto pendiente.
La lista completa, las instrucciones de carga y el traslado de archivos están en
[GUIA_FOTOS.md](GUIA_FOTOS.md); la comprobación pública está en
`informe_imagenes.json`. Las cifras siguientes corresponden a la revisión anterior.

## Actualización operativa — 24/11/2026

La base configurada ya tiene los **50 SKU `VET-`**: se conservaron el producto
inicial y sus datos y se importaron los 49 restantes sin existencias ficticias.
Se comprobó la migración `20261124_27` aplicada antes de la carga.

Después se recuperaron y asociaron **21 fotografías adicionales**, además de las
4 verificadas inicialmente: **25 productos con foto y 25 pendientes**.
Las nuevas fotografías provienen de los enlaces entregados o de imágenes cuyo
nombre coincide con el catálogo en la misma tienda (incluidos cuatro cambios de
título revisados). Esto no acredita visualmente el peso/volumen de cada envase;
se conserva ese alcance en `catalogo_origen.fotografia_recuperada` y en
`fotografias_recuperadas.json`, con las fuentes y la lista pendiente.
NexGard ANT-005 se excluye por diferencia entre el rango de peso del envase y el
registro. Villarán devuelve HTTP 500; otros listados no ofrecen coincidencias.

Para repetir la recuperación desde `backend` (descarga archivos y genera informe):

```powershell
.\.venv\Scripts\python.exe scripts/recover_catalog_photos.py
# Asociar fotos a productos existentes; conserva imágenes personalizadas:
.\.venv\Scripts\python.exe scripts/recover_catalog_photos.py --apply --allow-remote
```

Para completar una foto manualmente: **Administración → Productos → Editar →
Imagen del producto → Subir imagen → Guardar**. Admite JPG, PNG y WEBP hasta 5 MB.
Las copias recuperadas se sirven desde `frontend/public/catalogo/productos/`.
Las cifras y referencias a no haber ejecutado la carga que siguen documentan
el estado de la entrega inicial, anterior a esta actualización.

## Estado de la entrega

Implementado y probado localmente. **No se ejecutaron migraciones ni importaciones
en Neon.** La nueva versión del backend necesita la migración `20261124_27` antes
de atender consultas de productos contra una base existente. Coordinar migración,
despliegue del backend y frontend e importación; no reiniciar esta versión contra
un esquema anterior esperando que la carga ocurra automáticamente.

Los datos de origen se conservan en JSON, CSV y HTML. Angular usa FastAPI y la
tabla existente `clinica_veterinaria.productos`, no el HTML ni un catálogo mock.

## Datos y correspondencia

- 50 registros: 15 medicamentos, 10 alimentos caninos, 8 felinos, 7
  antiparasitarios, 5 de higiene y 5 accesorios.
- Los cuatro precios desconocidos de MED-003, MED-011, MED-012 y MED-013 siguen
  siendo `NULL`. Se muestran como «Precio por confirmar» y no se admiten en venta,
  pedido web, orden de cobro o carrito.
- Las marcas desconocidas y el proveedor no confirmado se guardan como `NULL`.
  Una tienda consultada no se convierte en proveedor de la clínica.
- La especie «Por confirmar» se conserva como desconocida en el origen y no se
  interpreta como aptitud para todas las especies.
- Los 50 stocks de origen son ficticios. Los vencimientos ficticios y precios de
  compra estimados no generan lotes, costos contables ni compras reales.
- Los precios de venta conservan la clasificación de la fuente: publicada,
  histórica o no disponible. No constituyen confirmación de una tarifa vigente de
  la clínica. Administración puede confirmar/corregir los precios operativos.

### SKU sin colisiones con productos anteriores

Las migraciones antiguas ya crean productos con códigos como HIG-001 (shampoo
500 ml) y ACC-001 (correa), distintos de los de este archivo. Los nuevos SKU son
**`VET-<codigo>`**, por ejemplo `VET-HIG-001`. El código original se conserva en
`productos.catalogo_origen.codigo`. El prefijo es parte de la identidad estable
del seed: no cambiarlo después de cargar.

La carga repetida omite los SKU ya registrados: no restablece precios, imágenes,
stock, proveedor, datos de origen ni estado activo. Si un SKU pertenece a otra
sede, la transacción se rechaza. Los SKU siguen siendo únicos globalmente; no se
crea una estructura paralela de existencias por sede.

### Tablas reutilizadas

| Origen | Destino |
| --- | --- |
| código | `productos.sku` con prefijo `VET-` y código original en metadatos |
| nombre, marca, presentación, descripción, subcategoría | Campos de `productos` |
| categoría | FK a `categorias_producto` |
| especie confirmada | `productos.especies` |
| precio de venta conocido | `productos.precio_venta`, `NUMERIC(12,2)` |
| compra estimada, fuente, fecha de consulta y demás indicadores | `productos.catalogo_origen` |
| foto verificada | `productos.imagen_url` hacia recurso local del frontend |
| stock ficticio / vencimiento ficticio | Metadatos de origen; modo demo aislado opcional |
| recepción real posterior | `compras_proveedor`, `lotes_inventario`, `movimientos_inventario`, `egresos` |
| venta y devolución | `ordenes_cobro`, `detalles_orden_cobro` y movimientos existentes |

Categorías operativas: medicamentos y antiparasitarios → Medicamentos veterinarios;
alimentos → Alimentos; dietas veterinarias → Alimento medicado; higiene → Higiene
y cuidado; accesorios → Accesorios. Se reutilizan categorías coincidentes sin
renombrar las anteriores; una coincidencia ambigua detiene la carga. La categoría
original queda en metadatos. Farmacia reutiliza estas categorías (32 de los 50
productos corresponden a sus grupos actuales).

La unidad es **unidad comercial no fraccionable**: una bolsa de 3 kg cuenta como
una bolsa, no como tres unidades ni venta a granel. Medicamentos, alimentos,
antiparasitarios y champús requieren vencimiento en la recepción.

El costo operativo inicial es **0 porque no se recibió inventario**, no una
sustitución del precio de compra desconocido. El precio de compra del catálogo
permanece separado, con `NULL` o su valor y la marca de estimación. El costo
promedio operativo se establece con recepciones reales.

## Fotografías

Se descargaron y revisaron visualmente las nueve candidatas. Solo cuatro tienen
coincidencia verificable de producto y presentación:

| Código original | Comprobación visual |
| --- | --- |
| PER-007 | Monge Fruit pato/naranja, 100 g |
| PER-008 | Monge Fruit cerdo/piña, 100 g |
| PER-009 | Monge Fruit salmón/pera, 100 g |
| HIG-001 | Drag Pharma Petever Forte, clorhexidina 3 %, 150 mL |

Las otras cinco (PER-006, GAT-004, GAT-007, GAT-008 y HIG-002) no permiten confirmar
visualmente el peso/volumen exacto; se conservan sus URL como candidatas, pero no
se publican como verificadas. En total **46 productos usan la imagen local de
reemplazo**, sin asociar fotos de otra presentación.

Manifiesto: `fotografias_verificadas.json`. Copias WEBP:
`frontend/public/catalogo/productos/`. Reemplazo:
`frontend/public/catalogo/producto-sin-foto.svg`. La web no necesita acceder a las
tiendas externas para mostrar estas imágenes. El manifiesto registra la fuente y
el alcance de la comprobación visual, no una autorización adicional del proveedor.

Para revisar nuevas candidatas, desde `backend`, indicar una carpeta local de
trabajo existente o su subcarpeta:

```powershell
.\.venv\Scripts\python.exe scripts/download_catalog_photo_candidates.py --output "C:\Users\salza\AppData\Local\Temp\opencode\catalogo-candidatas"
```

Descargar no verifica automáticamente una foto. Tras revisión y actualización del
manifiesto, regenerar solo las aprobadas:

```powershell
.\.venv\Scripts\python.exe scripts/download_catalog_photo_candidates.py --output ../frontend/public/catalogo/productos --verified-only
```

## Comandos sin conexión

Desde `backend`:

```powershell
# Contrasta JSON, CSV y fotografías. No lee .env ni abre conexiones.
.\.venv\Scripts\python.exe scripts/seed_veterinary_products.py

# Regenera el SQL de la misma fuente normalizada. No lo ejecuta.
.\.venv\Scripts\python.exe scripts/seed_veterinary_products.py --export-sql ../data/importar_productos_neon.sql
```

El SQL exportado corresponde a la sede 1. Se puede generar para otra sede con
`--sucursal-id ID`. No crea tablas ni tipos, requiere la migración y conserva
registros existentes. Serializa cargas/altas concurrentes mediante bloqueo de las
tablas de categorías/productos dentro de la transacción.

## Preparación de Neon: solo con autorización posterior

Los siguientes comandos están **documentados, no ejecutados en Neon**. Utilizan la
configuración local sin imprimir su URL ni credenciales.

1. Aplicar la migración y desplegar frontend/backend coordinadamente:

   ```powershell
   .\.venv\Scripts\python.exe -m alembic upgrade head
   ```

2. Previsualizar el catálogo frente a la base ya migrada:

   ```powershell
   .\.venv\Scripts\python.exe scripts/seed_veterinary_products.py --dry-run --sucursal-id 1
   ```

   Usa `SET TRANSACTION READ ONLY`: consulta SKU y sede, no inserta y no consume
   secuencias. Informa productos por insertar, conservados y conflictos.

3. Cuando el propietario autorice expresamente la carga remota:

   ```powershell
   .\.venv\Scripts\python.exe scripts/seed_veterinary_products.py --apply --allow-remote --sucursal-id 1
   ```

   Inserta solo productos ausentes, con proveedor pendiente y **stock operativo
   cero**. Usa una transacción y registra auditoría. El stock mínimo de origen se
   toma como umbral sugerido de configuración, editable desde Administración.

4. Registrar proveedor, costo, lote, cantidad y vencimiento reales en Recepciones.
   Nunca usar las cantidades del archivo como evidencia de mercadería recibida.

Alternativamente puede revisarse y ejecutarse `importar_productos_neon.sql` en una
sesión autorizada, después de migrar. No ejecutar el SQL inicial
`02_esquema_bd_modelo_clases.sql` encima de una base existente. El seed no hace
actualizaciones automáticas; cambios posteriores se realizan desde Administración.

## Demostración y pruebas

`--demo --apply` solo permite PostgreSQL en `localhost`, `127.0.0.1` o `database`,
con nombre de base `test_*`. Está bloqueado en Neon. Genera productos marcados con
`es_demostracion`, lotes `DEMO-*`, movimientos de ingreso con referencia y costo
estimado de demostración, sin inventar compras ni egresos. Repetirlo no repone el
stock vendido. Las tarjetas y administración identifican las existencias demo.

Comandos de verificación desde la raíz:

```powershell
.\backend\.venv\Scripts\python.exe backend/scripts/test_postgres.py --all
```

Desde `frontend`: `npm run build`. Después, desde la raíz:

```powershell
.\backend\.venv\Scripts\python.exe backend/scripts/check_veterinary_catalog_ui.py
```

### Evidencia local de esta entrega

- Suite completa: **433 aprobadas, cero fallos y cero omitidas** (156,22 s).
  PostgreSQL temporal Docker con migraciones hasta `20261124_27`; contenedor/red
  eliminados al terminar. Incluye 12 casos nuevos de catálogo y 5 nativos:
  idempotencia, SQL equivalente, modo demo, solo lectura y concurrencia. Las pruebas
  SQLite conservan su aislamiento; no se presentan como integraciones nativas.
- Se verificó recepción con vencimiento obligatorio, venta y devolución de un
  medicamento importado, Kardex, costo real separado de referencia, rechazo de
  compras/ventas/órdenes sin precio y conservación de registros previos.
- Angular compilado: **627,63 kB** iniciales; avisos existentes de presupuesto
  inicial y dependencias CommonJS.
- **Dos recorridos integrados Edge**, 1440×1000 y 390×844, contra FastAPI/JWT
  reales mediante TestClient y SQLite aislada. Sin respuestas de negocio simuladas:
  50 productos, farmacia con 32, filtros, cuatro precios pendientes, especie por
  confirmar, fotos locales, fallback ante fallo de imagen, recepción, carrito,
  edición persistida e inventario. Sin errores JavaScript ni desbordamiento.
- Capturas en la carpeta temporal `opencode`, no en el repositorio.
- **Ninguna migración ni importación ejecutada en Neon.**
