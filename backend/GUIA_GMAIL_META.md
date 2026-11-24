# Preparación de Gmail y Meta para la aceptación externa

Configuración acordada: Gmail `uzielzarate2003@gmail.com` como remitente de prueba; conexión Meta existente; sistema local y despliegue posterior. Esta guía prepara las pruebas, pero no acredita recepción ni aprobación de plantillas.

**Actualización E33 — 23/11/2026:** HU-002 y HU-004 completadas mediante recepción
real en Gmail y aceptación manual del usuario. Registro/código/verificación/ingreso,
recuperación, contraseña anterior rechazada y nueva aceptada; enlace anterior rechazado
al intentar reutilizarlo. Segunda recuperación en incógnito con pérdida visual del
acceso de la sesión normal previa y recuperación del acceso tras autenticar con la
última clave; no se inspeccionó HTTP. Diagnóstico SMTP conectado/autenticado.
Detalle y límites en [ESTADO_HISTORIAS.md](ESTADO_HISTORIAS.md).
Conteo vigente: **96 completadas, 19 parciales, 0 pendientes**. Las instrucciones
y evidencias E20–E32 siguientes conservan su contexto histórico; WhatsApp sigue
requiriendo aceptación externa propia.

## 1. Gmail: dos historias de acceso

En la cuenta Google del remitente:

1. Activa la verificación en dos pasos.
2. Abre <https://myaccount.google.com/apppasswords> y crea una contraseña de aplicación para la clínica, si la cuenta permite esta opción.
3. En el archivo **existente** `backend/.env`, completa estas claves, conservando la configuración de base de datos y las demás claves:

```dotenv
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=uzielzarate2003@gmail.com
SMTP_PASSWORD=CONTRASENA_DE_APLICACION_DE_GOOGLE
SMTP_STARTTLS=true
SMTP_SSL=false
MAIL_FROM=uzielzarate2003@gmail.com
FRONTEND_URL=http://localhost:4200
```

Sustituye el valor de `SMTP_PASSWORD` por la contraseña de aplicación real, sin espacios. No es la contraseña habitual de inicio de sesión. No copies el valor de ejemplo como si fuera una credencial. El archivo `.env` está excluido de Git.

Reinicia API y worker. Desde `backend`, ejecuta:

```powershell
.\.venv\Scripts\python.exe scripts/check_communications.py --check-smtp
```

El diagnóstico valida conexión y autenticación SMTP sin enviar correo. Puede seguir terminando con código 1 si falta WhatsApp; revisa el resultado específico de SMTP.

Para HU-002 registra una cuenta nueva de prueba, recibe el código en su buzón y verifícala. Para HU-004 solicita recuperación, abre el enlace recibido, cambia la contraseña y comprueba uso único y retirada de acceso de las sesiones anteriores. Si abres el enlace desde otro equipo/teléfono, `localhost` apunta a ese dispositivo, no a la computadora del backend: realiza primero la prueba local en el mismo equipo o configura una URL frontend accesible para ese destinatario.

## 2. Meta: catorce plantillas para las comunicaciones de E31

En **WhatsApp Manager → Plantillas de mensajes**, prepara estas catorce plantillas. Selecciona el idioma español disponible y guarda su **código exacto** en el sistema (por ejemplo, `es` si ese es el aprobado); no presupongas que el proveedor aprobó `es_PE`. Meta determina su aprobación y categoría; usa Utilidad para los avisos operativos cuando corresponda.

Los textos de Meta utilizan variables numéricas `{{1}}`, `{{2}}`, `{{3}}`. Al configurar la aplicación, usa el texto con variables nominales que devuelve `GET /admin/operaciones/plantillas` y el orden indicado abajo.

