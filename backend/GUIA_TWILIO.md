# WhatsApp con Twilio Sandbox: paso a paso local

**Modalidad anterior:** esta guía describe el Sandbox clásico. La prueba limitada
de la consola nueva exige `ContentSid` predefinidos y no admite este envío libre
de texto/PDF. El usuario eligió WhatsApp manual; consulta
[GUIA_WHATSAPP_MANUAL.md](GUIA_WHATSAPP_MANUAL.md) para la configuración vigente.

La aplicación permite seleccionar `WHATSAPP_PROVIDER=twilio`. Se usan mensajes
libres dentro de la ventana de 24 horas abierta por un mensaje entrante del
destinatario. No necesitas configurar una aplicación de Meta para esta prueba.

## 1. Crear la cuenta y habilitar el Sandbox

1. Crea/inicia sesión en <https://www.twilio.com/try-twilio> y completa la
   verificación de la cuenta que solicite Twilio.
2. Abre <https://www.twilio.com/console/sms/whatsapp/sandbox>. Según la interfaz,
   aparece como **Messaging → Try it out → Send a WhatsApp message** o
   **Try out WhatsApp**. Activa el Sandbox.
3. Anota el número emisor y el texto **`join <tu-código>`** que muestra TU cuenta.
   Desde WhatsApp envía ese texto al número mostrado. Debes recibir su confirmación.
   Cada teléfono de cliente y veterinario que utilices debe unirse al mismo Sandbox.
4. En la consola de la cuenta localiza **Account SID** (`AC...`) y **Auth Token**.
   Utiliza las credenciales reales de esa cuenta, no las *Test Credentials*.

El emisor habitual del Sandbox es `whatsapp:+14155238886`; copia el valor exacto
de tu consola. Los mensajes salen de ese número de Twilio.

## 2. Iniciar el proyecto

Desde la raíz del repositorio, en PowerShell:

```powershell
.\iniciar-local.ps1
```

El lanzador instala las dependencias de `backend/requirements.txt` y abre API,
worker y frontend. Si ya estaban abiertos, detén las ventanas anteriores antes
de iniciarlo. Para iniciarlos por separado, desde `backend`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

Y en otra terminal de `backend`:

```powershell
.\.venv\Scripts\python.exe -m app.tasks.appointment_worker
```

## 3. Dar una URL HTTPS pública al backend

Twilio debe poder llamar al backend de tu computadora. Instala Cloudflare Tunnel
si no está disponible:

```powershell
winget install --id Cloudflare.cloudflared --exact
```

Abre otra terminal después de la instalación y ejecuta:

```powershell
cloudflared tunnel --url http://localhost:8000
```

Conserva esa terminal abierta. Copia el origen HTTPS que aparece, por ejemplo
`https://palabras-aleatorias.trycloudflare.com`. Abre
`https://TU-DOMINIO/health`: debe devolver `{"status":"ok"}`.

## 4. Guardar las credenciales localmente

Desde `backend`, ejecuta el asistente:

```powershell
.\.venv\Scripts\python.exe scripts/configure_twilio.py
```

Te pedirá Account SID, Auth Token oculto, emisor del Sandbox y origen HTTPS del
túnel. Solo actualiza las claves de Twilio/proveedor en el `.env` existente;
conserva conexión a base de datos, correo y las demás claves.

Equivalente manual en `backend/.env`:

```dotenv
WHATSAPP_PROVIDER=twilio
TWILIO_ACCOUNT_SID=AC_TU_ACCOUNT_SID_REAL
TWILIO_AUTH_TOKEN=TU_AUTH_TOKEN_REAL
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_PUBLIC_URL=https://TU-DOMINIO.trycloudflare.com
```

No copies literalmente los valores de ejemplo. El SID real tiene `AC` y otros
32 caracteres hexadecimales. El token se configura en tu computadora, no en el
frontend ni en el chat. `backend/.env` está excluido de Git.

**Reinicia API y worker** después de guardar. El frontend no necesita volver a
compilarse por cambiar estas variables del servidor.

## 5. Configurar los dos webhooks

En **Sandbox settings / Sandbox configuration** de Twilio:

| Campo | Valor | Método |
| --- | --- | --- |
| When a message comes in | `https://TU-DOMINIO/whatsapp/twilio/incoming` | POST |
| Status callback URL | `https://TU-DOMINIO/whatsapp/twilio/status` | POST |

Guarda los cambios. El asistente y **Administración → Configuración →
Comunicaciones** muestran las URLs exactas. Al enviar, la aplicación añade
además un identificador al callback para correlacionarlo con la cola.

**Ahora envía `hola` desde tu teléfono al Sandbox.** Esto es necesario incluso
si ya enviaste `join` antes de configurar el webhook. La aplicación registra el
mensaje entrante y conoce la ventana de 24 horas de ese teléfono.

Los webhooks verifican `X-Twilio-Signature` mediante el SDK oficial, el Account
SID y los números de WhatsApp. No necesitan el Verify Token ni el App Secret
de Meta. Si aparece un 403, revisa que `TWILIO_PUBLIC_URL` coincida exactamente
con el origen del webhook y que el Auth Token pertenezca a esa cuenta.

