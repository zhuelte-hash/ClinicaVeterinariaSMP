# Revisión de historias parciales y pendientes

## Estado contrastado

Fuentes: `Informe_Historias_Usuario_SMP delcy.docx` (versión 3.17 / E33),
`README.md`, pruebas históricas del backend, compilación del frontend,
diagnóstico SMTP y aceptación manual externa del usuario el 23/11/2026.

Las 115 filas de historias del informe contienen **96 completadas, 19 parciales
y 0 pendientes**. Los conteos menores que aparecen en evidencias anteriores son
históricos. No se identificaron nuevas historias pendientes en el informe vigente.

Las 19 parciales tienen implementación documentada y cobertura automatizada.
Su cierre requiere los criterios de aceptación externos siguientes; aprobar
pruebas locales no cambia por sí solo su estado a Completada.

## Cierres E33 — 23/11/2026

HU-002 y HU-004 pasan de Parcial a Completada por aceptación manual del usuario
con correo real de Gmail, sumada a la cobertura automatizada histórica.

| Historia | Evidencia de aceptación |
| --- | --- |
| HU-002 | Código recibido en Gmail para cuenta con alias de prueba; código introducido, cuenta verificada e ingreso correcto, confirmados por el usuario. |
| HU-004 | Enlace recibido en Gmail; cambio de contraseña exitoso; enlace anterior rechazado al intentar reutilizarlo; contraseña anterior rechazada y nueva aceptada. Segunda recuperación desde incógnito: sesión normal previa perdió acceso a Mis mascotas; al iniciar con la última clave, los datos volvieron a cargar. |

La comprobación de sesiones fue manual y visual, mediante capturas y confirmación
del usuario; no se inspeccionó la respuesta HTTP. El rechazo del enlace se observó
sin distinguir uso previo de caducidad; uso único y revocación cuentan además con
cobertura automatizada histórica. No se archivaron capturas ni secretos.

Se agregó «¿Olvidaste tu contraseña?» al diálogo de inicio de sesión.
`npm run build` correcto: 625,71 kB iniciales, avisos de presupuesto/CommonJS.
El diagnóstico `scripts/check_communications.py --check-smtp` confirmó conexión
y autenticación correctas con Gmail sin enviar mensajes. La recepción posterior
fue comprobada por el usuario en los recorridos reales de registro y recuperación.
No se reejecutaron la suite backend ni las integraciones PostgreSQL en E33.

Primera entrega restante: **3 parciales (HU-036, HU-039 y HU-050)**.
Segunda etapa: **16 parciales**. En total restan **18 historias de WhatsApp
y HU-018 (fotografías reales)**.

## Matriz de cierre restante

### Avance HU-018 — 23/11/2026

El usuario aportó una fotografía real de la fachada mediante imagen y URL de
Google. Se conservó como `assets/instalaciones/fachada-san-martin-de-porres.jpg`
y se publicó en la política institucional del entorno activo con el título
«Fachada y entrada de la Clínica Veterinaria San Martín de Porres».
La fotografía se sirve localmente desde `/uploads/instalaciones/`, sin depender
de Google en cada visita. Procedencia y comando de publicación para otros entornos
en `assets/instalaciones/README.md`.

Verificación: API pública y JPEG HTTP 200; imagen 1020×1020. Dos recorridos Edge
contra frontend/API reales (1440×1000 y 390×844): imagen cargada, título y texto
alternativo correctos, imagen completa sin recorte, sin desbordamiento horizontal
ni errores JavaScript. `npm run build` correcto (625,71 kB; avisos existentes).
Capturas de verificación guardadas en la carpeta temporal de trabajo, no en Git.
El conteo se conserva en 96/19/0 hasta la confirmación visual final del usuario
de la galería publicada; no se exige un número adicional de fotografías.