| Nombre propuesto en Meta / evento local | Texto del cuerpo en Meta | Orden de variables en el sistema | Encabezado |
| --- | --- | --- | --- |
| `cita_confirmada` | Hola {{1}}, la cita de {{2}} está confirmada para {{3}}. | `nombre, mascota, fecha` | Sin documento |
| `cita_reprogramada` | Hola {{1}}, la cita de {{2}} fue reprogramada para {{3}}. | `nombre, mascota, fecha` | Sin documento |
| `cita_cancelada` | Hola {{1}}, la cita de {{2}} fue cancelada. Motivo: {{3}}. | `nombre, mascota, motivo` | Sin documento |
| `receta` | Hola {{1}}, adjuntamos la receta de {{2}} y su orden {{3}}. | `nombre, mascota, codigo` | **Documento PDF** |
| `veterinario_reprogramacion` | La cita {{1}} de {{2}} fue reprogramada/aceptada para {{3}}. | `cita, mascota, fecha` | Sin documento |
| `veterinario_cancelacion` | La cita {{1}} de {{2}} fue cancelada. Motivo: {{3}}. | `cita, mascota, motivo` | Sin documento |
| `recordatorio_24h` | Hola {{1}}, recuerda la cita de {{2}} para {{3}}. Responde ASISTIRE {{4}} para confirmar asistencia. | `nombre, mascota, fecha, cita` | Sin documento |
| `recordatorio_2h` | Hola {{1}}, la cita de {{2}} es a las {{3}}. Te esperamos. | `nombre, mascota, fecha` | Sin documento |
| `orden_creada` | Hola {{1}}, tu orden {{2}} es por S/ {{3}}. Envía el comprobante incluyendo {{2}} en el mensaje. | `nombre, codigo, total` | Sin documento |
| `orden_recordatorio` | Hola {{1}}, la orden {{2}} por S/ {{3}} sigue pendiente de comprobante. | `nombre, codigo, total` | Sin documento |
| `pago_validado` | Hola {{1}}, validamos tu pago de la orden {{2}}. Adjuntamos tu comprobante de venta. | `nombre, codigo` | **Documento PDF** |
| `bienvenida` | Bienvenido/a {{1}} a la Clínica Veterinaria San Martín de Porres. | `nombre` | Sin documento |
| `laboratorio` | Hola {{1}}, los resultados de {{2}} ya están disponibles en tu cuenta: {{3}}. | `nombre, mascota, enlace` | Sin documento |
| `encuesta` | Hola {{1}}, cuéntanos cómo fue la atención de {{2}}: {{3}}. | `nombre, mascota, enlace` | Sin documento |

Si Meta solicita ejemplos, usa datos ficticios: `Cliente de prueba`, `Mascota de prueba`, `20/11/2026 10:00`, `Cambio solicitado`, `OC-ABCDEF123456`, `123`, `40.00`. Para receta y pago validado carga un **PDF de muestra ficticio** como ejemplo del encabezado Documento. No agregues botones ni variables extra a estas plantillas: el envío está preparado para el cuerpo y el encabezado PDF cuando corresponde. En ventas directas y pedidos web aprobados, el código de pago puede ser `VTA-...`.

Cuando el estado sea **Aprobada**, abre **Administración → Configuración → Comunicaciones → Plantilla a configurar** y selecciona cada evento:

1. Nombre del proveedor: el nombre real aprobado en Meta (puede ser distinto del evento local).
2. Idioma: el código aprobado.
3. Contenido: el equivalente local con `{nombre}`, `{mascota}`, etc., no `{{1}}`.
4. Variables: los nombres nominales en el mismo orden del cuerpo aprobado.
5. Activa la plantilla y guarda.

Ejemplo local de cancelación:

```json
{
  "nombre_proveedor": "cita_cancelada",
  "idioma": "es",
  "contenido": "Hola {nombre}, la cita de {mascota} fue cancelada. Motivo: {motivo}.",
  "variables": ["nombre", "mascota", "motivo"],
  "activa": true
}
```

Usa `es` en este ejemplo únicamente si coincide con lo aprobado en Meta. Si tu número aún es el número de prueba de Meta, agrega/verifica los teléfonos de prueba permitidos en su panel. Una conexión existente no demuestra que las catorce plantillas estén aprobadas ni que el número ya esté habilitado para destinatarios generales.

## 3. Credenciales y recepción local

Completa en `backend/.env` con los valores reales de tu aplicación Meta:

