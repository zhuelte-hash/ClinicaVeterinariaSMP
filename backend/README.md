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

## Notas privadas y recepción de mercadería

- **Veterinario → Atención / Nueva atención / Ficha clínica → Historia clínica**: notas internas por atención. Se consultan en endpoints separados y se excluyen del historial y documentos del cliente. El acceso combina profesional autorizado y permisos de historias clínicas.
- **Administración → Lotes y unidades**: recepción por proveedor y documento, una o varias líneas, cantidad, unidad, costo, lote y vencimiento. La pantalla muestra el historial de recepciones, responsable y detalle. Un documento repetido del mismo proveedor devuelve HTTP 409; una línea inválida revierte la recepción completa. El permiso de consulta conserva los listados y oculta los formularios de creación.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

`tests/test_next_five_stories.py` verifica HU-002, HU-004, HU-036, HU-061 y HU-120 con HTTP, JWT y SQLite aislada. Sus pruebas de correo reciben mensajes por SMTP en un servidor local temporal. Las integraciones PostgreSQL requieren la base local de pruebas indicada por cada suite.

### Integraciones PostgreSQL con un solo comando

Con Docker Desktop iniciado y las dependencias del entorno virtual instaladas, ejecuta desde la **raíz del proyecto**:

```powershell
.\backend\.venv\Scripts\python.exe backend/scripts/test_postgres.py
```

El script crea PostgreSQL 15 temporal en `localhost:55432`, aplica todas las migraciones y configura `DATABASE_URL`, `TEST_DATABASE_URL` y `TEST_APPOINTMENT_DATABASE_URL` para el proceso de pruebas. La base `test_clinica` se guarda en memoria temporal del contenedor y se elimina al terminar, incluso si las migraciones o las pruebas fallan.

La ejecución incluye las 11 integraciones que normalmente se omiten (9 de pedidos web, 1 de ventas y 1 de citas), más la validación de archivos del mismo módulo: **12 pruebas**. La configuración se aplica únicamente a los procesos lanzados por el script.

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
