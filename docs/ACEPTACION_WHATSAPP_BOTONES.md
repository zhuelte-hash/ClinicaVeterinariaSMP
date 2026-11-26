# Cierre guiado de las 18 historias de WhatsApp por botones

## Preparación comprobada — 26/11/2026

- Modo local configurado: `WHATSAPP_PROVIDER=manual`.
- Base de datos accesible y migración aplicada `20261124_27`.
- Teléfono institucional consultado en la API: **938 304 590**.
- 99 pruebas específicas aprobadas y dos recorridos Edge integrados aprobados.
- Aplicación iniciada en `http://localhost:8000` con frontend compilado y API
  del mismo origen. La URL del celular depende de la red; consultar `url_lan`
  en el estado de la sesión del lanzador.

Esto acredita preparación técnica. Las 18 historias mantienen su aceptación
pendiente hasta completar las acciones y confirmar los resultados reales.

## Qué necesitamos del usuario

1. Acceso a una cuenta administradora y a los roles de veterinaria/caja para
   ejecutar sus acciones. Ingresar las contraseñas en la aplicación.
2. WhatsApp o WhatsApp Web disponible para el operador que enviará los avisos.
3. Un contacto de cliente de prueba que acepte recibir los mensajes, con teléfono
   correcto en su perfil y reserva. Para avisos profesionales, un veterinario de
   prueba con su teléfono actualizado.
4. Para laboratorio y encuesta: abrir la aplicación desde el celular. Puede ser
   la dirección de red local si computadora y teléfono tienen conectividad entre
   sí. Si no la tienen, preparar una dirección HTTPS accesible.
5. Identificar las operaciones como pruebas. Los pagos que se validen y las
   ventas que se aprueben generan movimientos reales en la base utilizada.

No se necesita una cuenta Meta, Twilio, plantillas aprobadas ni un webhook para
el alcance manual. SMTP se conserva para registro público/recuperación, pero
el alta administrativa y su bienvenida no dependen de él.

## Secuencia sugerida

### 1. Bienvenida y texto personalizado — HU-099 y HU-104

1. Entrar como administrador en **Clientes → Nuevo cliente**.
2. Introducir los datos del cliente de prueba y su teléfono real autorizado.
3. Pulsar **Enviar bienvenida por WhatsApp**.
4. Preparar el aviso y revisar destinatario y texto.
5. Abrir WhatsApp y pulsar **Enviar** en el chat.
6. El receptor confirma que recibió la bienvenida con el nombre correcto.
7. Registrar gestión manual; actualizar la lista y comprobar que no apareció
   una segunda bienvenida para la misma alta.
8. Para HU-104, antes de gestionar otro aviso pendiente, guardar un texto
   personalizado en **Configuración → Comunicaciones**, consultar su vista
   previa y enviarlo. Comprobar el texto recibido y que el aviso anterior
   gestionado conserva su contenido histórico.

### 2. Cita y asistencia — HU-032, HU-097 y HU-039

1. Registrar mascota y una cita de prueba con profesional y teléfono correctos.
2. Confirmar la cita y usar **Preparar avisos programados ahora** desde
   administración.
3. Probar una cita con más de 2 y hasta 24 horas restantes: enviar el primer
   recordatorio y comprobar mascota/fecha.
4. Probar una cita con más de 0 y hasta 2 horas: enviar el segundo recordatorio.
   Cada ventana debe corresponder a una operación vigente; no basta reenviar
   el primer tramo. Los límites ya tienen pruebas automatizadas.
5. Para una cita de hoy o mañana no iniciada, el cliente responde con la
   referencia completa `ASISTIRE <id> <codigo>` recibida.
6. Administración abre **Citas → Registrar asistencia recibida**, introduce
   remitente y referencia y guarda.
7. Comprobar asistencia en cliente y agenda veterinaria; repetir el registro
   debe conservar una sola confirmación.
8. Reprogramar/cancelar una cita con un aviso anterior pendiente y comprobar
   que ya no se permite preparar ese aviso obsoleto.

### 3. Cambios de cita — HU-098, HU-105, HU-036 y HU-106

1. Confirmar una cita y enviar su aviso al cliente (primera parte de HU-098).
2. Proponer un horario nuevo; el cliente acepta. Enviar la reprogramación
   al cliente y al veterinario (HU-098 y HU-105).
3. Confirmar recepción del horario efectivo correcto, sin avisos duplicados.
4. Cancelar otra cita desde el cliente respetando la anticipación configurada,
   con motivo, y enviar los avisos al cliente y al profesional.
5. Repetir cancelación desde administración con otra cita.
6. Verificar recepción de los motivos y destinatarios correctos. Así se cubren
   HU-036, la cancelación de HU-098 y ambos orígenes de HU-106.

### 4. Atención, receta y orden — HU-050 y HU-066

1. Iniciar una atención autorizada; guardar diagnóstico y receta, cerrar.
2. Entrar al WhatsApp de esa atención y descargar el PDF de receta.
3. Abrir chat, adjuntar el PDF con el clip y enviar.
4. El cliente confirma apertura del PDF y código de orden correcto.
5. Caja abre la orden y envía código e importe con su botón contextual.
6. Comprobar que preparar/enviar el aviso no registró pago ni descontó stock,
   y que sigue existiendo una sola orden del cierre.

