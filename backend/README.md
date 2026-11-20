# Ejecución y comprobación del backend

Ejecuta los comandos de PowerShell desde `backend`.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe run.py
```

API: <http://localhost:8000/docs>. Estado del servidor: <http://localhost:8000/health>.

## Cinco parciales prioritarias — E32, 20/11/2026

Avance de **HU-002, HU-004, HU-036, HU-039 y HU-050**. Conservan estado **Parcial**:
el diagnóstico del entorno sigue sin `SMTP_HOST`, `MAIL_FROM` ni las cuatro variables
de Meta/webhook. Conteo vigente: **94 completadas, 21 parciales y 0 pendientes**.

- **HU-002:** registro, desafío de verificación y mensaje se guardan en una sola transacción;
  si falla la preparación se revierte la cuenta y puede intentarse de nuevo. Reenvíos concurrentes
  se serializan por cuenta, conservando un solo desafío vigente y el límite de un minuto.
  Verificar/restablecer y reenviar usan el mismo orden de bloqueo (cuenta → desafío).
  Un correo pendiente se cancela si se desactiva la cuenta, cambia su dirección o ya fue verificada.
- **HU-004:** el formulario muestra la espera para solicitar otro enlace y respeta `Retry-After`.
  El token recibido se retira de la URL al abrir el formulario, permaneciendo solo en memoria;
  si se recarga antes de terminar, abrir de nuevo el enlace del correo. Se conservan uso único,
  caducidad y revocación de sesiones. Correos pendientes revalidan cuenta y destinatario actuales.
- **HU-036:** antes de enviar/reintentar la cancelación se comprueban propietario activo y
  verificado, estado de la cita, sede y teléfono actual de la reserva (respaldo del perfil).
  El teléfono inválido no consume intentos. El cliente consulta su estado en **Reservar cita →
  Comunicaciones y receta de mis citas**, sin acceso al contenido interno del mensaje.
- **HU-039:** el enlace preparado incluye `ASISTIRE <id> <codigo>`; el código HMAC depende del
  horario UTC, último evento de horario, contacto, propietario/versión de sesión y sede.
  Cambiar esos datos exige preparar otro enlace. Abrirlo sigue sin confirmar asistencia.
  Se conserva compatibilidad con `ASISTIRE <id>`; cuando Meta aporta timestamp, se rechaza
  el mensaje simple anterior al último cambio de horario. Si el webhook declara otro
  `metadata.phone_number_id` que el configurado, se rechaza el evento. La interfaz invalida
  enlaces preparados al actualizar los datos de la cita.
- **HU-050:** seguimiento privado de receta, código/importe/estado de su orden y descarga
  autenticada del **mismo PDF persistido para WhatsApp**, después del cierre. Permiso clínico,
  propiedad, sede y respuesta `private, no-store`; no se exponen parámetros, contenido o errores
  internos del mensaje. La entrega/reintento comprueba atención cerrada, orden vigente y PDF;
  anulación/vencimiento de la orden cancela el aviso pendiente, un PDF ausente espera configuración.
  Descargar no valida un pago ni acredita entrega WhatsApp.

API nueva de consulta: `GET /portal/citas/{id}/comunicaciones` y
`GET /portal/citas/{id}/receta-pdf`. Los estados se interpretan así: `pendiente` preparado,
`pendiente_configuracion` requiere intervención de clínica, `enviado` aceptado por proveedor,
`entregado/leido` confirmado por webhook. El seguimiento y la descarga son de solo consulta.

### Verificación E32

```powershell
# Desde backend: 27 casos nuevos HTTP/JWT, SMTP TCP local y SQLite aislada
.\.venv\Scripts\python.exe -m pytest -q tests/test_priority_partial_progress.py
# Desde la raíz: suite completa, incluidos cuatro casos PostgreSQL nativos nuevos
.\backend\.venv\Scripts\python.exe backend/scripts/test_postgres.py --all
# Desde frontend
npm run build
# Desde la raíz: Edge y API/JWT reales con SMTP local y webhook controlado
.\backend\.venv\Scripts\python.exe backend/scripts/check_priority_partials_ui.py
```

Resultado final: **416 aprobadas, cero fallos y cero omitidas, 107,92 s**. PostgreSQL temporal
migrado hasta `20261119_26`, contenedor/red eliminados; 31 casos nuevos (27 SQLite/JWT y cuatro
PostgreSQL). Incluye solicitudes simultáneas de verificación/recuperación, carrera entre reenvío
y verificación sin interbloqueo y asistencia versionada persistida. Build correcto, 625,38 kB
iniciales (avisos existentes de presupuesto/CommonJS). Dos recorridos integrados Edge aprobados
en 1440×1000 y 390×844, sin errores JavaScript: SMTP recibido, verificación, recuperación/espera,
token retirado/sesión revocada, asistencia mediante webhook firmado, seguimiento de cancelación
y descarga PDF con orden. Además, 52 regresiones visuales con API controlada aprobadas:
`check_next_five_stories_ui.py` (18) y `check_fundamental_stories_ui.py` (34).

**Cierre externo pendiente:** configurar los proveedores y completar los cinco recorridos de
[GUIA_GMAIL_META.md](GUIA_GMAIL_META.md), registrando recepción real, fecha, escenario y referencia.
SMTP TCP local y webhook/Meta controlados no acreditan recepción en buzón o WhatsApp externo.

## Seis historias restantes — E31, 19/11/2026

**Estado tras E31: 94 completadas, 21 parciales y 0 pendientes (115).**
HU-043/062/094 completadas; HU-099/107/108 implementadas y verificadas con proveedor
controlado, en estado Parcial hasta acreditar recepción externa por WhatsApp.
Los conteos de E28/E29/E30 de los apartados siguientes son históricos.

Aplica la nueva migración **20261119_26** antes de iniciar la API actualizada:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

- **HU-043 — Administración → Ocupación de agenda (`/admin/ocupacion`):** rango inclusivo
  de hasta 366 días y filtro de veterinario activo de la sede. Porcentaje = minutos
  ocupados/capacidad disponible × 100. Interseca horarios profesionales e institucionales,
  excepciones, descansos y bloqueos; combina intervalos superpuestos y excluye cancelaciones
  e inasistencias. Presenta totales y detalle diario, incluso capacidad cero. Consulta de Citas.
- **HU-062 — Veterinaria → Derivaciones clínicas (`/veterinario/derivaciones`):** seleccionar
  atención propia, otro especialista activo de la misma sede y motivo. El receptor acepta o
  rechaza con respuesta; ambos reciben seguimiento y notificaciones internas. Solo la aceptación
  habilita continuar el expediente referido desde la ficha del paciente; no crea otra atención
  ni reasigna la cita original. Rechaza duplicados activos, terceros, otra sede y falta de permisos.
- **HU-094 — Administración → Sucursales (`/admin/sucursales`):** alta, edición y activación;
  selector **Sede de trabajo** en el panel, aplicado mediante `X-Sucursal-ID`. Cambiar sede recarga
  el panel para eliminar datos visuales anteriores. Agenda, horarios, productos, inventario,
  caja, órdenes, pedidos web y reportes conservan contexto. Personal se asigna desde Usuarios;
  caja/veterinaria solo operan en su sede, administración puede seleccionarla. Cambiar la sede
  de un colaborador invalida sesiones y desactiva horarios anteriores; se rechaza mientras
  tenga caja abierta o citas futuras activas. No se desactiva la sede propia/seleccionada ni
  una con cajas abiertas. Clientes y permisos por rol, servicios, proveedores y políticas
  institucionales conservan su naturaleza compartida. No se trasladan existencias entre sedes.
  La migración persiste la sede de pedidos anteriores desde su venta/producto y crea índice/FK.
- **HU-099 — Bienvenida:** se encola una vez al verificar el correo y completar el registro.
  Antes de entregar/reintentar se releen cuenta activa/verificada, sede y teléfono actual;
  un contacto inválido queda pendiente sin consumir intentos. Plantilla `bienvenida`.
- **HU-107 — Laboratorio disponible:** guardar resultados escritos, marcar una orden de examen
  disponible o adjuntar un archivo de tipo Laboratorio encola un aviso transaccional. En Ficha
  clínica → Imágenes y archivos puede seleccionarse **Laboratorio**. El mensaje contiene un enlace
  a Mis mascotas; no incluye resultados clínicos ni archivos privados. El propietario inicia
  sesión para consultarlos; las descargas existentes tienen enlaces firmados de corta duración.
  Plantilla `laboratorio`.
- **HU-108 — Encuesta posterior:** el primer ciclo del worker a partir de 24 horas del cierre
  crea una encuesta única, también para atención sin cita, con token aleatorio guardado como hash
  y vigencia de 30 días. `/encuesta/:token` permite valorar de 1 a 5 y comentar hasta 2000 caracteres;
  no exige iniciar sesión ni muestra datos clínicos. Persiste una sola respuesta, rechaza enlaces
  caducados y cancela envíos pendientes si ya fue respondida. El seguimiento administrativo
  omite el contenido/parámetros de encuesta para no revelar su enlace. Plantilla `encuesta`.

Para HU-099/107/108 configura las tres plantillas y Meta/webhook según
[GUIA_GMAIL_META.md](GUIA_GMAIL_META.md), `FRONTEND_URL` accesible y el worker activo.
Registrar recepción externa con referencia `delivered/read` sigue siendo el criterio de cierre.

### Evidencia E31

```powershell
# Desde backend: 27 casos nuevos HTTP/JWT y SQLite aislada
.\.venv\Scripts\python.exe -m pytest -q tests/test_six_remaining_stories.py
# Desde la raíz: suite completa, migración y tres integraciones PostgreSQL nuevas
.\backend\.venv\Scripts\python.exe backend/scripts/test_postgres.py --all
# Desde frontend
npm run build
# Desde la raíz: Edge, escritorio y móvil, contra FastAPI/JWT reales y SQLite aislada
.\backend\.venv\Scripts\python.exe backend/scripts/check_six_stories_ui.py
```

Resultado final: **385 aprobadas, cero fallos y cero omitidas**, 96,50 s, PostgreSQL temporal
migrado hasta `20261119_26`; contenedor/red eliminados. Las 30 pruebas nuevas se distribuyen en
27 SQLite/JWT y tres PostgreSQL nativas; no se confunden los dos tipos de integración.
Build correcto (625,38 kB iniciales, avisos de presupuesto/CommonJS).
Dos recorridos integrados Edge aprobados (1440×1000 y 390×844), sin errores JavaScript: cálculo y
filtros, creación/selección de sede, mantenimiento/vista previa de tres plantillas, derivación,
aceptación y continuidad, encuesta/respuesta única/enlace inválido. Las peticiones del navegador
se ejecutan mediante TestClient contra la aplicación real y sus permisos, sin simular respuestas
de negocio; base SQLite aislada. Además, 60 regresiones visuales aprobadas con API controlada:
`check_independent_stories_ui.py` (26) y `check_fundamental_stories_ui.py` (34).
Los avisos WhatsApp y el webhook se prueban con transporte controlado, no con recepción externa.

## Correo de verificación y recuperación

Para la preparación acordada con **Gmail, una conexión Meta existente y ejecución local**, sigue [GUIA_GMAIL_META.md](GUIA_GMAIL_META.md): parámetros SMTP, catorce plantillas con textos/variables, webhook HTTPS y los dieciocho recorridos de aceptación externa.

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

### Cinco historias sin correo ni WhatsApp: HU-040, HU-041, HU-059, HU-079 y HU-119 (E30)

Implementadas y verificadas el 19/11/2026. Conteo vigente del informe maestro: **91 completadas, 18 parciales y 6 pendientes** (115 en total). Los conteos E28/E29 anteriores son históricos.

- **HU-040 — Administración → Citas:** selector de historial del listado y detalle desde el calendario. Muestra autor, fecha, valores anteriores/nuevos, nota y cantidades de reprogramaciones/cancelaciones. La creación, una reasignación y la misma fecha con otro huso horario no incrementan reprogramaciones. El historial es de consulta, sin endpoints de modificación; la actualización/eliminación ORM se rechaza. Conserva los eventos existentes; no reconstruye cambios anteriores a la trazabilidad.
- **HU-041 — Administración → Citas → Calendario mensual:** mes completo, navegación, filtro por veterinario o sin asignar, todos los estados y detalle de cita. Horario de Perú, independiente de los filtros del listado; consultas administrativas en modo lectura y aislamiento por sede. API reutilizada: `GET /admin/citas?fecha_inicial=AAAA-MM-01&fecha_final=AAAA-MM-DD`.
- **HU-059 — Cliente → Mis mascotas → Descargar carnet:** PDF específico de vacunas, con paciente, propietario, aplicación, lote, próxima fecha y profesional. No incluye desparasitaciones ni notas privadas. Sin aplicaciones, informa que no hay vacunas registradas. Descarga autenticada, permiso de Mascotas, propiedad y respuesta privada sin caché: `GET /portal/mascotas/{id}/carnet`.
- **HU-079 — Administración → Cierres de caja (`/admin/cierres`):** rango inclusivo por día de cierre en Perú, filtro opcional por ID del cajero, consolidado diario, diferencias y movimientos de cada caja cerrada. Incluye todos los cajeros de la sede; no duplica la venta final de una orden ya cobrada mediante abonos. El efectivo esperado incluye fondo más ingresos netos en efectivo, sin digitales. API: `GET /admin/operaciones/cierres?desde=AAAA-MM-DD&hasta=AAAA-MM-DD&cajero_id=5` (cajero opcional), `GET /admin/operaciones/cierres/{id}`. Requiere consulta de Ventas.
- **HU-119 — Administración → Inventario → Inventario valorizado al costo:** capital total, cantidad/unidad, costo promedio con cuatro decimales y valor por producto a dos decimales, búsqueda y filtro de costo pendiente. Método: promedio ponderado móvil de las compras existentes. Incluye productos inactivos y existencias físicas vencidas; señala costo cero con stock, sin sustituirlo por precio de venta. Total de valores redondeados por producto y subtotal del filtro; no suma cantidades de distintas unidades. `GET /admin/operaciones/valorizacion`, con permiso de consulta de Inventario y aislamiento por sede.

Verificación E30:

```powershell
# Desde backend: 21 casos HTTP/JWT con SQLite aislada
.\.venv\Scripts\python.exe -m pytest -q tests/test_five_independent_stories.py
# Desde la raíz: suite completa y cinco integraciones nativas nuevas
.\backend\.venv\Scripts\python.exe backend/scripts/test_postgres.py --all
# Desde frontend: compilación Angular
npm run build
# Desde la raíz: Edge, escritorio y móvil, API controlada
.\backend\.venv\Scripts\python.exe backend/scripts/check_independent_stories_ui.py
```

Resultado: **355 pruebas aprobadas, cero fallos y cero omitidas**, con migraciones completas en PostgreSQL temporal; contenedor/red eliminados al terminar. De los 26 casos nuevos, 21 usan SQLite y cinco PostgreSQL nativo (`test_independent_stories_postgres.py`). Las pruebas nativas nuevas usan transacción aislada revertida al terminar. Compilación correcta (624,37 kB iniciales; avisos de presupuesto/CommonJS). **26 comprobaciones Edge nuevas + 46 de regresión** (`check_fundamental_stories_ui.py`: 34 y `check_five_stories_ui.py`: 12), sin errores JavaScript, en 1440×1000 y 390×844. La API visual es controlada; HTTP/JWT y PostgreSQL se verifican por separado. No requiere migraciones nuevas ni datos de proveedores externos.

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

La ejecución incluye ventas, citas, pedidos web, respaldo/snapshot/restauración, las integraciones
de E30/E31 y `test_priority_partial_progress_postgres.py` de E32 (concurrencia de acceso y asistencia).
Los casos que dependen de PostgreSQL se omiten si no hay base aislada configurada. La configuración
del script se aplica únicamente a sus procesos de prueba.

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
