# Revisión del proyecto — 26/11/2026

Base revisada: commit `31ecbff` de `master`.

## Dictamen

El proyecto tiene una base funcional avanzada y pruebas de backend sustanciales.
Está próximo a un despliegue de validación, pero **no se considera listo para
producción con la configuración y los contenedores actuales**.

El informe Word contiene 115 historias: **96 completadas (83,5 %), 19 parciales
(16,5 %) y ninguna pendiente**. Se validaron directamente las filas del Word, no
solo el resumen Markdown. Esos estados son estados documentados de aceptación;
esta revisión no constituye una nueva aceptación individual de las 115 historias.

## Verificaciones ejecutadas en esta revisión

| Verificación | Resultado observado |
| --- | --- |
| `backend`: `python -m pytest -q -rs` usando `.venv` | **564 aprobadas, 29 omitidas, 0 fallos**, 129,94 s. |
| `frontend`: `npm run build -- --progress=false` | Correcto; paquete inicial 630,46 kB. Avisos de presupuesto de 500 kB y CommonJS. |
| `backend/scripts/check_manual_stories_ui.py` | **2 pruebas aprobadas**, Edge 1440×1000 y 390×844; API/JWT reales mediante TestClient y SQLite aislada. |
| `backend/scripts/check_fundamental_stories_ui.py` | **64 comprobaciones aprobadas**, escritorio y móvil, API controlada. |
| `backend/scripts/check_communications.py --check-smtp` | SMTP conectó y autenticó correctamente; no envió correo. Proveedor WhatsApp actual: `meta`, sin las cuatro variables Meta/webhook. |
| `python -m alembic heads` | Una cabeza: `20261124_27`. No acredita la migración aplicada en la base operativa. |
| `python -m pip check` | Sin requisitos incompatibles. |
| `docker info` | Motor Docker Desktop Linux no disponible. |

La primera recolección de pytest falló por falta de `twilio` en el entorno virtual.
Se ejecutó `pip install -r requirements.txt` y se resolvió. La dependencia ya
estaba declarada en el repositorio. La ejecución final es la de la tabla.

Las 29 omisiones requieren PostgreSQL aislado: ventas, citas, pedidos web,
respaldo/restauración, concurrencia de cuentas y otras integraciones nativas.
El repositorio documenta 593 aprobadas sobre PostgreSQL temporal en otra ejecución;
**esa cifra es evidencia histórica, no el resultado PostgreSQL revalidado aquí**.

## Historias de usuario

### Áreas con implementación y evidencia automatizada

- Cuentas: registro/verificación, login, recuperación, perfiles, permisos,
  desactivación y revocación de sesiones por versión.
- Agenda: disponibilidad, confirmación, cambios, cancelaciones, bloqueos,
  historial, calendario y ocupación.
- Clínica: atenciones, recetas, archivos, vacunas, carnet, notas privadas y
  derivaciones con autorización.
- Caja: órdenes, abonos, comprobantes, validación, ventas, anulaciones y cierres.
- Administración/inventario: productos, proveedores, recepciones, lotes,
  movimientos, valorización, reportes, sucursales y respaldo.

### Las 19 parciales documentadas

| Historias | Cierre que falta |
| --- | --- |
| HU-018 | Confirmación visual final de la galería real. |
| HU-032, HU-097 | Recepción real de recordatorios y comprobación de ambos tramos. |
| HU-036, HU-098 | Recepción de cancelación/confirmación/reprogramación correctas. |
| HU-039 | Respuesta real del propietario y registro administrativo de la referencia. |
| HU-050 | Receta PDF recibida con código de orden correcto. |
| HU-056, HU-103 | Avisos reales de vacunas, con y sin cita. |
| HU-066, HU-100 | Código/importe y seguimiento real dentro de la ventana vigente. |
| HU-067 | Archivo real recibido por WhatsApp, cargado y validado una sola vez. |
| HU-099 | Bienvenida real enviada al cliente. |
| HU-101 | Confirmación y boleta PDF reales tras pago total. |
| HU-104 | Texto personalizado recibido y aprobado. |
| HU-105, HU-106 | Avisos reales al profesional correcto. |
| HU-107 | Enlace recibido y resultado accesible como propietario autenticado. |
| HU-108 | Enlace recibido, respuesta persistida y rechazo del segundo uso. |

Los recorridos están en `backend/PRUEBAS_WHATSAPP_BOTONES.md`. El alcance vigente
E35 es **envío humano por botones**, no entrega automática. Preparar un mensaje,
abrir WhatsApp o marcar `gestionado_manual` no prueba recepción.

### Discrepancia adicional a resolver

HU-012 sigue marcada como completada y su descripción en el Word pide
descripción, duración y precio referencial. El detalle público actual muestra
descripción y duración, pero no precio
(`frontend/src/app/features/services/service-detail-dialog.component.ts:27`).
`data/README.md:18` documenta la decisión de ocultar precios públicos.

Debe conciliarse el requisito con esa decisión: registrar el cambio de alcance
aceptado o volver a mostrar el precio si el criterio original sigue vigente.
Las pruebas backend que verifican el precio en la API no prueban su presentación
en pantalla. No se modificaron estados del Word durante esta revisión.

## Evaluación de las pruebas backend

**Son pruebas útiles y sustanciales**, no únicamente comprobaciones de HTTP 200:

- `test_priority_stories.py` pasa por JWT, rol, permisos y sede; verifica
  idempotencia, stock y ausencia de ventas antes del pago.
- `test_manual_story_completion.py` comprueba referencias inválidas/obsoletas,
  asistencia persistida, auditoría, permisos por rol y aislamiento de sede.