### 5. Seguimiento, comprobante y boleta — HU-100, HU-067 y HU-101

1. Para HU-100, usar una orden de prueba con 2 a menos de 48 horas de antigüedad,
   sin comprobante en revisión ni pago validado. Preparar y enviar seguimiento.
2. Desde **Mis pagos**, el cliente prepara la leyenda, abre WhatsApp y adjunta
   JPG/PNG/PDF del comprobante de prueba junto a esa leyenda.
3. Caja carga el archivo recibido con canal WhatsApp y verifica la orden.
4. Caja valida el pago una sola vez. Comprobar saldo, venta, caja y stock;
   repetir la acción no debe duplicar sus efectos.
5. Después del pago total, enviar confirmación y adjuntar boleta PDF.
6. Para completar HU-101 repetir sus variantes: orden liquidada, venta directa
   con cliente identificado y pedido web aprobado.
7. Comprobar que el aviso de seguimiento anterior no puede prepararse después
   del pago/comprobante/vencimiento. No alterar fechas de datos operativos para
   simular la espera: usar operaciones de prueba cuya ventana corresponda.

### 6. Vacunas — HU-056 y HU-103

1. Registrar próxima vacuna con fecha dentro del plazo configurado.
2. Probar una atención con cita y otra sin cita.
3. Preparar avisos y enviar cada recordatorio; comprobar propietario, producto
   y próxima fecha recibidos.
4. Volver a preparar avisos no debe duplicar el recordatorio de esa aplicación.
5. Cambiar próxima fecha/contacto y comprobar invalidación del mensaje anterior
   o uso del contacto vigente, según corresponda.

### 7. Laboratorio y encuesta — HU-107 y HU-108

1. Guardar/adjuntar un resultado de laboratorio y enviar su aviso contextual.
2. Desde el celular receptor abrir el enlace, iniciar sesión como propietario
   y comprobar acceso al resultado. El texto de WhatsApp no debe incluirlo.
3. Para una atención cerrada hace al menos 24 horas, preparar y enviar encuesta.
4. Abrir el enlace en el celular, responder y comprobar persistencia.
5. Intentar responder otra vez: debe rechazarse.
6. Repetir encuesta con atención con cita y sin cita para completar HU-108.

## Registro de aceptación real

Marcar solo después de comprobar todos los escenarios del bloque. Registrar
fecha e identificadores de operación sin copiar documentos privados ni tokens.

| Historia | Fecha / operación / resultado confirmado por receptor |
| --- | --- |
| HU-032 | Pendiente |
| HU-036 | Pendiente |
| HU-039 | Pendiente |
| HU-050 | Pendiente |
| HU-056 | Pendiente |
| HU-066 | Pendiente |
| HU-067 | Pendiente |
| HU-097 | Pendiente |
| HU-098 | 26/11/2026: usuario indica que llegó la confirmación. Captura posterior muestra el acceso a confirmación de asistencia de chasca, cita #26; no muestra el contenido recibido en WhatsApp. Pendientes verificar texto/datos del aviso recibido y escenarios de reprogramación y cancelación. |
| HU-099 | 26/11/2026: cliente #10, aviso #6. Usuario confirma envío correcto; captura muestra bienvenida enviada en chat propio de WhatsApp (Tú). Comprobados apertura, destinatario y texto precargado/enviado. Capturas posteriores muestran «Gestión manual registrada», bandeja de pendientes vacía y una sola bienvenida #6 en el filtro Gestionados manualmente con estado gestionado_manual. Pendientes prueba de no duplicación al repetir el acceso desde Clientes y recepción desde cuenta de clínica en cuenta de cliente distinta. |
| HU-100 | Pendiente |
| HU-101 | Pendiente |
| HU-103 | Pendiente |
| HU-104 | 26/11/2026: captura de vista previa guardada de cita_confirmada muestra el texto personalizado con nombre benito, mascota puful y fecha de ejemplo sustituidos correctamente. Pendientes aplicación a un aviso pendiente real, envío/recepción del texto y conservación del contenido histórico gestionado. |
| HU-105 | Pendiente |
| HU-106 | Pendiente |
| HU-107 | Pendiente |
| HU-108 | Pendiente |

Guía funcional original: `backend/PRUEBAS_WHATSAPP_BOTONES.md`.

## Reutilizar el lanzador

Desde la raíz, después de compilar el frontend:

```powershell
.\backend\.venv\Scripts\python.exe backend/scripts/configure_manual_whatsapp.py
.\backend\.venv\Scripts\python.exe backend/scripts/start_manual_app.py --session "$env:TEMP\opencode\whatsapp-nueva-sesion"
```

La carpeta de sesión debe ser nueva y su padre `opencode` debe existir. El
lanzador informa URL local y de red, conserva logs, y actualiza `FRONTEND_URL`.
No inicia el worker: para estos recorridos se pueden preparar avisos por el botón
administrativo cuando su fecha corresponda. Para detener la sesión actual:

```powershell
.\backend\.venv\Scripts\python.exe backend/scripts/start_manual_app.py --session "$env:TEMP\opencode\whatsapp-botones-20261126" --stop
```
