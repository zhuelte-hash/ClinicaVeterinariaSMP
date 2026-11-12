# Cierre de 10 historias parciales prioritarias

Fecha: **11 de noviembre de 2026**. Informe: **versión 2.1**.

## Criterios de cierre y recorridos

| HU | Cierre implementado y verificado | Recorrido |
| --- | --- | --- |
| HU-008 | Matriz por rol/módulo aplicada en servidor a administración, caja, veterinaria y clientes, incluidas ventas administrativas y nuevas operaciones. Acciones separadas de ver/crear/editar/eliminar/aprobar. Guardas y navegación usan permisos actuales. El rol y la propiedad de los registros siguen comprobándose. | Administración → Usuarios → Permisos por rol. Revocar acceso y comprobar el portal o invocar directamente su API. |
| HU-065 | Orden persistida antes del pago, código, cliente, artículos, precios fijados, total y saldo. Caja y veterinaria pueden crearla; cerrar una atención genera una orden por servicio y productos vinculados de la receta. Se evita duplicar por atención o reintento y cobrar por otro flujo una atención con orden activa. | Caja / Veterinaria / Administración → Órdenes y pagos. Atención → emitir receta → vincular productos → cerrar → consultar orden. |
| HU-068 | Caja carga manualmente JPG/PNG/PDF recibido por WhatsApp, registra monto, medio —incluida transferencia— y código de operación; el archivo queda privado. Puede verlo, validarlo o rechazarlo con motivo. Solo la validación autorizada afecta caja, saldo, boleta y stock. | Caja → Órdenes → Ver detalle → Origen «Recibido por WhatsApp (carga manual)» → adjuntar → registrar → ver comprobante → validar/rechazar. |
| HU-070 | Listado de órdenes pendientes sin comprobante vigente, incluso cuando un archivo anterior fue rechazado. Conserva código, cliente, fechas, estado, importe, abonado y saldo para seguimiento. | Caja → Órdenes y pagos → Solo sin comprobante vigente → Filtrar órdenes. |
| HU-074 | Solicitud con cliente, monto y motivo; administración aprueba/rechaza y queda identificada. POS y órdenes solo aceptan autorizaciones aprobadas para el mismo solicitante y cliente, de un solo uso. Se rechazan descuentos arbitrarios o reutilizados por API. | Caja → Punto de venta / Órdenes → solicitar descuento. Administración → Órdenes y pagos → aprobar. Caja → actualizar autorizaciones → aplicar. |
| HU-076 | Historial propio reúne órdenes y abonos, ventas físicas/servicios y compras web; permite descargar la boleta de venta y distingue el archivo bancario enviado. Se comprueba la propiedad en API y descargas. | Portal cliente → Mis pagos y boletas (`/mis-pagos`). |
| HU-077 | Cajero autorizado anula su orden sin abonos o su venta directa de caja abierta con motivo obligatorio. La venta revierte stock e ingreso una sola vez y conserva responsable. Las órdenes con abonos y las ventas de cajas cerradas requieren conciliación; se bloquea su anulación inconsistente. | Caja → Órdenes y pagos → Anular orden con motivo / Ventas registradas → Anular con motivo. |
| HU-080 | Administración consulta todas las órdenes de la sede por fechas inclusivas en horario de Perú, estado y ausencia de comprobante. El detalle incluye artículos, importes, pagos, motivos e historial con autores y fechas. | Administración → Órdenes y pagos → Desde/Hasta/Estado → Ver detalle y pagos. |
| HU-083 | Alta y edición del personal más activación/desactivación persistida. Desactivar conserva citas y registros, invalida JWT anteriores e impide login. Reactivar exige sesión nueva. El profesional inactivo deja de ofrecer disponibilidad para nuevas reservas. | Administración → Usuarios → Desactivar / Activar. |
| HU-089 | Exportación XLSX de ventas, citas e inventario con permisos por reporte y todas las filas filtradas, sin paginación. Fechas inclusivas; estado, medio y código en ventas; estado en citas. Inventario indica cantidades y valorización actuales. | Administración → Reportes Excel (`/admin/reportes`). |

## Verificación ejecutada

### Backend

Desde `backend`:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Resultado: **81 aprobadas, 11 omitidas**. Las omitidas requieren PostgreSQL local de pruebas configurado explícitamente. Las **19 nuevas pruebas** de `tests/test_priority_stories.py` usan datos SQLite aislados, JWT real, autorización del servidor y almacenamiento real en esa base de prueba; no contactan proveedores de mensajería ni modifican datos operativos.

Cubren, entre otros: revocación por rol en cuatro portales, invalidación de sesiones del personal, generación clínica de órdenes con receta, duplicados, comprobantes privados, validación repetida, precio acordado aunque cambie el catálogo, rollback ante falta de disponibilidad, rechazo y seguimiento, descuentos aprobados, devolución de stock/caja, límites de fecha en Perú, propiedad del historial y sus boletas, vinculación web, y exportación de más de una página de ventas.

### Interfaz

`npm run build` correcto. **16 comprobaciones automatizadas en Edge** sobre la compilación con API controlada: creación de orden y descuento, filtro sin comprobante, carga de WhatsApp, visor privado, validación, descarga de boleta, anulación con motivo, aprobación administrativa, Excel, historial multicanal, vinculación de receta, denegación por permisos y vista móvil de 390 px. Sin errores JavaScript.

La simulación de API de estas comprobaciones visuales es independiente de las pruebas HTTP reales del backend descritas arriba.

### Base de datos

`alembic current`: **37ebf391ec82 (head)**. Se reutilizan las tablas de operaciones y los campos ya presentes en esa migración; no se requiere otra migración para este lote.

## Alcance del cierre

- HU-068 cierra el **registro manual por caja de un comprobante recibido por WhatsApp**, tal como solicita esa historia. La recepción automática por webhook corresponde a HU-067 y tiene su propio criterio de entrega/operación.
- La boleta es interna. Su descarga no acredita integración fiscal.
- Las diez historias pasan de Parcial a Completada. El conteo documental pasa de **54 a 64 implementadas/completadas**, con **21 parciales y 30 pendientes**. Las demás filas mantienen la evaluación anterior, incluso cuando existan avances locales fuera de este lote.

## Archivos principales

- `backend/app/permissions.py`, `security.py`, `routers/users.py`, `services/access_service.py`.
- `backend/app/routers/operations.py`, `reports.py`, `appointments.py`.
- `backend/app/services/billing_service.py`, `cashier_service.py`, `appointment_service.py`, `audit_service.py`.
- `backend/tests/test_priority_stories.py`.
- `frontend/src/app/core/guards/permission.guard.ts` y `core/auth/auth.service.ts`.
- `frontend/src/app/features/billing/`: órdenes, pagos, descuentos y vinculación de productos de receta.
- `frontend/src/app/features/admin/pages/reportes/reportes.component.ts`.
