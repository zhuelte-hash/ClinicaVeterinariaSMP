# Prueba de las 18 historias de WhatsApp — E35

## Alcance de esta entrega

WhatsApp normal o Web, con botones y envío humano, según lo solicitado por el
usuario. Los mensajes se preparan desde el sistema; una persona pulsa **Enviar**
en el chat, adjunta los PDF y registra las respuestas o los comprobantes recibidos.

La implementación está lista para la prueba del usuario. Las evidencias anteriores
de automatización son históricas; la aceptación actual evalúa estos recorridos.

## Preparación

1. Reinicia el backend y el frontend con `WHATSAPP_PROVIDER=manual`.
2. Comprueba **938 304 590** en Administración → Configuración → Teléfono.
3. Usa un cliente y un veterinario con teléfono correcto y las cuentas autorizadas
   de administración, veterinaria y caja.
4. Para probar enlaces desde otro teléfono, entra al sistema desde una dirección
   accesible para ese teléfono. El lanzador `scripts/start_manual_app.py` publica
   el frontend compilado y la API en el mismo origen e informa la dirección de red local.

## Botones comunes

- **WhatsApp de esta cita**: desde Citas o la agenda veterinaria.
- **WhatsApp de receta, vacunas y resultados**: desde la atención o el detalle del registro clínico.
- **Enviar orden, recordatorio o boleta por WhatsApp**: desde el detalle de la orden.
- **Enviar boleta por WhatsApp**: desde las últimas ventas del punto de venta.
- **Enviar confirmación y boleta por WhatsApp**: desde el pedido web aprobado.
- **Enviar bienvenida por WhatsApp**: desde Clientes.
- **Preparar avisos programados ahora**: administración, para los avisos cuya fecha ya corresponde.

Cada acceso abre la bandeja filtrada para su operación. Puedes pulsar
**Abrir WhatsApp #id** directamente, o **Preparar aviso #id** para revisar el texto,
**Copiar mensaje**, **Abrir chat de WhatsApp**, **Descargar PDF del aviso** y
**Registrar gestión manual**. **Ver todos los avisos** elimina el filtro contextual.

## Recorridos de aceptación

| Historia | Acción con los botones | Resultado a comprobar |
| --- | --- | --- |
| HU-032 | Crear/usar una cita próxima, preparar avisos y abrir su recordatorio. | Cliente recibe fecha y mascota correctas antes de la cita. |
| HU-036 | Cancelar una cita con motivo y entrar a WhatsApp de esa cita. | Cliente recibe la cancelación con su motivo. |
| HU-039 | Responder la referencia completa `ASISTIRE <id> <codigo>` del recordatorio o del portal. En Citas, pulsar Registrar asistencia recibida. | Una confirmación persistida, visible para cliente y veterinario; volver a registrarla no la duplica. |
| HU-050 | Guardar receta y cerrar la atención con cita; abrir su WhatsApp y descargar el PDF. | Cliente recibe el archivo adjunto y su código de orden correcto; se conserva una sola orden. |
| HU-056 | Programar próxima vacuna en atención con cita y sin cita; preparar avisos cuando esté en el plazo. | Aviso correcto para cada aplicación, sin duplicación. |
| HU-066 | Crear una orden, abrir su WhatsApp y enviar el texto preparado. | Código e importe correctos; preparar/abrir el aviso no registra pago ni salida de stock. |
| HU-067 | Desde Mis pagos, preparar la leyenda y abrir WhatsApp para adjuntar JPG/PNG/PDF. Caja registra el archivo recibido y pulsa Validar pago. | Comprobante asociado a la orden; efectos financieros una sola vez al validarlo. |
| HU-097 | Probar una cita con más de 2 y hasta 24 horas restantes y otra con hasta 2 horas; preparar los avisos. | Cada tramo corresponde al horario; un aviso previo de una cita reprogramada/cancelada deja de prepararse. |
| HU-098 | Confirmar, reprogramar y cancelar citas; abrir cada aviso vigente. | Cliente recibe los tres tipos correctos; los avisos obsoletos no se preparan. |
| HU-099 | Administración → Clientes → Nuevo cliente; después Enviar bienvenida por WhatsApp. | Bienvenida preparada una vez, recibida por el teléfono del cliente; no requiere SMTP en el alta administrativa. |
| HU-100 | Usar una orden sin comprobante con 2 a menos de 48 horas de antigüedad; preparar avisos. | Recordatorio disponible en su ventana; cargar comprobante, pagar o vencer invalida el aviso pendiente. |
| HU-101 | Completar el pago de una orden, una venta directa identificada y un pedido web aprobado; abrir los avisos y adjuntar sus PDF. | Confirmación y boleta correctas después del pago total; la gestión del mensaje no repite venta ni stock. |
| HU-103 | Preparar el aviso de vacuna con plazo configurado y teléfono actual, con y sin cita. | Destinatario y fecha correctos. Cambiar la próxima fecha invalida el aviso anterior. |
| HU-104 | Configuración → Comunicaciones → Personalizar textos; guardar y preparar un aviso pendiente. | Usa el texto actualizado y sus variables correctas; lo ya gestionado conserva su texto histórico. |
| HU-105 | Cliente acepta una propuesta de reprogramación; abrir el aviso al veterinario. | Profesional recibe el horario aceptado, sin avisos duplicados. |
| HU-106 | Cancelar una cita desde cliente y otra desde administración; abrir los avisos al profesional. | Veterinario correcto recibe cada motivo. |
| HU-107 | Guardar/adjuntar un resultado de laboratorio y abrir el WhatsApp de la atención. | Cliente recibe un enlace de la aplicación actual y accede a sus resultados al iniciar sesión. |
| HU-108 | Usar una atención cerrada hace al menos 24 horas, con cita y sin cita; preparar avisos y enviar la encuesta. | Enlace accesible, respuesta guardada y segunda respuesta rechazada. |

Los avisos por fecha respetan su ventana real. El botón no adelanta las dos horas
de una orden ni las 24 horas de una encuesta. La verificación técnica de límites
de tiempo usa reloj controlado; la prueba del usuario puede usar registros cuya fecha ya corresponda.

## Registro del resultado

Anota por historia: fecha, operación probada, rol, mensaje/PDF recibido y resultado.
El envío se acredita revisando el chat y confirmando la recepción con el destinatario.
**Registrar gestión manual** organiza la bandeja y conserva el operador; abrir el
chat o marcar la gestión no equivale por sí solo a recepción.

## Comprobación técnica

Desde `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_whatsapp_buttons.py tests/test_manual_whatsapp.py tests/test_complete_manual_access.py tests/test_manual_story_completion.py
```

Desde `frontend`: `npm run build -- --progress=false`.

Desde la raíz, después de compilar:

```powershell
.\backend\.venv\Scripts\python.exe backend/scripts/check_manual_stories_ui.py
```

El recorrido de Edge utiliza la aplicación real con JWT y SQLite aislada en
escritorio y móvil; simula la apertura del chat para comprobar el botón sin efectuar un envío externo.
