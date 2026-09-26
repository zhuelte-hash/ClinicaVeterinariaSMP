import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { AdminApiService, AdminSale, SalesDay } from '../../services/admin-api.service';
import { PageHeaderComponent } from '../../shared/page-header.component';

@Component({ selector: 'app-admin-ventas', standalone: true, imports: [FormsModule, PageHeaderComponent], templateUrl: './ventas.component.html', styleUrl: '../../shared/admin-ui.css', changeDetection: ChangeDetectionStrategy.OnPush })
export class VentasComponent {
  private readonly api = inject(AdminApiService);
  readonly date = signal(new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima' }).format(new Date())); readonly query = signal(''); readonly report = signal<SalesDay | null>(null); readonly loading = signal(true); readonly error = signal('');
  readonly filtered = computed(() => { const query = this.query().trim().toLowerCase(); return (this.report()?.ventas ?? []).filter((sale) => !query || `${sale.codigo_orden} ${sale.cliente_nombre ?? ''} ${sale.cajero_nombre}`.toLowerCase().includes(query)); });
  readonly total = computed(() => this.filtered().reduce((sum, item) => sum + item.total, 0));
  constructor() { this.load(); }
  load(): void { this.loading.set(true); this.api.getSalesDay(this.date()).pipe(finalize(() => this.loading.set(false))).subscribe({ next: (report) => { this.report.set(report); this.error.set(''); }, error: (error: unknown) => this.error.set(this.errorText(error)) }); }
  formatTime(value: string): string { return new Intl.DateTimeFormat('es-PE', { timeStyle: 'short', timeZone: 'America/Lima' }).format(new Date(value)); }
  private errorText(error: unknown): string { return error instanceof HttpErrorResponse && typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudieron consultar las ventas.'; }
}
