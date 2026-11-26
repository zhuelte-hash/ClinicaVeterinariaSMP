# Revisión de historias parciales y pendientes — E35

## Revisión del sistema — 26/11/2026

| Comprobación ejecutada | Resultado |
| --- | --- |
| `backend/scripts/test_postgres.py --all --port 55433` | **593 aprobadas, 0 omitidas y 0 fallos**, 177,86 s; PostgreSQL 15 temporal y migraciones hasta `20261124_27`. |
| `frontend`: `npm run build -- --progress=false` | Correcto; 630,46 kB iniciales. Persisten los avisos de presupuesto y dependencias CommonJS. |
| `backend/scripts/check_manual_stories_ui.py` | **2 recorridos Edge aprobados**, 1440×1000 y 390×844, API/JWT reales y SQLite aislada; sin errores JavaScript ni desbordamiento en las bandejas comprobadas. |
| `backend/scripts/check_fundamental_stories_ui.py` | **64 comprobaciones aprobadas** con API controlada en escritorio/móvil; sin errores JavaScript. |
| `backend/scripts/check_communications.py` | WhatsApp en modo manual; faltan `SMTP_HOST` y `MAIL_FROM` para repetir registro público/recuperación con correo real en este entorno. |

Se corrigió el bloqueo del ejecutor de pruebas cuando otro entorno ocupa `55432`:
`--port` configura de forma consistente Docker, Alembic y las tres conexiones de
prueba. Cinco casos nuevos verifican puerto predeterminado/personalizado, aislamiento
de la configuración operativa, rechazo de puertos inválidos y limpieza tras un
fallo de migración. El contenedor y la red `clinica-tests` se eliminaron al finalizar;
la eliminación se comprobó con Docker.

El conteo de aceptación sigue en **96 completadas, 19 parciales y 0 pendientes**.
Las 18 historias de WhatsApp requieren los recorridos de recepción y aceptación
del usuario de E35; HU-018 requiere su confirmación visual final de la galería.
Las pruebas de interfaz no enviaron mensajes externos.

## E35 — WhatsApp por botones (25/11/2026)

El usuario confirmó el alcance **WhatsApp solo con botones**, con envío humano y
prueba de usuario posterior a la implementación. Las 18 historias de WhatsApp
quedan implementadas para ese alcance. La aceptación final se registra al ejecutar
[PRUEBAS_WHATSAPP_BOTONES.md](PRUEBAS_WHATSAPP_BOTONES.md).

- Accesos contextuales desde citas, atención/registros clínicos, clientes, órdenes,
  últimas ventas y pedidos web aprobados. Filtros por operación, sede y permisos.
- Botones para preparar, abrir WhatsApp directamente, copiar texto, descargar PDF
  y registrar gestión manual.
- HU-032/HU-039/HU-097: ambos recordatorios incluyen la referencia completa de
  asistencia, actualizada al preparar y válida para el registro administrativo.
- HU-104: preparar un aviso pendiente aplica el texto personalizado actual; el
  historial gestionado conserva el contenido anterior.
- HU-107/HU-108: enlaces preparados con la dirección de la sesión actual, conservando
  autorización y token de encuesta. La dirección debe ser accesible al destinatario.
- HU-099: alta de cliente por administración y botón de bienvenida, sin dependencia
  de SMTP para ese recorrido. El registro público mantiene su verificación por correo.
- Preparar avisos por fecha trabaja en la sede seleccionada, informa nuevos avisos
  y no procesa transportes ni cambia citas/órdenes por vencimiento.

Los criterios anteriores de automatización quedan como antecedentes. El criterio
vigente es el recorrido manual por botones. En el informe, **Parcial** conserva la
aceptación final pendiente; el avance de implementación de estas 18 historias es
**listo para prueba de usuario**. HU-018 conserva su situación independiente.

### Verificación técnica E35

- Suite backend completa con PostgreSQL 15 temporal: **588 aprobadas, 0 omitidas,
  0 fallos**; 158,10 s. Se ejecutaron las 29 integraciones antes omitidas mediante
  `backend/scripts/test_postgres.py --all`, con migraciones hasta `20261124_27`.
  Contenedor y red de `clinica-tests` eliminados y limpieza verificada al terminar.
  La ejecución inicial sin PostgreSQL obtuvo 559 aprobadas y 29 omitidas (112,02 s).
- **13 casos nuevos** en `tests/test_whatsapp_buttons.py`: referencias de ambos
  recordatorios, cambio de contacto, textos pendientes/histórico, origen de enlaces,
  filtros de órdenes/ventas y preparación de avisos sin transportes ni vencimientos.
- Frontend: `npm run build -- --progress=false` correcto; 630,46 kB iniciales,
  con avisos de presupuesto y CommonJS.
- **2 recorridos Edge integrados** en 1440×1000 y 390×844, con API/JWT reales y
  SQLite aislada: filtros desde citas/órdenes, apertura directa, copia, asistencia,
  PDF de receta/boleta y encuesta con origen actual. Sin errores JavaScript ni
  desbordamiento horizontal en las bandejas comprobadas.
