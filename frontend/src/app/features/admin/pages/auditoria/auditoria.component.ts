import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { JsonPipe } from '@angular/common';
import { AuditEvent, OperationsApiService, operationError } from '../../services/operations-api.service';
import { PageHeaderComponent } from '../../shared/page-header.component';

@Component({ standalone: true, imports: [FormsModule, JsonPipe, PageHeaderComponent], styleUrl: '../../shared/admin-ui.css', template: `
  <admin-page-header title="Auditoría de acciones" description="Eventos transaccionales de la sede: autor, fecha, entidad y cambios. Se excluyen contraseñas, comprobantes y notas privadas." />
  @if (error()) { <p class="mb-4 rounded-xl bg-rose-50 p-4 text-rose-700" role="alert">{{ error() }}</p> }
  <form class="admin-card mb-5 grid gap-3 p-4 sm:grid-cols-5" #filters="ngForm" (ngSubmit)="load()">
    <label>Desde<input required type="date" class="admin-input" name="from" [(ngModel)]="from"></label><label>Hasta<input required type="date" class="admin-input" name="to" [(ngModel)]="to"></label>
    <label>ID de autor<input type="number" min="1" class="admin-input" name="user" [(ngModel)]="userId"></label>
    <label>Entidad<select class="admin-input" name="entity" [(ngModel)]="entity"><option value="">Todas</option>@for (name of entities; track name) { <option [value]="name">{{ name }}</option> }</select></label><button class="admin-primary" [disabled]="loading() || filters.invalid">Consultar</button>
  </form>
  @if (loading()) { <p role="status">Cargando auditoría…</p> }
  <section class="admin-card overflow-x-auto p-4"><p class="text-sm text-slate-500">{{ rows().length }} eventos · máximo 2000 por consulta; usa un rango menor para consultar más detalle.</p><table class="admin-table"><thead><tr><th>Fecha (Perú)</th><th>Autor</th><th>Acción</th><th>Entidad / registro</th><th>Cambios</th></tr></thead><tbody>@for (item of rows(); track item.id) { <tr><td>{{ date(item.fecha) }}</td><td>{{ item.autor }} (#{{ item.usuario_id || 'sistema' }})</td><td>{{ item.accion }}</td><td>{{ item.entidad }} #{{ item.registro_id }}</td><td><details><summary class="cursor-pointer font-bold text-teal-700">Ver antes / después</summary><pre class="max-w-xl whitespace-pre-wrap break-all text-xs">{{ item.cambios | json }}</pre></details></td></tr> } @empty { <tr><td colspan="5">Sin eventos para los filtros indicados.</td></tr> }</tbody></table></section>
` })
export class AuditoriaComponent {
  private readonly api = inject(OperationsApiService);
  readonly rows = signal<AuditEvent[]>([]); readonly error = signal(''); readonly loading = signal(false);
  readonly entities = ['usuarios', 'permisos_rol', 'productos', 'ajustes_inventario', 'citas', 'ordenes_cobro', 'ordenes_pendientes', 'abonos_orden', 'cajas', 'compras_proveedor', 'movimientos_inventario', 'lotes_inventario', 'egresos', 'politicas_clinica', 'horarios_veterinarios', 'unidades_medida', 'solicitudes_reprogramacion', 'configuracion_clinica'];
  to = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima' }).format(new Date()); from = this.to.slice(0, 8) + '01'; userId: number | null = null; entity = '';
  constructor() { this.load(); }
  load() { this.loading.set(true); this.error.set(''); this.rows.set([]); const params: Record<string, string> = { desde: this.from, hasta: this.to }; if (this.userId) params['usuario_id'] = String(this.userId); if (this.entity) params['entidad'] = this.entity; this.api.audit(params).subscribe({ next: rows => { this.rows.set(rows); this.loading.set(false); }, error: error => { this.error.set(operationError(error)); this.loading.set(false); } }); }
  date(value: string) { return new Intl.DateTimeFormat('es-PE', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Lima' }).format(new Date(value)); }
}
