import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize, forkJoin } from 'rxjs';
import { NoticeService } from '../../../../core/services/notice.service';
import { AdminApiService, AdminProduct, InventoryAdjustment } from '../../services/admin-api.service';
import { PageHeaderComponent } from '../../shared/page-header.component';
import { InventoryMovement, OperationsApiService, operationError } from '../../services/operations-api.service';
import { InventoryValuationComponent } from './inventory-valuation.component';

@Component({ selector: 'app-admin-inventario', standalone: true, imports: [FormsModule, PageHeaderComponent, InventoryValuationComponent], templateUrl: './inventario.component.html', styleUrl: '../../shared/admin-ui.css' })
export class InventarioComponent {
  private readonly api = inject(AdminApiService);
  private readonly operations = inject(OperationsApiService);
  readonly movements = signal<InventoryMovement[]>([]); readonly kardexLoading = signal(false); readonly kardexError = signal('');
  kardexProduct = 0; kardexStart = ''; kardexEnd = ''; kardexKind = ''; private kardexVersion = 0;
  private readonly notice = inject(NoticeService);
  readonly query = signal('');
  readonly onlyLow = signal(false);
  readonly editing = signal<AdminProduct | null>(null);
  readonly products = signal<AdminProduct[]>([]);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly error = signal('');
  stock = 0;
  reason = '';
  readonly adjustments = signal<InventoryAdjustment[]>([]);
  readonly items = computed(() => {
    const q = this.query().trim().toLowerCase();
    return this.products().filter((item) =>
      (!q || `${item.nombre} ${item.sku}`.toLowerCase().includes(q))
      && (!this.onlyLow() || item.stock_actual <= item.stock_minimo));
  });
  readonly lowCount = computed(() => this.products().filter((item) => item.stock_actual <= item.stock_minimo).length);
  readonly units = computed(() => {
    const totals = new Map<string, number>();
    for (const item of this.products()) totals.set(item.unidad_medida, (totals.get(item.unidad_medida) ?? 0) + item.stock_actual);
    return [...totals].map(([unit, total]) => `${total.toLocaleString('es-PE', { maximumFractionDigits: 3 })} ${unit}`).join(' · ') || 'Sin existencias';
  });

  constructor() { this.load(); }
  load(): void {
    this.loading.set(true);
    forkJoin({ products: this.api.getInventory(), adjustments: this.api.getStockAdjustments() }).pipe(finalize(() => this.loading.set(false))).subscribe({
      next: ({ products, adjustments }) => { this.products.set(products); this.adjustments.set(adjustments); this.error.set(''); },
      error: (error: unknown) => this.error.set(this.errorText(error)),
    });
  }
  edit(item: AdminProduct): void { this.editing.set(item); this.stock = item.stock_actual; this.reason = ''; this.error.set(''); }
  loadKardex(): void {
    const version = ++this.kardexVersion;
    this.movements.set([]); this.kardexError.set('');
    if (!this.kardexProduct) { this.kardexLoading.set(false); return; }
    if (this.kardexStart && this.kardexEnd && this.kardexStart > this.kardexEnd) { this.kardexLoading.set(false); this.kardexError.set('La fecha inicial no puede ser posterior a la final.'); return; }
    const params: Record<string, string> = {};
    if (this.kardexStart) params['desde'] = this.kardexStart;
    if (this.kardexEnd) params['hasta'] = this.kardexEnd;
    if (this.kardexKind) params['tipo'] = this.kardexKind;
    this.kardexLoading.set(true);
    this.operations.kardex(this.kardexProduct, params).subscribe({ next: rows => { if (version === this.kardexVersion) { this.movements.set(rows); this.kardexLoading.set(false); } }, error: error => { if (version === this.kardexVersion) { this.kardexError.set(operationError(error)); this.kardexLoading.set(false); } } });
  }
  movementDate(value: string): string { return new Intl.DateTimeFormat('es-PE', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Lima' }).format(new Date(value)); }
  save(): void {
    const item = this.editing();
    if (!item || this.saving() || !Number.isFinite(this.stock) || (!item.fraccionable && !Number.isInteger(this.stock)) || this.stock < 0) {
      this.error.set('Ingresa una cantidad mayor o igual a cero que respete la unidad del producto.');
      return;
    }
    if (this.reason.trim().length < 3) { this.error.set('Indica el motivo del ajuste (mínimo 3 caracteres).'); return; }
    this.saving.set(true);
    this.api.updateStock(item.id, this.stock, item.stock_actual, this.reason.trim()).pipe(finalize(() => this.saving.set(false))).subscribe({
      next: (updated) => {
        this.products.update((items) => items.map((product) => product.id === updated.id ? updated : product));
        this.editing.set(null);
        this.notice.show('Existencia actualizada');
        this.load();
      },
      error: (error: unknown) => this.error.set(this.errorText(error)),
    });
  }
  private errorText(error: unknown): string {
    return error instanceof HttpErrorResponse && typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudo actualizar el inventario.';
  }
}