- Word **3.19/E35** actualizado, conservando las 115 historias y los estados de
  aceptación. Las historias ajenas a WhatsApp y los demás archivos internos del
  paquete Word se conservan; respaldo previo guardado en la carpeta temporal.

## Estado contrastado E34 (histórico)

Fuentes: `Informe_Historias_Usuario_SMP delcy.docx` (versión 3.18 / E34), código,
pruebas HTTP/JWT, recorridos integrados Edge y configuración institucional
comprobados el 24/11/2026. La aceptación externa de correo E33 se conserva como
antecedente del 23/11/2026.

Las 115 filas de historias del informe contienen **96 completadas, 19 parciales
y 0 pendientes**. Los conteos menores que aparecen en evidencias anteriores son
históricos. No se identificaron nuevas historias pendientes en el informe vigente.

Las 19 parciales tienen implementación documentada y cobertura automatizada.
El usuario eligió WhatsApp normal con envío manual y proporcionó **938304590**.
Su cierre conserva la aceptación real de cada historia; aprobar pruebas locales,
abrir un chat o declarar gestión manual no acredita recepción automática.

## Avance E34 — 24/11/2026

- Teléfono institucional guardado: **938 304 590**, `https://wa.me/51938304590`.
  Contacto público centralizado en portada, cabecera, pie, contacto, servicios,
  botón flotante, compras y enlaces del cliente.
- Bandejas **WhatsApp manual** en `/admin/comunicaciones`,
  `/veterinario/comunicaciones` y `/caja/comunicaciones`, con sede y permisos.
  Veterinaria accede a casos propios y derivaciones aceptadas; caja a avisos
  financieros. Los listados omiten el contenido privado y los tokens.
- HU-039: referencia versionada en el mensaje del cliente. Administración →
  Citas registra teléfono y referencia recibidos; confirmación única persistida,
  autor en auditoría/historial y notificación interna al veterinario.
- HU-098/HU-105/HU-106 revalidan estado, horario, último aviso, profesional,
  sede y contactos. Los cambios posteriores invalidan mensajes pendientes.
- HU-056/HU-103 revalidan vacuna, propietario, fecha, clave y plazo. La espera
  por política puede recuperarse y una fecha cambiada genera otro aviso.
- Avisos programados preparables desde la interfaz o worker; receta/boleta PDF
  autenticadas y gestión manual auditada. Compatibilidad con referencias de pago antiguas.
- HU-018: fachada real publicada idempotentemente, conservando las otras nueve
  fotos del entorno; resta la confirmación visual final del usuario.

### Verificación E34

| Comprobación | Resultado |
| --- | --- |
| Suite backend | **515 aprobadas, 24 omitidas, 0 fallos**; 122,34 s. Las omitidas requieren PostgreSQL aislado y Docker estaba inactivo. |
| Casos nuevos E34 | **42** en `tests/test_manual_story_completion.py`: contacto, asistencia, permisos/sede/caso, derivaciones, avisos vigentes, vacunas, bienvenida, recordatorios, comprobantes y boletas. |
| Frontend | `npm run build -- --progress=false` correcto; 626,83 kB iniciales, con avisos de presupuesto/CommonJS existentes. |
| Edge integrado | **2 recorridos**, 1440×1000 y 390×844, con `scripts/check_manual_stories_ui.py`: frontend compilado, FastAPI/JWT reales, SQLite aislada y asset real. Sin errores JavaScript ni desbordamiento horizontal. |
| Regresión visual | **64 comprobaciones** con API controlada en `scripts/check_fundamental_stories_ui.py`. |
| Entorno configurado | Contacto público/compras devuelven `51938304590`; API institucional y JPEG de fachada HTTP 200 mediante aplicación real/TestClient. |

Los recorridos integrados incluyen teléfono, galería, contacto codificado,
asistencia persistida, bandejas por rol, receta/boleta PDF y encuesta única.
No envían mensajes externos ni acreditan una espera real de 2/24 horas; los
límites de tiempo se comprueban con reloj controlado.

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

## Matriz de cierre E34 (histórica; alcance vigente en E35)

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

Actualización de galería: se incorporaron las nueve fotografías reales aportadas en
`frontend/public`, con copias JPEG optimizadas en `assets/instalaciones` (9439 KB
a 1352 KB). El entorno activo publica diez fotografías contando la fachada.
Presentación adaptable en columnas sin recortar las fotos, títulos descriptivos y
visor ampliado con navegación, cierre por Escape y retorno del foco. Comprobado en
Edge contra frontend/API reales en 1440×1000 y 390×844: diez imágenes cargadas,
sin desbordamiento horizontal ni errores JavaScript; navegación y cierre correctos.
Compilación correcta, con los avisos existentes de presupuesto y CommonJS.
HU-018 conserva su estado hasta la confirmación visual final del usuario.