```dotenv
WHATSAPP_PHONE_NUMBER_ID=ID_DEL_NUMERO_EN_META
WHATSAPP_ACCESS_TOKEN=TOKEN_DE_ACCESO_REAL
WHATSAPP_APP_SECRET=SECRETO_DE_LA_APLICACION_META
WHATSAPP_VERIFY_TOKEN=TOKEN_DE_VERIFICACION_ELEGIDO_PARA_EL_WEBHOOK
```

`WHATSAPP_PHONE_NUMBER_ID` es el ID del número, no el número telefónico ni el ID de la cuenta Business. El token de verificación se elige para comprobar el webhook y debe coincidir con el registrado en Meta; es distinto del token de acceso y del secreto de aplicación.

Meta no puede llamar a `localhost`. Para las pruebas locales se necesita un túnel HTTPS hacia `http://localhost:8000` o un backend desplegado. Con el túnel iniciado, registra en Meta:

- URL de devolución: `https://DOMINIO_PUBLICO_DEL_TUNEL/whatsapp/webhook`.
- Token de verificación: el mismo `WHATSAPP_VERIFY_TOKEN` del backend.
- Suscripción al campo **messages** de la cuenta WhatsApp correspondiente.

Mantén API, worker y túnel ejecutándose durante las pruebas. Si cambia el dominio temporal, actualiza la URL en Meta. En Configuración, el teléfono público de la clínica debe ser el Business receptor real. En Personal, completa el teléfono de prueba del veterinario; el cliente debe tener su teléfono en el perfil y en la reserva según corresponda.

Al desplegar, reemplaza el webhook temporal por el dominio HTTPS estable y cambia `FRONTEND_URL` al frontend real para que los enlaces de recuperación apunten al destino correcto.

## 4. Evidencia para cerrar las dieciocho historias de esta guía

| Historia | Comprobación real que falta acreditar |
| --- | --- |
| HU-002 | Código recibido en buzón externo y cuenta verificada. |
| HU-004 | Enlace recibido, contraseña cambiada, enlace de un solo uso y sesiones anteriores rechazadas. |
| HU-036 | Cancelación con motivo y mensaje recibido por el cliente, con referencia y estado del webhook. |
| HU-039 | Cliente prepara el enlace actualizado y envía `ASISTIRE <id> <codigo>` desde el contacto autorizado; webhook registra asistencia y las agendas la muestran sin duplicados. Si cambia horario o contacto, preparar otro enlace. |
| HU-050 | Cliente recibe PDF de receta y código de la orden única. |
| HU-067 | Archivo de pago enviado por WhatsApp con leyenda en el mismo archivo, vinculado a la orden y validado después por caja una sola vez. |
| HU-098 | Cliente recibe confirmación, reprogramación y cancelación reales, sin avisos duplicados. |
| HU-104 | Nombres/idiomas/variables guardados corresponden a plantillas aprobadas y se utilizan en envíos reales. |
| HU-105 | Veterinario recibe aviso al aceptar el cliente la propuesta de reprogramación. |
| HU-106 | Veterinario recibe aviso tras cancelar desde cliente y administración, con motivo correcto. |
| HU-032 | Cliente recibe un recordatorio real antes de su cita, con fecha y contacto correctos. Se comparte implementación con HU-097 sin generar otro aviso por esta HU. |
| HU-097 | Recepción real de los dos tramos (24 h y 2 h), con referencias y sin duplicados; verificar que cancelar o reprogramar invalida el recordatorio anterior pendiente. |
| HU-066 | Cliente recibe el código y el importe de una orden nueva; no se registra pago/venta/stock por enviar el aviso. |
| HU-100 | Cliente recibe seguimiento real desde las 2 h mientras no existe abono validado ni comprobante en revisión; no hay envío de un recordatorio obsoleto tras pagar/cargar comprobante/vencer. |
| HU-101 | Tras validar totalmente el pago, cliente recibe confirmación y boleta PDF; verificar orden liquidada y pedido web aprobado, con una referencia por operación. |
| HU-099 | Registrar y verificar una cuenta de prueba; recibir una única bienvenida en su teléfono, con referencia delivered/read. Un reenvío de verificación o reintento no debe generar otra bienvenida. |
| HU-107 | Adjuntar un resultado Laboratorio o publicar un resultado escrito/orden disponible; recibir el aviso real. Seguir el enlace, iniciar sesión como propietario y consultar el resultado; otra cuenta no puede acceder al archivo. |
| HU-108 | Cerrar una consulta, mantener worker y URL frontend accesible; después de 24 h recibir la encuesta real. Abrir el enlace, valorar y comentar; comprobar persistencia, rechazo de segundo envío y caducidad. Repetir con atención sin cita. |