| Historia | Funcionalidad implementada | Criterio restante para completar |
| --- | --- | --- |
| HU-018 | Subida, orden y publicación de galería; fachada real aportada por el usuario ya publicada y verificada en escritorio/móvil | Confirmación visual final del usuario de la fotografía en la galería pública. |
| HU-032 | Recordatorio previo desde el worker | Recibir recordatorio real de cita con referencia del proveedor. |
| HU-036 | Cancelación con motivo y aviso encolado | Cancelar una cita y acreditar recepción WhatsApp por el cliente. |
| HU-039 | Enlace de asistencia versionado y webhook firmado | Enviar confirmación real desde el contacto de la reserva y comprobar su persistencia. |
| HU-050 | Receta PDF persistida, orden y seguimiento privado | Cerrar atención y recibir receta PDF real con código de orden correcto. |
| HU-056 | Próxima vacuna y selección por fecha/sede | Recibir recordatorio de vacuna programada, también sin cita, sin duplicados. |
| HU-066 | Código e importe de orden en cola transaccional | Recibir código e importe reales; comprobar que el envío no crea pago, venta ni salida de stock. |
| HU-067 | Leyenda de pago y recepción de archivo por webhook | Enviar JPG/PNG/PDF real por WhatsApp con leyenda; revisar y validar una sola vez en caja. |
| HU-097 | Tramos de recordatorio de 24 h y 2 h | Recibir ambos tramos; comprobar que cancelar/reprogramar invalida el aviso obsoleto. |
| HU-098 | Avisos de confirmación, reprogramación y cancelación | Recibir los tres avisos reales con fecha efectiva y sin duplicados. |
| HU-099 | Bienvenida única tras verificar registro | Recibir una bienvenida real después de registrar y verificar una cuenta de prueba. |
| HU-100 | Seguimiento de orden desde 2 h y antes de 48 h | Recibir seguimiento real sin comprobante; invalidarlo al pagar, cargar comprobante o vencer. |
| HU-101 | Confirmación de pago total y boleta PDF interna | Recibir confirmación y PDF tras liquidar orden y aprobar pedido web, sin duplicados. |
| HU-103 | Recordatorio de vacuna con plazo configurable | Recibir aviso real para atención con cita y sin cita, con destinatario correcto. |
| HU-104 | Edición, vista previa y orden de variables de plantillas | Contrastar nombre, idioma, encabezado y variables con Meta y usar una plantilla aprobada en un envío real. |
| HU-105 | Aviso al profesional al aceptar reprogramación | Recibir aviso real en el teléfono del veterinario al aceptar la propuesta, sin duplicados. |
| HU-106 | Aviso al profesional por cancelación | Recibir aviso real al cancelar desde cliente y administración, con motivo correcto. |
| HU-107 | Aviso de laboratorio sin exponer resultados en el mensaje | Recibir aviso real y seguir el enlace como propietario autenticado con acceso autorizado. |
| HU-108 | Encuesta única desde 24 h del cierre | Recibir enlace externo, responder y comprobar persistencia y uso único, también sin cita. |

## Bloqueos comprobados en el entorno

El diagnóstico E33 confirmó SMTP preparado y autenticado con Gmail.
Siguen faltando las variables de WhatsApp/webhook:

- `WHATSAPP_PHONE_NUMBER_ID` y `WHATSAPP_ACCESS_TOKEN`.
- `WHATSAPP_APP_SECRET` y `WHATSAPP_VERIFY_TOKEN`.

En la revisión anterior Docker no respondía: el motor `dockerDesktopLinuxEngine` no estaba disponible.
Esto impide ejecutar en esta revisión las 24 pruebas nativas de PostgreSQL.
No demuestra un fallo del código de esas historias.

## Verificación local anterior a E33 (histórica)

| Comando y directorio | Resultado |
| --- | --- |
| `backend`: `.\.venv\Scripts\python.exe -m pytest -q` | 392 aprobadas, 24 omitidas, cero fallos; 107,23 s. Aviso de deprecación de Starlette/AnyIO. |
| `frontend`: `npm run build` | Correcto. Paquete inicial de 625,38 kB; avisos de presupuesto de 500 kB y dependencias CommonJS. |
| `backend`: `.\.venv\Scripts\python.exe scripts/check_communications.py` | No preparado: faltan las seis variables indicadas. No se enviaron mensajes. |
| Raíz: `docker info --format '{{.ServerVersion}}'` | No disponible; motor Docker inactivo. |

Las 416 pruebas aprobadas de E32 son evidencia histórica. La revisión local anterior obtuvo
es 392 aprobadas y 24 omitidas; no se presenta como una nueva ejecución completa
de PostgreSQL. En E33 sí se realizaron los recorridos manuales de correo descritos arriba.

## Secuencia para completar el cierre

1. Conservar la configuración Gmail local y las regresiones de HU-002/HU-004,
   cerradas en E33. Para volver a comprobar conexión sin enviar mensajes:
   `.\.venv\Scripts\python.exe scripts/check_communications.py --check-smtp`.
2. Configurar Meta, plantillas aprobadas, URL HTTPS pública y suscripción
   `messages`. Asegurar que el teléfono público de la clínica sea el Business
   receptor y que `FRONTEND_URL` sea accesible para los destinatarios.
3. Reiniciar API y ejecutar el worker desde `backend`:
   `.\.venv\Scripts\python.exe -m app.tasks.appointment_worker`.
4. Ejecutar los escenarios de la matriz con cuentas y destinatarios de prueba
   autorizados. Registrar historia, fecha, escenario, resultado y referencia.
   Para WhatsApp saliente, acreditar `delivered/read` mediante webhook;
   `enviado` solo significa aceptación por el proveedor. Para correo, comprobar
   recepción en el buzón externo. HU-039/HU-067 requieren además mensaje entrante
   real y persistencia del resultado esperado.
5. Publicar las fotografías reales de HU-018 desde Configuración.
6. Iniciar Docker Desktop y ejecutar desde la raíz:
   `.\backend\.venv\Scripts\python.exe backend/scripts/test_postgres.py --all`.
7. Actualizar el informe maestro únicamente para las historias cuyos criterios
   hayan sido acreditados. Conservar como Parcial cualquier cierre sin evidencia.

No incluir contraseñas, tokens, códigos de acceso ni documentos privados en la
evidencia. Los datos del proveedor se configuran localmente en `.env`.
