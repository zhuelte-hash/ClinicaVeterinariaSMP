# Anexos UML de la Clínica Veterinaria San Martín de Porres

Cada archivo contiene un diagrama PlantUML independiente, desde `@startuml`
hasta `@enduml`.

| Anexo | Archivo | Alcance |
| --- | --- | --- |
| 3 | `anexo_03_casos_de_uso.puml` | Funciones principales y actores del sistema. |
| 4 | `anexo_04_clases.puml` | Vista resumida de las entidades principales y sus relaciones. |
| 5 | `actividades/` | Un diagrama de actividades por funcionalidad. |
| 6 | `secuencias/` | Un diagrama de secuencia por funcionalidad. |
| 7 | `anexo_07_componentes.puml` | Módulos Angular, servicios FastAPI y dependencias. |
| 8 | `anexo_08_despliegue.puml` | Ejecución local con PostgreSQL alojado en Neon. |

## Actividades y secuencias por funcionalidad

Cada fila corresponde a dos diagramas independientes: uno del anexo 5 y otro
del anexo 6. Los diagramas de secuencia representan la colaboración funcional
entre Angular, FastAPI, los servicios y la base de datos.

| Funcionalidad | Actividades | Secuencia |
| --- | --- | --- |
| Inicio de sesión | [5.1](actividades/anexo_05_01_inicio_sesion.puml) | [6.1](secuencias/anexo_06_01_inicio_sesion.puml) |
| Reserva y confirmación de cita | [5.2](actividades/anexo_05_02_reserva_cita.puml) | [6.2](secuencias/anexo_06_02_reserva_cita.puml) |
| Atención veterinaria | [5.3](actividades/anexo_05_03_atencion_veterinaria.puml) | [6.3](secuencias/anexo_06_03_atencion_veterinaria.puml) |
| Pago de una orden | [5.4](actividades/anexo_05_04_pago_orden.puml) | [6.4](secuencias/anexo_06_04_pago_orden.puml) |
| Compra de productos por web | [5.5](actividades/anexo_05_05_pedido_web.puml) | [6.5](secuencias/anexo_06_05_pedido_web.puml) |
| Apertura y cierre de caja | [5.6](actividades/anexo_05_06_caja.puml) | [6.6](secuencias/anexo_06_06_caja.puml) |
| Recepción de mercadería | [5.7](actividades/anexo_05_07_recepcion_inventario.puml) | [6.7](secuencias/anexo_06_07_recepcion_inventario.puml) |
| WhatsApp manual | [5.8](actividades/anexo_05_08_whatsapp_manual.puml) | [6.8](secuencias/anexo_06_08_whatsapp_manual.puml) |

Las operaciones privadas parten de una sesión activa y se someten a los permisos,
la propiedad del registro y la sede correspondientes. La atención del anexo 5.3
representa el recorrido con cita; el sistema también permite atenciones sin cita.
La reserva del anexo 5.2 empieza con una mascota ya registrada.

Las vistas integradas anteriores se conservan en `resumen/` como referencia.

## Correspondencia con el sistema

- Los roles implementados son cliente, veterinario, cajero y administrador.
  Los actores abstractos del anexo 3 agrupan funciones compartidas; las acciones
  siguen sujetas a los permisos configurados y al contexto de sede.
- Los perfiles de usuario se representan como composición, conforme a las
  relaciones de `backend/app/models/user.py`.
- `OrdenPendiente` es la solicitud de cobro; `AbonoOrden` representa cada abono;
  `OrdenCobro` es el modelo que registra la venta. La liquidación completa genera
  la venta, consume las existencias correspondientes y emite la boleta.
- WhatsApp se representa en el modo manual documentado en E34. El sistema prepara
  mensajes y documentos; una persona los envía y registra su gestión.
- El anexo 8 corresponde al arranque descrito por `iniciar-local.ps1` y
  `compose.neon.yaml`. La publicación del frontend compilado desde FastAPI se
  indica en una nota, conforme a `frontend_service.py`.

Fuentes principales: `backend/app/models/`, `backend/app/routers/`,
`backend/app/services/`, `backend/app/tasks/appointment_worker.py`,
`frontend/src/app/app.routes.ts`, `backend/ESTADO_HISTORIAS.md` y
`backend/GUIA_WHATSAPP_MANUAL.md`.

## Generación de imágenes

Desde esta carpeta, con Java y PlantUML disponibles:

```powershell
java -jar "ruta\plantuml.jar" -charset UTF-8 -tsvg "**/*.puml"
```

Los diagramas estructurales usan Smetana, incluido en PlantUML, para su disposición.

Los seis diagramas iniciales se comprobaron con PlantUML 1.2025.2 y se
renderizaron como imágenes PNG para revisar su estructura y sus etiquetas.

La separación por funcionalidades añade **16 diagramas independientes**: ocho
de actividades y ocho de secuencia. Se verificó su sintaxis y su generación en
PNG y SVG con PlantUML 1.2025.2; se revisaron visualmente los flujos con decisiones,
recepción por líneas y comunicaciones manuales.