E31 deja HU-099/HU-107/HU-108 en **Parcial**: implementación, HTTP/JWT, persistencia y
navegador verificados; Meta permanece sin configurar en el entorno de esta revisión. Los accesos
rápidos de Administración → Configuración seleccionan cada evento y sus envíos. `laboratorio`
enlaza a `/mis-mascotas`; `encuesta` a `/encuesta/<token>`. El enlace de encuesta concede respuesta
sin login: el seguimiento administrativo oculta su contenido y parámetros. Utiliza ejemplos
ficticios para las plantillas (`https://ejemplo.invalid/encuesta/muestra`) y una `FRONTEND_URL`
realmente accesible para la aceptación externa. Ejecuta el worker; los avisos se procesan por
intervalos, no exactamente al segundo. No publiques enlaces de encuestas reales en el informe.

Los recordatorios se revisan por intervalo del worker: tramo de 24 h cuando faltan más de 2 y hasta 24 horas, y tramo de 2 h cuando faltan más de 0 y hasta 2 horas. Si se inicia tarde no se envían ambos juntos. La orden sin pago/comprobante vence al cumplir 48 h; antes de ese límite se recuerda una sola vez desde las 2 h. Configuración permite seleccionar, previsualizar y seguir estos eventos con accesos rápidos. Las cinco HU nuevas pasan a Parcial en E29 hasta esta aceptación externa.

Las confirmaciones de asistencia y los comprobantes entrantes no requieren crear una plantilla para el texto que envía el cliente; requieren el webhook activo. Una conversación entrante o abrir el enlace no sustituyen recibir el archivo o procesar el comando válido.

### Avance E32 — cinco parciales prioritarias (20/11/2026)

HU-002/HU-004/HU-036/HU-039/HU-050 mantienen **Parcial** con mejoras verificadas:
registro atómico, serialización de solicitudes de código/enlace, correos pendientes revalidados,
espera visible en recuperación, token retirado al abrir el formulario y asistencia versionada.
En **Reservar cita → Comunicaciones y receta de mis citas** el propietario puede consultar el
estado de cancelación/asistencia, ver su orden y descargar la receta PDF emitida al cierre.
Es el mismo PDF preparado para WhatsApp; la descarga no reemplaza la recepción externa.

En la prueba real de HU-039 usa **Preparar confirmación** y el mensaje completo, incluido el código.
Si cambias el horario después de prepararlo, comprueba que el comando anterior se rechaza y que
uno nuevo sí confirma. `ASISTIRE <id>` sigue admitido por compatibilidad; si Meta aporta timestamp
se rechaza cuando es anterior al último cambio de horario. Los eventos que declaran un
`metadata.phone_number_id` distinto del configurado son rechazados. Abrir WhatsApp o actualizar la vista no confirma asistencia.

Para HU-036/HU-050 verifica también que corregir el teléfono permite reintentar al contacto actual;
el formato inválido no consume intentos. Una orden de receta anulada o vencida invalida su aviso
pendiente. El cliente distingue **aceptado por proveedor** de **entregado/leído** en el seguimiento.
Para HU-002/HU-004 recibe el correo externo y completa el proceso; los 31 casos nuevos y los
recorridos de navegador utilizan SMTP local y Meta/webhook controlados, sin acreditar recepción real.

Registra por cada historia fecha, escenario, resultado y referencia del proveedor en el documento maestro. No registres contraseñas, tokens, códigos de acceso ni archivos clínicos/bancarios privados. `enviado` en WhatsApp significa aceptación del proveedor; `entregado/leido` procede del webhook. SMTP aceptado no demuestra llegada al buzón. El cierre corresponde a la evidencia real de todos los criterios, no solo a la configuración.
