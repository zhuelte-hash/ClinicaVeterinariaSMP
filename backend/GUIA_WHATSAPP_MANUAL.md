# WhatsApp normal con envío manual

El modo elegido es `WHATSAPP_PROVIDER=manual` en `backend/.env`. Usa WhatsApp
normal o WhatsApp Web. Cada envío lo realiza una persona desde su sesión.

**E34:** el WhatsApp institucional ya quedó guardado como **938 304 590**
(`51938304590`). Portada, contacto, servicios, compras y enlaces del cliente
toman ese dato del contacto público persistido.

**E35 — alcance confirmado:** las 18 historias de WhatsApp se implementan con
botones y envío humano. La prueba final del usuario se realizará después de esta
entrega. El recorrido por botones está en [PRUEBAS_WHATSAPP_BOTONES.md](PRUEBAS_WHATSAPP_BOTONES.md).

## Configuración y primera prueba

1. Reinicia el backend para cargar el modo manual. Desde la raíz
   puedes usar `iniciar-local.ps1` después de detener las ventanas anteriores.
2. Ingresa como administrador y abre **Configuración**.
3. En **Información de la clínica → Teléfono**, escribe el WhatsApp en que la
   clínica recibirá mensajes. Para Perú puedes usar nueve dígitos o `+51` y el
   número. Para otros países, usa el código internacional.
4. Pulsa **Guardar cambios**, baja a **Comunicaciones** y pulsa **Actualizar
   comunicaciones**.
5. Debe aparecer **Manual · WhatsApp normal**. Pulsa **Probar enlace de WhatsApp**
   y, una vez abierto el chat, pulsa **Enviar**.

Ese teléfono se usa para los enlaces de asistencia, reprogramación y comprobantes
que preparan los clientes. Los avisos de la clínica usan el teléfono de cada
cliente o veterinario, según el evento.

## Enviar un aviso o una receta

1. Realiza la operación habitual: cancelar/confirmar una cita, crear una orden,
   cerrar una atención con receta o validar totalmente un pago.
2. Abre **WhatsApp manual** en tu panel: `/admin/comunicaciones`,
   `/veterinario/comunicaciones` o `/caja/comunicaciones`. Filtra por tipo y estado.
   También puedes entrar con el botón contextual desde Citas, atención clínica,
   Clientes, detalle de una orden, últimas ventas o un pedido web aprobado. La
   bandeja se abre filtrada para esa operación; **Ver todos los avisos** quita el filtro.
3. Pulsa **Preparar aviso**. Se comprueban operación, sede, permisos y contacto.
   La sección anterior de **Configuración → Comunicaciones** también permite prepararlos.
4. Pulsa **Abrir chat de WhatsApp**. Revisa el texto y pulsa **Enviar** dentro
   de WhatsApp. También puedes usar **Abrir WhatsApp #id** directamente en la
   tarjeta o **Copiar mensaje**. El botón directo revalida el aviso antes de abrirlo.
5. Si hay un PDF, pulsa **Descargar PDF del aviso** y agrégalo con el clip
   del chat. Un enlace `wa.me` no adjunta archivos automáticamente.
6. Al terminar, pulsa **Registrar gestión manual** para organizar la lista.
   Se conserva el operador en auditoría sin copiar el texto privado del aviso.

`pendiente_manual` significa que espera intervención humana. `gestionado_manual`
registra lo declarado por el operador; no es una confirmación de entrega ni de
lectura y no crea un identificador de proveedor. Preparar/copiar/abrir tampoco
registra pagos, ventas ni movimientos de inventario.

Los avisos por fecha (recordatorios, vacunas, órdenes pendientes y encuestas) se
crean con **Preparar avisos programados ahora**, desde administración. El botón
trabaja solo en la sede seleccionada, informa cuántos avisos nuevos creó y conserva
las ventanas de tiempo. No procesa correo ni cambia citas a inasistencia u órdenes
a vencidas. El worker conserva su funcionamiento como opción operativa.
Cambios posteriores de cita/vacuna/pago invalidan el aviso anterior cuando
corresponde; los contactos se releen al preparar.

Los textos se personalizan en **Configuración → Comunicaciones → Personalizar
textos de WhatsApp**. Al volver a preparar un aviso pendiente usa el texto guardado
actual; los avisos ya gestionados conservan su contenido histórico.

## Respuestas, asistencia y comprobantes

- Las respuestas se leen en WhatsApp normal.
- El cliente prepara un aviso de asistencia desde Reservar cita con referencia
  `ASISTIRE <id> <codigo>`. Los recordatorios de 24 h y 2 h también incluyen la
  referencia completa, actualizada al prepararlos. Administración abre **Citas**, filtra hoy/mañana o pulsa
  **Limpiar** y elige **Registrar asistencia recibida**. Introduce el teléfono
  del mensaje y pega su referencia/texto. Se validan contacto/horario actuales y
  se registra una confirmación única, autor y aviso al veterinario. El cliente
  consulta con **Actualizar confirmación registrada por la clínica**.
- Un comprobante recibido por WhatsApp debe cargarse en la orden desde caja con
  canal WhatsApp. Después un usuario autorizado lo valida. Solo esa validación
  actualiza el saldo y las operaciones asociadas.
- Los webhooks automáticos de Meta/Twilio quedan inactivos en modo manual.

## Permisos y alcance

Administración requiere consulta/edición de Usuarios. Veterinaria requiere consulta/
edición de Historias clínicas y accede a casos propios o derivaciones aceptadas.
Caja requiere consulta/creación de Ventas y accede a los avisos financieros de su
sede. Se respetan además los permisos del módulo de cada evento; la consulta no
permite preparar o marcar gestión. Registrar asistencia requiere edición de Citas.
El PDF sigue siendo autenticado y el correo conserva su configuración SMTP.

Los botones de laboratorio y encuesta usan la dirección de la sesión actual de
la aplicación y conservan el token privado de la encuesta. Así dejan de depender
de un túnel antiguo en `FRONTEND_URL`. La API conserva esa variable como respaldo
para llamadas que no incluyen una dirección de aplicación.
Para probar desde otro teléfono, abre primero el sistema mediante su dirección
de red local o dominio accesible. `localhost` sirve para pruebas en el mismo equipo.

Para probar la bienvenida por botones, usa **Administración → Clientes → Nuevo
cliente → Enviar bienvenida por WhatsApp**. El alta por personal autorizado prepara
una bienvenida única sin depender del correo del registro público. El registro
público conserva su verificación por correo.

Los criterios vigentes de E35 describen la preparación con botones, el envío humano,
el registro de asistencia y la carga/revisión del comprobante por el personal.
Los criterios anteriores de Meta/Twilio quedan como antecedentes. La implementación
se entrega lista para el test del usuario; la recepción real se registra durante
esa prueba y no se infiere del estado `gestionado_manual`.
