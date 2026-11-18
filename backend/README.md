# Ejecución y comprobación del backend

Ejecuta los comandos de PowerShell desde `backend`.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe run.py
```

API: <http://localhost:8000/docs>. Estado del servidor: <http://localhost:8000/health>.

## Correo de verificación y recuperación

Para la preparación acordada con **Gmail, una conexión Meta existente y ejecución local**, sigue [GUIA_GMAIL_META.md](GUIA_GMAIL_META.md): parámetros SMTP, once plantillas con textos/variables, webhook HTTPS y los quince recorridos de aceptación externa.

Completa estas variables en el archivo existente `backend/.env` con los datos del proveedor de correo. Las opciones también están en `.env.example`.

```dotenv
SMTP_HOST=smtp.tu-proveedor.com
SMTP_PORT=587
SMTP_USERNAME=correo-de-la-clinica@tu-dominio.com
SMTP_PASSWORD=clave-smtp-del-proveedor
SMTP_STARTTLS=true
SMTP_SSL=false
MAIL_FROM=correo-de-la-clinica@tu-dominio.com
FRONTEND_URL=http://localhost:4200
```

Para un proveedor que use TLS implícito en el puerto 465, establece `SMTP_PORT=465`, `SMTP_SSL=true` y `SMTP_STARTTLS=false`. Reinicia la API después de cambiar `.env`.

- El registro solicita un código de seis dígitos, válido durante 15 minutos. La cuenta permite iniciar sesión después de verificarlo.
- El reenvío está disponible después de un minuto y sustituye los códigos anteriores. Cinco códigos incorrectos invalidan el desafío.
- La recuperación envía un enlace válido durante una hora y de un solo uso. Al restablecer la contraseña se invalidan las sesiones anteriores.
- La API intenta el primer envío en segundo plano después de guardar el mensaje. Si falta SMTP, responde HTTP 503 antes de crear una cuenta nueva. Los fallos del proveedor conservan el mensaje para reintento.

Para procesar reintentos y automatizaciones, abre otra terminal en `backend`:

```powershell
.\.venv\Scripts\python.exe -m app.tasks.appointment_worker
```

## Cancelación y confirmación por WhatsApp

En **Reservar cita → Mis citas → Cancelar**, indica un motivo de 3 a 500 caracteres. El servidor comprueba propiedad, permisos, anticipación y que la atención no haya comenzado. La cancelación libera el horario; repetir la petición conserva la cancelación original.

La confirmación se guarda en la cola de WhatsApp. Para entregarla, configura `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN` y una plantilla aprobada para el evento `cita_cancelada` mediante `PUT /admin/operaciones/plantillas/cita_cancelada`. La plantilla debe usar las variables `nombre`, `mascota` y `motivo`. Ejecuta el worker y comprueba el registro en `GET /admin/operaciones/mensajes`.

`WHATSAPP_APP_SECRET` y `WHATSAPP_VERIFY_TOKEN` permiten verificar el webhook y recibir estados de entrega. El código de estas historias no sustituye las credenciales y plantillas del proveedor.

### Preparación de las cinco historias prioritarias

Desde `backend`, comprueba las variables sin imprimir credenciales ni enviar mensajes:

```powershell
.\.venv\Scripts\python.exe scripts/check_communications.py
.\.venv\Scripts\python.exe scripts/check_communications.py --check-smtp
```

El segundo comando también comprueba conexión, TLS y autenticación SMTP. Un resultado correcto no acredita recepción en un buzón externo. El diagnóstico termina con código 1 si faltan variables o falla la comprobación; no modifica `.env` ni la base de datos.

Configura las plantillas aprobadas mediante `PUT /admin/operaciones/plantillas/{evento}` con una cuenta administradora. `GET /admin/operaciones/plantillas` devuelve el contenido y las variables necesarias:

| Evento | Variables del cuerpo, en este orden | Encabezado |
| --- | --- | --- |
| `cita_confirmada` | `nombre`, `mascota`, `fecha` | Sin documento |
| `cita_reprogramada` | `nombre`, `mascota`, `fecha` | Sin documento |
| `cita_cancelada` | `nombre`, `mascota`, `motivo` | Sin documento |
| `receta` | `nombre`, `mascota`, `codigo` | Documento PDF |

Ejemplo para cancelación; sustituye `nombre_proveedor` e `idioma` por los aprobados en Meta:

```json
{
  "nombre_proveedor": "cita_cancelada",
  "contenido": "Hola {nombre}, la cita de {mascota} fue cancelada. Motivo: {motivo}.",
  "variables": ["nombre", "mascota", "motivo"],
  "idioma": "es_PE",
  "activa": true
}
```

- **HU-002/HU-004:** registrar una cuenta de prueba, recibir el código en un buzón externo y verificarla; solicitar recuperación, abrir el enlace recibido y comprobar la contraseña nueva y la invalidación de sesiones anteriores.
- **HU-036/HU-098:** confirmar, reprogramar y cancelar desde los roles autorizados. Cada cambio real encola su aviso, también desde administración. La aceptación del horario propuesto avisa con la fecha efectiva en Lima; editar asistencia, reasignar profesional o reenviar la misma fecha no repite la confirmación.
- **HU-050:** guardar la receta y cerrar la atención. Se genera una orden con servicio y productos vinculados y se encola la receta PDF para el teléfono de la cita, con respaldo del perfil. Una orden emitida antes del cierre se reutiliza si sus artículos/cantidades coinciden; si no coincide o está anulada, el cierre se rechaza sin persistirlo. Los importes ya emitidos se conservan. El stock no se descuenta hasta el pago validado. Un servicio gratuito con productos recetados también genera orden.
- Ejecutar el worker y revisar `GET /admin/operaciones/mensajes`. `enviado` significa aceptación por el proveedor; `entregado`/`leido` se acreditan con el webhook firmado `POST /whatsapp/webhook`. Suscribir el campo `messages` en Meta, con la URL pública HTTPS del backend y el token de verificación; la validación inicial usa `GET /whatsapp/webhook`. Las notificaciones repetidas o desordenadas no degradan un mensaje leído a entregado o fallido.
- Si un envío falla, la cola reintenta hasta cinco intentos con espera progresiva. Los mensajes que aún esperan no bloquean otros listos. Tras corregir la configuración, se puede solicitar `POST /admin/operaciones/mensajes/{id}/reintentar` con permiso de edición de usuarios.

Registrar por cada HU fecha, escenario, resultado y referencia del mensaje, sin guardar tokens ni contraseñas en el informe. Las cinco historias conservan estado **Parcial** hasta acreditar su recepción externa y todos sus criterios.

### Panel operativo de las cinco parciales prioritarias (17/11/2026)

En **Administración → Configuración → Comunicaciones de la primera entrega**:

- Consulta variables faltantes de SMTP, WhatsApp y webhook, y el formato del teléfono público de asistencia. Solo se muestran nombres de variables y presencia de configuración; no se consultan proveedores ni se exponen credenciales. Un formato válido no verifica que el teléfono sea el Business receptor.
- Prepara las plantillas `cita_cancelada` (HU-036) y `receta` (HU-050), con nombre/idioma aprobados, contenido, activación y orden de variables del cuerpo. La receta requiere encabezado PDF en Meta. Guardar aquí no crea ni aprueba plantillas en el proveedor. Se rechazan variables duplicadas y formatos/conversiones que impedirían generar el mensaje.
- Filtra los últimos 200 envíos por evento y estado para seguir HU-002/HU-004/HU-036/HU-050, consultar referencia del proveedor y solicitar reintentos. La consulta no incluye códigos, enlaces de recuperación ni documentos binarios. Las acciones requieren edición de Usuarios; el acceso de consulta conserva el seguimiento.
- Un reintento vuelve a preparar la cola para el worker. Los mensajes cancelados, enviados, entregados/leídos y correos con desafío caducado/usado se rechazan; para estos correos el cliente debe solicitar uno nuevo.
- Para HU-039, el cliente puede pulsar **«Ya envié el mensaje: actualizar asistencia»** desde Reservar cita. Consulta de nuevo al servidor; abrir WhatsApp o pulsar actualizar no registra la asistencia. Esta sigue dependiendo del webhook firmado y de un mensaje válido.

API de diagnóstico: `GET /admin/operaciones/comunicaciones/estado`. Seguimiento: `GET /admin/operaciones/mensajes?evento=receta&estado=error`. Ambas respuestas llevan `Cache-Control: private, no-store`. La configuración local no acredita entrega externa ni que el worker esté activo.

Pruebas HTTP/JWT específicas: `python -m pytest -q tests/test_communication_readiness.py` (14 casos). Recorrido visual ampliado: `python backend/scripts/check_fundamental_stories_ui.py` desde la raíz, después de compilar (34 comprobaciones en Edge, escritorio/móvil, API controlada).

### Cinco parciales adicionales: HU-067, HU-098, HU-104, HU-105 y HU-106

- **Cliente → Mis pagos → Ver detalle y pagos → Enviar comprobante por WhatsApp (HU-067):** indica monto, medio digital y operación opcional. El servidor valida propiedad, permisos, saldo, estado y teléfono de perfil; prepara una leyenda `OC-código MONTO=40.00 MEDIO=yape OPERACION=OP-1`. Abre WhatsApp, adjunta JPG/PNG/PDF de hasta 5 MB y pega la leyenda **en el mismo archivo**. Enviar solo texto no registra un abono. El teléfono público de clínica debe corresponder al Business receptor y el remitente debe ser el del perfil. Preparar el enlace no crea pagos ni descuenta stock.
- El webhook firmado valida remitente, cuenta activa y permiso de creación de Ventas. Descarga en streaming con límite efectivo de 5 MB, además del límite declarado por Meta; comprueba tipo permitido y contenido real mediante el validador de comprobantes. Rechaza importes mal formados y sobrepagos. El ID entrante evita procesar de nuevo la misma entrega. Fallos transitorios de consulta/descarga responden HTTP 503 y revierten el registro del ID para permitir reentrega. Una recepción válida conserva el comprobante privado como **enviado para revisión**; caja debe validarlo antes de actualizar saldo, caja, venta y existencias.
- **Configuración → Comunicaciones (HU-104):** el selector ahora permite mantener **todos** los eventos del catálogo, no solo cancelación/receta. Nombre del proveedor, contenido, idioma, activación y orden de variables se guardan con permiso de edición de Usuarios. Con permiso de consulta se puede leer y cambiar el evento seleccionado, sin modificar plantillas. La aprobación y correspondencia real con Meta se acreditan aparte.
- **HU-098/HU-105/HU-106:** el selector incluye confirmación/reprogramación/cancelación al cliente y reprogramación/cancelación al veterinario. Los filtros de envíos permiten seguir cada evento, referencia y estado. Verifica el teléfono del profesional en Personal. Se probaron la aceptación por cliente del horario propuesto y la cancelación administrativa: un aviso por evento/destinatario, teléfono correcto del veterinario y envío mediante transporte controlado. Las regresiones conservan la ausencia de avisos duplicados por ediciones que no cambian el estado/horario efectivo.
- **Configuración → Recepción de WhatsApp y comprobantes:** muestra los últimos 200 IDs de proveedor, remitente y resultado, sin leyenda ni archivos. `comprobante_vinculado:OC-...` indica recepción para revisión, no validación del pago. Requiere consulta de Usuarios y devuelve respuesta privada sin caché.

API nueva: `POST /operaciones/ordenes/{id}/preparar-whatsapp` con `monto`, `medio` y `codigo_operacion` opcional; `GET /admin/operaciones/mensajes-entrantes`. Pruebas nuevas: `python -m pytest -q tests/test_five_whatsapp_stories.py` (22 casos HTTP/JWT con Meta controlado). Desde la raíz, después de compilar: `python backend/scripts/check_five_whatsapp_stories_ui.py` (20 comprobaciones Edge escritorio/móvil con API controlada).

Las cinco historias mantienen **Parcial** hasta acreditar sus criterios externos: archivo recibido desde WhatsApp real, plantillas aprobadas y avisos recibidos por cliente/profesional. La prueba local del transporte y el resultado `enviado` no sustituyen recepción externa.

### Otras cinco parciales: HU-018, HU-056, HU-103, HU-104 y HU-105 (17/11/2026)

- **HU-018 — Configuración → Galería de instalaciones y próximas vacunas:** subir JPG/PNG reales de hasta 5 MB, asignar título, ordenar, quitar y guardar la galería pública. La subida prepara el archivo; **Guardar galería pública** publica la selección. Quitar una foto la retira de la selección, sin borrar su archivo físico. Se permiten hasta 50 fotos y se rechazan títulos vacíos/cortos, duplicados, rutas externas y archivos no subidos. El endpoint parcial conserva horarios y las otras políticas. La portada muestra títulos y texto alternativo, estado vacío y reintento. La galería es global, al igual que la política institucional existente. Falta aportar fotografías identificables de las instalaciones reales para cerrar la historia; las imágenes sintéticas de pruebas no cuentan.
- **HU-056/HU-103 — Próxima vacuna:** el worker incluye atenciones con cita y presenciales sin cita. Selecciona solo vacunas, propietario activo y sede del propietario; excluye desparasitación, fechas vencidas, ausentes o posteriores al plazo. El rango incluye hoy y el último día, usando la fecha de Perú. La clave de aplicación/fecha impide repetir el recordatorio en ejecuciones sucesivas. Configuración permite anticipación de 0 a 30 días; cero significa solo hoy. Ejecutar el worker y configurar/aprobar la plantilla `vacuna` con variables `nombre, mascota, producto, fecha`. La programación y selección están probadas, pero falta recepción WhatsApp real para el cierre documentado de ambas HU.
- **HU-104 — Comunicaciones → Plantilla a configurar:** la vista previa usa la **plantilla guardada** y ejemplos ficticios; muestra contenido, encabezado esperado y posiciones/valores del cuerpo sin enviar ni escribir mensajes. Guardar primero cualquier edición. Si se cambia el orden de variables, se reordenan transaccionalmente los parámetros de mensajes aún pendientes; el historial enviado permanece intacto. Mensajes pendientes incompatibles bloquean ese cambio con HTTP 409. El acceso de consulta permite vista previa sin editar plantillas. Falta acreditar correspondencia y uso con plantillas aprobadas en Meta.
- **HU-105 — Aviso al veterinario:** antes del envío se comprueba profesional activo y teléfono válido. Un teléfono incompleto deja el mensaje pendiente de configuración sin consumir intentos; tras corregir Personal, el reintento utiliza el teléfono actual normalizado. Si el profesional fue desactivado, se cancela el envío encolado. El seguimiento muestra la fecha de entrega del webhook cuando existe. Se conservan las pruebas de propuesta sin aviso y aceptación única que sí avisa. Falta recepción externa real por el profesional.

API nueva:

- `PUT /admin/operaciones/galeria`: `{ "galeria": [{ "url": "/uploads/instalaciones/<id>.png", "titulo": "Consultorio principal" }] }`.
- `PUT /admin/operaciones/politicas-vacunas`: `{ "dias_recordatorio_vacuna": 3 }`.
- `POST /admin/operaciones/plantillas/{evento}/vista-previa`: `{ "valores": { "cita": "123", "mascota": "Mascota de prueba", "fecha": "20/11/2026 10:00" } }` para `veterinario_reprogramacion`; usar las variables propias de cada evento.

Verificación de este avance: `python -m pytest -q tests/test_other_five_partial_stories.py` aporta **27 casos** HTTP/JWT y SQLite aislada. Suite local completa: **277 aprobadas, 12 omitidas**, sin fallos; las omitidas requieren PostgreSQL aislado y Docker estaba inactivo. `npm run build` correcto, con avisos de presupuesto inicial (624,15 kB frente a 500 kB) y CommonJS. Desde la raíz: `python backend/scripts/check_other_five_partial_stories_ui.py`, **20 comprobaciones nuevas** en Edge escritorio/móvil, más **54 de regresión** (`check_five_whatsapp_stories_ui.py`: 20; `check_fundamental_stories_ui.py`: 34), sin errores JavaScript. API visual, fotografías y proveedor controlados: no acreditan instalaciones reales ni entrega externa.

El informe maestro registra el bloqueo de las cinco prioritarias en **E27** (82 pruebas aprobadas y variables faltantes) y este avance en **E28**. Las cinco nuevas conservan **Parcial**; el total sigue en **86 completadas, 13 parciales y 16 pendientes**.

### Cinco pendientes prioritarias: HU-032, HU-097, HU-066, HU-100 y HU-101 (E29)

Estas cinco historias pasan de **Pendiente a Parcial**: el flujo está implementado y verificado con proveedor controlado; falta acreditar WhatsApp externo. Conteo actual: **86 completadas, 18 parciales y 11 pendientes**. El conteo E28 del apartado anterior es histórico.

**Operación:** ejecutar `python -m app.tasks.appointment_worker` desde `backend`. En **Administración → Configuración → Comunicaciones → Recordatorios y cobros prioritarios**, los cinco accesos rápidos seleccionan la plantilla y filtran sus envíos. Configurar las plantillas aprobadas desde ese panel y comparar la vista previa con Meta:

| Evento | Variables del cuerpo en orden | Encabezado |
| --- | --- | --- |
| `recordatorio_24h` | `nombre, mascota, fecha, cita` | Sin documento |
| `recordatorio_2h` | `nombre, mascota, fecha` | Sin documento |
| `orden_creada` | `nombre, codigo, total` | Sin documento |
| `orden_recordatorio` | `nombre, codigo, total` | Sin documento |
| `pago_validado` | `nombre, codigo` | Documento PDF |

- **HU-032/HU-097:** citas confirmadas/reprogramadas, cliente activo, sin llegada ni atención iniciada. El primer tramo se encola cuando faltan más de 2 y hasta 24 horas; el segundo cuando faltan más de 0 y hasta 2 horas. Se procesan en el siguiente ciclo disponible del worker, no con precisión de segundo. Si el worker inicia con menos de 2 horas, no acumula el aviso anterior de 24 h. Clave por evento/cita/instante UTC; formato de fecha mostrado en Perú. Destinatario: contacto de la reserva y, si falta, teléfono del perfil. Un cambio de fecha/estado, llegada o paso a otro tramo cancela el recordatorio pendiente antes de enviarlo. Desactivar recordatorios pausa el envío sin consumir intentos; reactivarlos permite enviar el mismo mensaje si sigue vigente.
- **HU-066:** crear una orden encola una sola comunicación con código e importe a dos decimales. Repetir la misma solicitud no crea otra orden ni otro aviso. Crear/enviar la orden no registra venta, pago ni descuento de stock. Un aviso pendiente se descarta si la orden ya está pagada, anulada o vencida.
- **HU-100:** un aviso por orden desde las 2 horas y antes de las 48 horas, mientras siga pendiente y no tenga abono validado ni comprobante en revisión. Un comprobante rechazado vuelve a permitir el seguimiento si nunca se envió ese aviso; no reinicia su clave. Se conserva el vencimiento existente de 48 h, ahora con límite exacto, sin encolar un recordatorio tardío. Las vencidas se consultan con `GET /operaciones/ordenes?estado=vencida`; se excluyen del filtro activo sin comprobante. API y pantalla impiden nuevos pagos de una vencida; coordinar una nueva orden.
- **HU-101:** el pago total confirmado encola una única boleta PDF, dentro de la transacción de la venta. Incluye liquidación de órdenes, venta directa con cliente identificado y aprobación de pedidos web. Un abono parcial, comprobante enviado o pedido rechazado no confirma el pago total. Ventas de público general sin cliente asociado no tienen destinatario. La confirmación de una venta anulada se descarta antes de enviar; un PDF faltante queda pendiente de configuración. El PDF es el comprobante interno existente de venta.
- **Reintentos:** se revalidan cliente, operación, sede activa, ventana, contacto y PDF según evento; los mensajes obsoletos pasan a `cancelado`. Un reintento administrativo obsoleto responde HTTP 409 y conserva el motivo. El teléfono inválido deja `pendiente_configuracion` sin consumir intentos; corregir el contacto y reintentar. `enviado` significa aceptación del proveedor; `entregado/leido` proviene del webhook. La deduplicación local no garantiza por sí sola entrega externa exactamente una vez ante fallos de red.

También se corrigió la comparación de inasistencia a `fecha_hora_programada <= ahora - tolerancia`, equivalente en PostgreSQL y compatible con SQLite; evita que una suma de fecha/intervalo en SQLite marque citas futuras como ausentes.

Pruebas: `python -m pytest -q tests/test_priority_pending_stories.py` aporta **40 casos nuevos**. Suite local final: **317 aprobadas, 12 omitidas**, cero fallos; Docker inactivo y PostgreSQL aislado no reejecutado. Build correcto (624,15 kB iniciales; avisos de presupuesto/CommonJS). Desde la raíz: `python backend/scripts/check_priority_pending_stories_ui.py`, **28 comprobaciones nuevas** en Edge escritorio/móvil. Regresiones de esta revisión: 20 de otras cinco parciales, 34 fundamentales y 20 de WhatsApp; todas aprobadas, sin errores JavaScript. La API visual y Meta son controlados.

**Cierre externo pendiente:** recibir los recordatorios reales (HU-032/HU-097), el código/importe de una orden nueva (HU-066), el seguimiento de una orden sin comprobante tras dos horas (HU-100) y la confirmación con boleta PDF tras validar el pago (HU-101). Registrar fecha, escenario y referencia del proveedor con `delivered/read`, sin credenciales ni documentos privados. La guía Gmail/Meta incluye las cinco plantillas nuevas.

## Notas privadas y recepción de mercadería

- **Veterinario → Atención / Nueva atención / Ficha clínica → Historia clínica**: notas internas por atención. Se consultan en endpoints separados y se excluyen del historial y documentos del cliente. El acceso combina profesional autorizado y permisos de historias clínicas.
- **Administración → Lotes y unidades**: recepción por proveedor y documento, una o varias líneas, cantidad, unidad, costo, lote y vencimiento. La pantalla muestra el historial de recepciones, responsable y detalle. Un documento repetido del mismo proveedor devuelve HTTP 409; una línea inválida revierte la recepción completa. El permiso de consulta conserva los listados y oculta los formularios de creación.

## Pruebas

### Cinco historias fundamentales: respaldo, vencimientos, asistencia, políticas y Kardex

- **HU-095 — Configuración → Respaldo de información:** descargar ZIP completo y seleccionar el archivo para verificar su restauración lógica aislada. Incluye todas las tablas y sedes, valores binarios, `uploads` y `clinical_private`, con SHA-256. La lectura PostgreSQL utiliza una transacción independiente `REPEATABLE READ` de solo lectura para mantener una fotografía consistente ante escrituras concurrentes. La verificación de interfaz usa SQLite temporal y rechaza archivos dañados, relaciones inválidas y rutas/esquemas incompatibles; no reemplaza tablas operativas. Requiere edición de Usuarios. La copia es manual: no programa retención ni almacenamiento externo.
- **Ensayo nativo del respaldo:** `tests/test_backup_postgres.py` comprueba el snapshot concurrente y recupera todas las tablas en un esquema PostgreSQL temporal, manteniendo tipos, JSON, binarios, claves y secuencias de identidad; compara cada fila y comprueba una inserción posterior. La transacción del esquema se revierte al finalizar. Es una prueba automatizada aislada, distinta del verificador SQLite de la interfaz. Las carpetas del ZIP se verifican por SHA-256; una recuperación operativa de archivos debe conservar las rutas de `uploads` y `clinical_private`.
- **HU-116 — Recepción, lotes y unidades:** plazo de aviso configurable entre 1 y 365 días con edición de Inventario. Lista estado vigente, próximo a vencer, vencido, sin fecha o agotado. El worker crea notificaciones internas para administradores activos de la sede con stock disponible, sin repetir por lote, fecha, etapa y destinatario; al pasar de próximo a vencido genera otro aviso. Utiliza la fecha de Perú. El WhatsApp adicional depende del proveedor, pero no condiciona la alerta interna de esta HU. Mantener en ejecución `python -m app.tasks.appointment_worker`.
- **HU-039 — Reservar cita → Confirmar asistencia por WhatsApp:** para citas de hoy o mañana no iniciadas, el cliente prepara `ASISTIRE <id>` hacia el teléfono de la clínica. Este teléfono debe corresponder al número Business que recibe el webhook. Abrir el enlace no confirma asistencia. El webhook firmado valida teléfono de la reserva (o perfil), cuenta activa, permisos, estado y fecha; guarda una única confirmación y notifica al veterinario. Cliente, agenda veterinaria y administración muestran el indicador; cambiar el horario elimina la confirmación anterior. **Pendiente de cierre:** configurar `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN`, URL pública HTTPS, suscripción `messages` y probar un mensaje real desde el contacto de una reserva.
- **HU-093 — Horarios y solicitudes:** cancelación configurable entre 0 y 168 horas; reprogramación entre 4 y 168. Se conserva el mínimo de cuatro horas de HU-035. Endpoints parciales con permiso de edición de Citas preservan galería, horarios y política de inventario. Los plazos se aplican a las acciones del cliente y a la aceptación de una propuesta; el personal mantiene la coordinación autorizada. No se borran citas existentes.
- **HU-114 — Inventario → Kardex por producto:** consulta ingresos, compras, ventas, ajustes y devoluciones con cantidades firmadas, saldo anterior/nuevo, fecha de Perú, lote, responsable, motivo y referencia. Filtros inclusivos por fecha y tipo, con permiso de consulta de Inventario y aislamiento de sede. Consulta sin edición ni borrado de movimientos. Los saldos son los originales, no se recalculan sobre la selección filtrada; movimientos anteriores a la trazabilidad no se inventan.

Pruebas específicas:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_fundamental_stories.py
```