| Historia | Funcionalidad disponible E34 | Aceptación real aún pendiente |
| --- | --- | --- |
| HU-018 | Subida, orden y publicación de galería; fachada real aportada por el usuario ya publicada y verificada en escritorio/móvil | Confirmación visual final del usuario de la fotografía en la galería pública. |
| HU-032 | Recordatorio en bandeja manual, worker o interfaz | Enviar y recibir el aviso real antes de la cita. |
| HU-036 | Cancelación con motivo y aviso manual privado | Cancelar, enviar y confirmar recepción por el cliente. |
| HU-039 | Referencia versionada y registro por administración, con persistencia y auditoría | Recibir un mensaje real del propietario y registrar su referencia. |
| HU-050 | Receta PDF con código de orden, desde bandeja autorizada | Adjuntar y recibir el PDF real con código correcto. |
| HU-056 | Próxima vacuna con fecha, política y contacto revalidados | Recibir recordatorio real con y sin cita, sin duplicados. |
| HU-066 | Código e importe en bandeja de caja | Recibir datos reales sin efectos financieros por abrir el aviso. |
| HU-067 | Leyenda y carga/revisión/validación del archivo recibido manualmente | Enviar un archivo real y registrarlo/validarlo una sola vez. |
| HU-097 | Tramos 24 h/2 h y rechazo de mensajes obsoletos | Recibir ambos tramos y comprobar invalidación al cambiar la cita. |
| HU-098 | Avisos con horario, estado y último cambio revalidados | Recibir los tres avisos reales sin mensajes obsoletos. |
| HU-099 | Bienvenida manual única tras verificar registro | Verificar con correo operativo y recibir la bienvenida real. |
| HU-100 | Seguimiento 2–48 h, invalidado por pago/comprobante/vencimiento | Recibir el aviso real y comprobar que no se prepara uno obsoleto. |
| HU-101 | Confirmación y boleta en caja, incluida venta directa y aprobación web | Recibir confirmación y PDF reales después del pago total. |
| HU-103 | Vacuna con contacto/plazo actual y espera recuperable | Recibir avisos reales con y sin cita y destinatario correcto. |
| HU-104 | Textos manuales personalizables y vista previa privada | Aceptar el texto personalizado mediante un envío real del alcance manual. |
| HU-105 | Aviso con contacto/asignación/último evento vigentes | Recibir aviso real tras aceptar reprogramación, sin duplicados. |
| HU-106 | Cancelación al profesional con motivo y estado vigente | Recibir avisos reales desde ambos orígenes de cancelación. |
| HU-107 | Aviso sin resultados; caso propio o derivación aceptada | Recibir aviso y acceder como propietario desde un frontend accesible. |
| HU-108 | Encuesta privada única, también sin cita, preparada en bandeja | Recibir enlace accesible, responder y comprobar uso único. |

Los criterios originales de despacho/recepción automáticos y plantillas aprobadas
no se acreditan con esta alternativa manual. El Word conserva el criterio anterior
junto al vigente E34; no hay cierre por asociación.

## Configuración y bloqueos documentados en E34 (histórico)

E34 usa **manual**, con el teléfono actualizado. Cada aviso lo envía una persona
y los archivos recibidos se registran en caja. `FRONTEND_URL` debe ser accesible
desde el dispositivo que abra laboratorio/encuesta; `localhost` sirve solo en el equipo local.

El diagnóstico local sigue sin `SMTP_HOST`/`MAIL_FROM`: la aceptación Gmail E33
es histórica y repetir registro/recuperación exige restaurar su configuración.
Docker Desktop no está disponible; se omiten las 24 integraciones PostgreSQL.

### Antecedentes de proveedores E33

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

## Secuencia para completar el cierre manual

1. Reiniciar API/frontend con `WHATSAPP_PROVIDER=manual` y comprobar el teléfono
   **938304590** en Configuración. La fachada real ya fue publicada.
2. Abrir **WhatsApp manual** en el panel del rol correspondiente. Los avisos
   programados se actualizan con worker o **Preparar avisos programados ahora**
   desde administración. Preparar y enviar cada mensaje con WhatsApp normal.
3. Para HU-039, el cliente envía el mensaje con referencia. Administración filtra
   la cita de hoy/mañana o pulsa **Limpiar** y usa **Registrar asistencia recibida**.
   Para HU-067, caja registra el archivo recibido y después valida el pago.
4. Ejecutar la matriz con destinatarios de prueba y registrar fecha, escenario,
   resultado y confirmación del receptor. `gestionado_manual` es una declaración
   del operador; no acredita por sí solo recepción ni automatización.
5. Confirmar visualmente la galería y configurar frontend/API accesibles para
   los enlaces. Restaurar SMTP local antes de repetir registro/recuperación.
6. Para las pruebas PostgreSQL, iniciar Docker Desktop y ejecutar desde la raíz:
   `.\backend\.venv\Scripts\python.exe backend/scripts/test_postgres.py --all`.
7. Actualizar el informe maestro únicamente para las historias cuyos criterios
   hayan sido acreditados. Conservar como Parcial cualquier cierre sin evidencia.

No incluir contraseñas, tokens, códigos de acceso ni documentos privados en la
evidencia. Los datos del proveedor se configuran localmente en `.env`.
