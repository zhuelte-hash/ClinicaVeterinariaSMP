import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ClosureDetail, ClosureReport, Numeric, OperationsApiService, operationError } from '../../services/operations-api.service';
import { PageHeaderComponent } from '../../shared/page-header.component';
import { clinicToday } from '../../../veterinarian/veterinarian.models';

@Component({
  selector: 'app-cash-closures', standalone: true, imports: [FormsModule, PageHeaderComponent], styleUrl: '../../shared/admin-ui.css',
  template: `<admin-page-header title="Cierres de caja" description="Supervisa todos los cajeros de la sede, con consolidado diario y diferencias de arqueo." />
    <form class="admin-card mb-4 flex flex-wrap items-end gap-3 p-4" (ngSubmit)="load()">
      <label>Desde<input type="date" class="admin-input" name="start" [(ngModel)]="start" required></label><label>Hasta<input type="date" class="admin-input" name="end" [(ngModel)]="end" required></label>
      <label>ID del cajero (opcional)<input type="number" class="admin-input" name="cashier" [(ngModel)]="cashier" min="1" step="1" placeholder="Todos los cajeros"></label>
      <button class="admin-primary" [disabled]="loading()">Consultar cierres</button>
    </form>
    @if (error()) { <p role="alert" class="mb-4 text-rose-700">{{ error() }}</p> }
    @if (loading()) { <p role="status">Consultando cierres…</p> }
    @if (report(); as data) {
      <p class="mb-4 text-sm text-slate-500">{{ data.criterio }}</p>
      <div class="mb-4 grid gap-3 sm:grid-cols-3"><div class="admin-card p-4">Cierres<b class="block text-2xl">{{ data.cantidad }}</b></div><div class="admin-card p-4">Efectivo contado<b class="block text-2xl">S/ {{ money(data.totales.efectivo_contado) }}</b></div><div class="admin-card p-4">Diferencia total<b class="block text-2xl">S/ {{ money(data.totales.diferencia) }}</b></div></div>
      <section class="admin-card mb-4 overflow-x-auto"><h2 class="p-4 text-lg font-bold">Consolidado diario</h2><table class="admin-table"><thead><tr><th>Día de cierre (Perú)</th><th>Cajas</th><th>Fondo</th><th>Ingreso efectivo</th><th>Ingreso digital</th><th>Esperado</th><th>Contado</th><th>Diferencia</th></tr></thead><tbody>@for (day of data.por_dia; track day.fecha) { <tr><td>{{ day.fecha }}</td><td>{{ day.cantidad }}</td><td>{{ money(day.fondo_inicial) }}</td><td>{{ money(day.ingresos_efectivo) }}</td><td>{{ money(day.ingresos_digitales) }}</td><td>{{ money(day.efectivo_esperado) }}</td><td>{{ money(day.efectivo_contado) }}</td><td>{{ money(day.diferencia) }}</td></tr> } @empty { <tr><td colspan="8">No hay cierres en este período.</td></tr> }</tbody></table></section>
      <section class="admin-card overflow-x-auto"><h2 class="p-4 text-lg font-bold">Detalle por caja y cajero</h2><table class="admin-table"><thead><tr><th>Caja / cajero</th><th>Apertura</th><th>Cierre</th><th>Efectivo esperado</th><th>Contado</th><th>Digital</th><th>Diferencia</th><th>Detalle</th></tr></thead><tbody>@for (item of data.cierres; track item.id) { <tr><td>#{{ item.id }} · {{ item.cajero }}</td><td>{{ date(item.fecha_apertura) }}</td><td>{{ date(item.fecha_cierre) }}</td><td>{{ money(item.efectivo_esperado) }}</td><td>{{ money(item.efectivo_contado) }}</td><td>{{ money(item.ingresos_digitales) }}</td><td>{{ money(item.diferencia) }}</td><td><button type="button" class="admin-secondary" (click)="show(item.id)">Ver caja #{{ item.id }}</button></td></tr> } @empty { <tr><td colspan="8">No hay cajas cerradas para estos filtros.</td></tr> }</tbody></table></section>
    }
    @if (detailLoading()) { <p role="status">Consultando movimientos de la caja…</p> }
    @if (detail(); as item) { <section class="admin-card mt-4 overflow-x-auto"><h2 class="p-4 text-lg font-bold">Movimientos de caja #{{ item.id }} · {{ item.cajero }}</h2><table class="admin-table"><thead><tr><th>Fecha</th><th>Referencia</th><th>Medio</th><th>Monto</th><th>Concepto</th></tr></thead><tbody>@for (row of item.movimientos; track $index) { <tr><td>{{ date(row.fecha) }}</td><td>{{ row.referencia }}</td><td>{{ row.medio }}</td><td>{{ money(row.monto) }}</td><td>{{ row.motivo }}</td></tr> } @empty { <tr><td colspan="5">Sin ingresos netos registrados.</td></tr> }</tbody></table><button type="button" class="admin-secondary m-4" (click)="closeDetail()">Cerrar movimientos</button></section> }
  `,
})
export class CashClosuresComponent {
  private readonly api = inject(OperationsApiService); private version = 0; private detailVersion = 0;
  start = clinicToday().slice(0, 7) + '-01'; end = clinicToday(); cashier = '';
  readonly report = signal<ClosureReport | null>(null); readonly detail = signal<ClosureDetail | null>(null); readonly loading = signal(false); readonly detailLoading = signal(false); readonly error = signal('');
  constructor() { this.load(); }
  load(): void {
    if (!this.start || !this.end || this.start > this.end) { this.error.set('Selecciona un rango válido.'); return; }
    const version = ++this.version; this.closeDetail(); this.report.set(null); this.loading.set(true); this.error.set('');
    this.api.closures(this.start, this.end, String(this.cashier || '')).subscribe({ next: data => { if (version === this.version) { this.report.set(data); this.loading.set(false); } }, error: error => { if (version === this.version) { this.error.set(operationError(error)); this.loading.set(false); } } });
  }
  closeDetail(): void { ++this.detailVersion; this.detail.set(null); this.detailLoading.set(false); }
  show(id: number): void { const version = ++this.detailVersion; this.detail.set(null); this.detailLoading.set(true); this.error.set(''); this.api.closureDetail(id).subscribe({ next: data => { if (version === this.detailVersion) { this.detail.set(data); this.detailLoading.set(false); } }, error: error => { if (version === this.detailVersion) { this.error.set(operationError(error)); this.detailLoading.set(false); } } }); }
  money(value: Numeric): string { return Number(value).toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  date(value: string): string { return new Intl.DateTimeFormat('es-PE', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Lima' }).format(new Date(value)); }
}