Desde la raíz, después de compilar el frontend:

```powershell
.\backend\.venv\Scripts\python.exe backend/scripts/check_fundamental_stories_ui.py
```

Este recorrido ejecuta 34 comprobaciones en Edge (escritorio/móvil) con API controlada, incluidos diagnóstico, plantillas, filtros, reintentos y actualización de asistencia. La recepción real de WhatsApp se acredita aparte; HU-039 mantiene estado Parcial hasta entonces.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

`tests/test_next_five_stories.py` verifica HU-002, HU-004, HU-036, HU-061 y HU-120 con HTTP, JWT y SQLite aislada. Sus pruebas de correo reciben mensajes por SMTP en un servidor local temporal. Las integraciones PostgreSQL requieren la base local de pruebas indicada por cada suite.

`tests/test_priority_communications.py` verifica los disparadores administrativos/veterinarios, aceptación de horario, ausencia de avisos duplicados, cierre/orden/receta PDF, rechazo transaccional de órdenes incompatibles, envío controlado a Meta, reintentos y estados de entrega mediante webhook firmado. El transporte de Meta es controlado y no sustituye la evidencia externa.

### Integraciones PostgreSQL con un solo comando

Con Docker Desktop iniciado y las dependencias del entorno virtual instaladas, ejecuta desde la **raíz del proyecto**:

```powershell
.\backend\.venv\Scripts\python.exe backend/scripts/test_postgres.py
```

El script crea PostgreSQL 15 temporal en `localhost:55432`, aplica todas las migraciones y configura `DATABASE_URL`, `TEST_DATABASE_URL` y `TEST_APPOINTMENT_DATABASE_URL` para el proceso de pruebas. La base `test_clinica` se guarda en memoria temporal del contenedor y se elimina al terminar, incluso si las migraciones o las pruebas fallan.

La ejecución incluye las 12 integraciones que normalmente se omiten (9 de pedidos web, 1 de ventas, 1 de citas y 1 de respaldo/snapshot/restauración PostgreSQL), más la validación de archivos del mismo módulo: **13 pruebas**. La configuración se aplica únicamente a los procesos lanzados por el script.

Para ejecutar **toda la suite** con PostgreSQL disponible:

```powershell
.\backend\.venv\Scripts\python.exe backend/scripts/test_postgres.py --all
```

Para comprobar las pantallas en Microsoft Edge, instala la herramienta opcional `playwright`, compila el frontend y ejecuta desde la raíz del proyecto:

```powershell
.\backend\.venv\Scripts\python.exe -m pip install playwright
.\backend\.venv\Scripts\python.exe backend/scripts/check_next_five_stories_ui.py
```

El recorrido de interfaz utiliza una API controlada. La entrega a un buzón externo o a WhatsApp se acredita aparte con la configuración real de la clínica. El estado de cada historia y sus evidencias se mantienen en el informe Word maestro.