## 6. Enviar la primera prueba

1. Abre <http://localhost:4200> e ingresa como administrador.
2. Ve a **Configuración → Comunicaciones → Conectar Twilio Sandbox**.
3. Confirma que aparece **Proveedor de WhatsApp: Twilio Sandbox**, que las
   variables están presentes y que las URLs son las del túnel activo.
4. Introduce el teléfono desde el que enviaste `hola`, por ejemplo
   `+51 999888777`, y pulsa **Encolar prueba de Twilio**.
5. Mantén el worker activo y pulsa **Actualizar comunicaciones**. La referencia
   debe comenzar por `SM` o `MM`. `enviado` indica aceptación de Twilio;
   `entregado` y `leido` llegan mediante el callback. La lectura depende de que
   el destinatario tenga habilitadas las confirmaciones.

Puedes comprobar la configuración sin enviar mensajes:

```powershell
.\.venv\Scripts\python.exe scripts/check_communications.py
```

El diagnóstico distingue correo y Twilio. Puede terminar con código 1 si falta
SMTP aunque la parte de Twilio tenga todas las variables.

## 7. Probar las historias del sistema

- **Cancelación:** cliente cancela con motivo; el worker envía la confirmación.
- **Asistencia:** Reservar cita → Preparar confirmación abre el número del
  Sandbox. Envía el comando completo `ASISTIRE <id> <codigo>` desde el teléfono
  de la reserva. Actualiza para comprobar que quedó guardado.
- **Receta:** guarda la receta y cierra la atención. El worker envía el mismo
  PDF persistido que puede descargar el propietario. **Twilio no admite
  leyenda en documentos:** se envía el PDF sin `Body`; el código de la orden
  está dentro de la receta. La orden también tiene su aviso separado.
- **Comprobante entrante:** Mis pagos → detalle → preparar WhatsApp. Adjunta
  JPG/PNG/PDF de hasta 5 MB con la leyenda en el mismo mensaje. El archivo queda
  para revisión; caja debe validarlo antes de afectar saldo, venta o stock.
- **Avisos al veterinario:** su teléfono de Personal también debe estar unido
  al Sandbox y haber enviado `hola` con el webhook activo.
- **Laboratorio y encuesta:** los enlaces usan `FRONTEND_URL`. Para abrirlos
  desde un teléfono, configura un frontend y su API accesibles desde ese
  dispositivo; `localhost:4200` del teléfono no es tu computadora.

Los enlaces de asistencia/comprobantes usan automáticamente `TWILIO_WHATSAPP_FROM`
al seleccionar Twilio. El teléfono institucional público de la clínica conserva
su valor. Los textos pueden personalizarse desde Configuración sin aprobar
plantillas de Meta para estos envíos dentro de la ventana.

Los PDF se entregan a Twilio mediante una URL firmada de 30 minutos, ligada al
mensaje, destinatario y contenido. No se publican en la carpeta de uploads.
Los comprobantes entrantes se descargan con límite real de 5 MB desde los
servidores de Twilio, y conservan los controles de propiedad e idempotencia.

## Límites del Sandbox y problemas habituales

- **63015:** el teléfono no está unido a tu Sandbox o su vinculación caducó;
  vuelve a enviar el `join` exacto de tu consola. La sesión de Sandbox dura
  tres días y se renueva al volver a unirse.
- **63016 / sin ventana:** envía un nuevo `hola`. La aplicación espera sin
  consumir intentos cuando no conoce un mensaje entrante en las últimas 24 h.
- **20003:** comprueba las credenciales reales y la cuenta de Twilio.
- **21608:** la cuenta de prueba puede requerir verificar también el número
  destinatario en la consola.
- **No llegan entrantes o estados:** comprueba túnel, URL exacta, POST, firma
  y configuración guardada. Revisa los logs de Messaging de Twilio.
- El Sandbox admite un mensaje cada tres segundos. La cola respeta ese mínimo;
  con el worker predeterminado, varios avisos pueden necesitar varios ciclos.
- Al cerrar/reabrir un túnel rápido suele cambiar el dominio. Actualízalo con:

  ```powershell
  .\.venv\Scripts\python.exe scripts/configure_twilio.py --public-url https://NUEVO-DOMINIO.trycloudflare.com
  ```

  Reinicia API/worker y cambia también ambos webhooks en Twilio.

Esta integración es para pruebas con ventana activa. **No utiliza las tres
plantillas genéricas preaprobadas del Sandbox ni envía tus plantillas propias
fuera de las 24 horas.** Para probar una encuesta después de 24 h o recordatorios
de varios días, el destinatario debe abrir una nueva ventana antes del envío.
Esto no acredita una comunicación proactiva de producción ni cierra por sí
solo los criterios del Word que exigen plantillas aprobadas/entrega externa.

El Sandbox/trial tiene límites y puede generar cargos según la cuenta. Consulta
las condiciones actuales de tu consola. Referencia oficial:
<https://www.twilio.com/docs/whatsapp/sandbox>.
