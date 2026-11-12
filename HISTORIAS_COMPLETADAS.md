# Historias completadas

## Estado actualizado: cierre de 10 parciales prioritarias

**Fecha:** 11 de noviembre de 2026. **Versión documental:** 2.1.

Se cerraron **HU-008, HU-065, HU-068, HU-070, HU-074, HU-076, HU-077, HU-080, HU-083 y HU-089**, seleccionadas por su impacto en accesos, cobros y seguimiento financiero.

| Estado documental | Antes | Ahora |
| --- | ---: | ---: |
| Implementadas / completadas | 54 | **64** |
| Parciales | 31 | **21** |
| Pendientes | 30 | **30** |
| Total | 115 | **115** |

Las 64 se componen de **39 implementadas originales y 25 cierres verificados**. Esta actualización reclasifica las diez historias seleccionadas; la evaluación de las demás conserva su fecha y alcance previos.

- Evidencias y recorridos: [HISTORIAS_PRIORITARIAS_COMPLETADAS.md](HISTORIAS_PRIORITARIAS_COMPLETADAS.md).
- Word actualizado: `Informe_Historias_Usuario_SMP_actualizado.docx`.
- Backend: **81 aprobadas y 11 omitidas**, incluidas **19 nuevas comprobaciones HTTP con autenticación real** en `backend/tests/test_priority_stories.py`.
- Frontend: `npm run build` correcto, con advertencias de tamaño y CommonJS.
- Interfaz: **16 comprobaciones en Edge** con API controlada, escritorio y móvil, sin errores JavaScript.
- Esquema requerido: `37ebf391ec82`, confirmado como head de la base configurada. Este lote reutiliza ese esquema.

## Registro histórico: cierre previo de 15 historias parciales

**Fecha:** 10 de noviembre de 2026.

**Informe:** `Informe_Historias_Usuario_SMP delcy.docx`, versión 2.0.

**Base de código:** `master`, `7fc913b`, más los cambios locales de esta actualización.

**Migración:** `20261110_24`, aplicada en la base configurada.

## Estado sincronizado

| Estado | Antes | Después |
| --- | ---: | ---: |
| Implementadas / completadas | 39 | **54** |
| Parciales | 46 | **31** |
| Pendientes | 30 | **30** |
| Total | 115 | **115** |

Las 15 historias pasan de **Parcial** a **Completada** en su fila del Word.
Las 39 implementadas de la revisión original conservan su clasificación.

## Historias y criterios de cierre

| Historia | Funcionalidad completada | Dónde verificar |
| --- | --- | --- |
| HU-012 | Descripción, precio referencial y duración desde el mismo catálogo persistido de reservas y caja. | `/servicios` → Ver más. |
| HU-015 | Detalle individual con imagen, descripción editable, precio y stock. | `/productos/:id`; descripción en Administración → Productos. |
| HU-017 | Filtros combinables de categoría, especie y rango de precios; validación de rangos. | `/productos`. Especies vacías en el producto significan uso general. |
| HU-020 | WhatsApp contextual con mensaje precargado en servicios médicos, estéticos y su detalle. | `/servicios` → Consultar por WhatsApp. Es apertura de conversación para envío manual. |
| HU-030 | Agenda de lunes a domingo, semanas anterior/siguiente, listado diario y filtros de estado. | Veterinaria → Citas → Vista semanal. |
| HU-038 | Inasistencia manual por el veterinario asignado, con tolerancia, motivo y responsable; impide marcar pacientes llegados o ya atendidos. | Veterinaria → Citas → No asistió, cuando transcurrió la tolerancia. |
| HU-042 | Urgencia visible, filtro, contador y prioridad en la gestión administrativa. | Administración → Citas. |
| HU-044 | Ficha maestra editable de identificación, nacimiento/edad, peso, alergias, condiciones y antecedentes; sincronización desde atenciones. | Veterinaria → Pacientes e historial → Ficha del paciente. |
| HU-046 | Edición por propietario y veterinario; carga/reemplazo de foto real con validación. | Cliente → Mis mascotas; Veterinaria → Ficha del paciente. |
| HU-054 | Gráfico cronológico de evolución del peso con fecha, kg y tabla de valores. | Veterinaria → Ficha del paciente → Evolución del peso. |
| HU-055 | Alergias y condiciones consolidadas y alerta explícita antes de una nueva consulta. | Atención programada, nueva atención presencial y ficha del paciente. |
| HU-075 | Transferencia bancaria en caja, esquema, base de datos, pagos mixtos, boleta y filtros de reportes; ingreso digital. | Caja → Punto de venta; Administración → Ventas → Medio de pago. |
| HU-087 | Rango de fechas inclusivo y resumen/gráfico de todas las citas por estado, total y urgentes. | Administración → Citas. El resumen corresponde al rango completo antes del filtro de estado. |
| HU-091 | Alta, edición y consulta de proveedores; asociación y cambio de proveedor de productos existentes. | Administración → Proveedores y Productos. |
| HU-113 | Ajuste de stock con motivo obligatorio, cantidades anterior/nueva, responsable y fecha; historial y rechazo de edición desactualizada. | Administración → Inventario → Ajustar e Historial de ajustes manuales. |

## Verificación ejecutada

- **Backend:** `backend/.venv/Scripts/python.exe -m pytest -q`, desde `backend`: **62 aprobadas y 11 omitidas**. Las omitidas requieren una `TEST_DATABASE_URL` de PostgreSQL de pruebas. Los nuevos flujos HTTP se verifican con datos aislados mediante `backend/tests/test_story_completion.py`.
- **Frontend:** `npm run build`, desde `frontend`: correcto. La compilación conserva advertencias de presupuesto del paquete y dependencias CommonJS.
- **Interfaz:** 16 comprobaciones automatizadas en Edge, con API controlada, escritorio y vista móvil; sin errores de JavaScript. Incluyen filtros/detalle, tarifas y WhatsApp, edición de mascota, agenda semanal, inasistencia, curva de peso, alertas clínicas, urgencias, proveedores y filtro de transferencia.
- **Base de datos:** `alembic upgrade head` aplicado y `alembic current` confirmado en `20261110_24`. La migración consolida alergias clínicas existentes y conserva los registros previos.
- **Sesión:** se corrigió la dependencia circular entre la restauración de `AuthService` y su interceptor, detectada al verificar la recarga de las rutas protegidas.

## Archivos de referencia

- `backend/alembic/versions/20261110_24_historias_parciales.py`
- `backend/tests/test_story_completion.py`
- `backend/app/routers/catalog.py`, `admin.py`, `appointments.py`, `sales.py`
- `backend/app/services/admin_service.py`, `appointment_service.py`
- `frontend/src/app/features/products/`
- `frontend/src/app/features/services/`
- `frontend/src/app/features/appointments/pet-editor.component.ts` y `my-pets.component.ts`
- `frontend/src/app/features/veterinarian/weight-evolution.component.ts` y `patient-alerts.component.ts`
- `frontend/src/app/features/admin/pages/citas/`, `proveedores/`, `inventario/` y `productos/`

El historial de ajustes documenta HU-113. El Kardex integral de HU-114 sigue pendiente de unificar ventas, recepciones, devoluciones y ajustes. El mantenimiento administrativo de servicios de HU-084 también conserva su estado pendiente.
