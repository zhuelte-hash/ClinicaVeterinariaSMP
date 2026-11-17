# Ejecución y comprobación del backend

Ejecuta los comandos de PowerShell desde `backend`.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe run.py
```

API: <http://localhost:8000/docs>. Estado del servidor: <http://localhost:8000/health>.

## Correo de verificación y recuperación

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

Este recorrido ejecuta 24 comprobaciones en Edge (escritorio/móvil) con API controlada. La recepción real de WhatsApp se acredita aparte; HU-039 mantiene estado Parcial hasta entonces.

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