- `test_whatsapp_buttons.py` comprueba textos pendientes frente al histórico,
  referencias de ambos recordatorios, enlaces y filtros contextuales.
- Las pruebas PostgreSQL incluyen atomicidad de venta/anulación, restricciones
  nativas y carreras entre emisión, reenvío y uso de desafíos de cuenta.
- Hay pruebas con SMTP local y webhooks/transporte controlados; son apropiadas
  para regresión sin depender de servicios externos.

**Límites de lo demostrado:**

1. La mayoría usa SQLite con `Base.metadata.create_all`; eso no valida por sí
   mismo las migraciones Alembic ni los bloqueos/restricciones de PostgreSQL.
2. Algunas suites históricas sustituyen el usuario autenticado; otras eliminan
   esa sustitución y ejercitan JWT real. No todas tienen el mismo alcance.
3. `tests/conftest.py` fuerza `meta` por defecto y las suites manuales cambian
   explícitamente a `manual`. Por eso una suite verde no detecta necesariamente
   un proveedor mal seleccionado en el `.env` operativo.
4. Los recorridos Edge integrados redirigen las peticiones a TestClient; no
   prueban la red, TLS, CORS o el proxy de un despliegue real.
5. No se midió cobertura de líneas/ramas ni carga. El número de casos no equivale
   a un porcentaje de cobertura o a garantía de concurrencia de todo el sistema.
6. No se encontró configuración CI versionada para exigir estas verificaciones
   en cada cambio. `ng test` está declarado, pero Angular no tiene un target
   `test` configurado; las comprobaciones visuales existentes son scripts Python.

## Bloqueos y trabajo de despliegue

### Prioridad alta

1. **Alinear WhatsApp con E35.** El entorno actual resuelve
   `WHATSAPP_PROVIDER=meta`. Las bandejas y acciones manuales devuelven 409 fuera
   de `manual` (`backend/app/services/manual_message_service.py:22-24,39-41`).
   Configurar `manual` y reiniciar antes de aceptar las 18 historias. Meta no
   requiere credenciales si se conserva exclusivamente el alcance manual.
2. **Crear empaquetado de producción.** `compose.yaml` y `compose.neon.yaml`
   usan `uvicorn --reload` y montajes del código. El Dockerfile frontend ejecuta
   `ng serve`. Preparar imagen con build Angular y servidor de estáticos/proxy,
   o empaquetar los estáticos junto a FastAPI con la ruta esperada. La imagen
   backend actual copia solo `backend`; no incluye el `frontend/dist/browser`
   que busca `frontend_service.py:8`.
3. **Configurar dominio, HTTPS y rutas.** `environment.prod.ts` espera mismo
   origen o configuración runtime. Si hay dominios separados, CORS solo admite
   localhost en `backend/app/main.py:25`. El entorno actual mantiene
   `FRONTEND_URL` y `BOOKING_URL` en localhost: los enlaces no sirven desde el
   teléfono de un destinatario externo.
4. **Desactivar log SQL detallado.** El entorno actual tiene `DEBUG=True`, y
   `database.py:23` lo utiliza como `echo` de SQLAlchemy. Establecer `DEBUG=false`
   en producción para no registrar consultas/parámetros de datos operativos.
5. **Completar validación PostgreSQL.** Iniciar Docker Desktop y ejecutar desde
   la raíz ` .\backend\.venv\Scripts\python.exe backend/scripts/test_postgres.py --all --port 55433`.
   Después verificar/aplicar `alembic upgrade head` en el destino con respaldo
   y procedimiento de recuperación. La base operativa no se migró en esta auditoría.
6. **Persistencia y operación.** Definir almacenamiento persistente para
   `uploads` y `clinical_private`, además de PostgreSQL. Ejecutar el worker como
   proceso/servicio supervisado separado; `compose.yaml` no lo arranca y
   `compose.neon.yaml` lo deja en segundo plano junto al servidor.
7. **Datos iniciales reales.** `data/README.md` registra 724 unidades estimadas
   de demostración y vencimientos de ejemplo en el entorno documentado. Antes
   de vender con inventario real, conciliar existencias, costos y vencimientos.
   Subir código no reproduce automáticamente fotos, configuración ni datos de BD.

### Mejoras operativas antes de ampliar uso

- Respaldos programados con retención externa y ensayo de recuperación completa
  de base y archivos. El respaldo implementado es manual; la comprobación de
  interfaz no reemplaza una restauración operativa.
- Readiness de base de datos y supervisión del worker. `/health` devuelve
  `{"status":"ok"}` sin consultar BD ni comprobar el worker.
- Automatizar suite PostgreSQL y compilación en CI; completar la aceptación
  manual y el recorrido en el dominio definitivo.
- Reducir el paquete inicial y revisar las dependencias CommonJS. Los avisos
  actuales no impidieron compilar y no son el bloqueo principal.

## Secuencia recomendada

1. Corregir proveedor y configuración de destino.
2. Revalidar las 593 pruebas con PostgreSQL aislado.
3. Preparar imagen/proxy, persistencia y worker de producción.
4. Publicar un entorno de validación con HTTPS y datos de prueba.
5. Ejecutar la matriz de 18 WhatsApp, galería y discrepancia HU-012; registrar
   resultados y actualizar únicamente las historias aceptadas.
6. Verificar registro/recuperación con correo real y flujo completo
   cita → atención → receta → orden → pago → stock/caja en el destino.
7. Conciliar datos reales y comprobar recuperación antes de abrir producción.

Se actualizaron dependencias del entorno virtual y se generó este informe.
No se modificaron el código de aplicación, el `.env`, el Word ni los estados de
historias. Las pruebas usaron sus datos aislados; no se enviaron mensajes externos.
