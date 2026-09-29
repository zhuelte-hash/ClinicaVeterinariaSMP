import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize, forkJoin } from 'rxjs';
import { AdminApiService, SaleDetail, SalesFilters, SalesPage, SalesSummary } from '../../services/admin-api.service';
import { PageHeaderComponent } from '../../shared/page-header.component';

@Component({ selector: 'app-admin-ventas', standalone: true, imports: [FormsModule, PageHeaderComponent], templateUrl: './ventas.component.html', styleUrl: '../../shared/admin-ui.css', changeDetection: ChangeDetectionStrategy.OnPush })
export class VentasComponent {
  private readonly api = inject(AdminApiService);
  filters: SalesFilters = { pagina: 1, tamano_pagina: 20 };
  readonly page = signal<SalesPage | null>(null);
  readonly summary = signal<SalesSummary | null>(null);
  readonly selected = signal<SaleDetail | null>(null);
  readonly loading = signal(false);
  readonly error = signal('');
  readonly actionError = signal('');
  readonly saving = signal(false);

  constructor() { this.load(); }
  search(): void { this.filters.pagina = 1; this.load(); }
  load(): void {
    this.loading.set(true);
    forkJoin({ page: this.api.getSales(this.filters), summary: this.api.getSalesSummary(this.filters) })
      .pipe(finalize(() => this.loading.set(false))).subscribe({
        next: ({ page, summary }) => { this.page.set(page); this.summary.set(summary); this.error.set(''); },
        error: (error: unknown) => this.error.set(this.errorText(error)),
      });
  }
  changePage(page: number): void { this.filters.pagina = page; this.load(); }
  view(id: number): void { this.actionError.set(''); this.api.getSale(id).subscribe({
    next: (sale) => this.selected.set(sale), error: (error: unknown) => this.error.set(this.errorText(error)),
  }); }
  voidSale(): void {
    const sale = this.selected();
    if (!sale || !window.confirm(`¿Anular la venta ${sale.codigo_orden}? Se devolverá el stock.`)) return;
    this.saving.set(true); this.actionError.set('');
    this.api.voidSale(sale.id).pipe(finalize(() => this.saving.set(false))).subscribe({
      next: (updated) => { this.selected.set(updated); this.load(); },
      error: (error: unknown) => this.actionError.set(this.errorText(error)),
    });
  }
  exportCsv(): void {
    const headers = ['Número', 'Fecha', 'Cajero', 'Cliente', 'Método', 'Subtotal', 'Descuento', 'Impuesto', 'Total', 'Estado'];
    const rows = (this.page()?.ventas ?? []).map(s => [s.codigo_orden, s.fecha_emision, s.cajero_nombre, s.cliente_nombre ?? '', s.medio_pago, s.subtotal, s.descuento, s.impuesto, s.total, s.estado]);
    const csv = [headers, ...rows].map(row => row.map(value => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a'); link.href = url; link.download = 'ventas-pagina.csv'; link.click(); URL.revokeObjectURL(url);
  }
  formatDate(value: string): string { return new Intl.DateTimeFormat('es-PE', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Lima' }).format(new Date(value)); }
  money(value: string): string { return Number(value).toFixed(2); }
  private errorText(error: unknown): string { return error instanceof HttpErrorResponse && typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudo completar la operación.'; }
}
