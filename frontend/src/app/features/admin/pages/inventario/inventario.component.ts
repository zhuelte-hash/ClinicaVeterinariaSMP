import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { NoticeService } from '../../../../core/services/notice.service';
import { AdminApiService, AdminProduct } from '../../services/admin-api.service';
import { PageHeaderComponent } from '../../shared/page-header.component';

@Component({ selector: 'app-admin-inventario', standalone: true, imports: [FormsModule, PageHeaderComponent], templateUrl: './inventario.component.html', styleUrl: '../../shared/admin-ui.css' })
export class InventarioComponent {
  private readonly api = inject(AdminApiService);
  private readonly notice = inject(NoticeService);
  readonly query = signal('');
  readonly onlyLow = signal(false);
  readonly editing = signal<AdminProduct | null>(null);
  readonly products = signal<AdminProduct[]>([]);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly error = signal('');
  stock = 0;
  readonly items = computed(() => {
    const q = this.query().trim().toLowerCase();
    return this.products().filter((item) =>
      (!q || `${item.nombre} ${item.sku}`.toLowerCase().includes(q))
      && (!this.onlyLow() || item.stock_actual <= item.stock_minimo));
  });
  readonly lowCount = computed(() => this.products().filter((item) => item.stock_actual <= item.stock_minimo).length);
  readonly units = computed(() => this.products().reduce((sum, item) => sum + item.stock_actual, 0));

  constructor() { this.load(); }
  load(): void {
    this.loading.set(true);
    this.api.getInventory().pipe(finalize(() => this.loading.set(false))).subscribe({
      next: (products) => { this.products.set(products); this.error.set(''); },
      error: (error: unknown) => this.error.set(this.errorText(error)),
    });
  }
  edit(item: AdminProduct): void { this.editing.set(item); this.stock = item.stock_actual; this.error.set(''); }
  save(): void {
    const item = this.editing();
    if (!item || this.saving() || !Number.isInteger(this.stock) || this.stock < 0) {
      this.error.set('Ingresa una cantidad entera mayor o igual a cero.');
      return;
    }
    this.saving.set(true);
    this.api.updateStock(item.id, this.stock).pipe(finalize(() => this.saving.set(false))).subscribe({
      next: (updated) => {
        this.products.update((items) => items.map((product) => product.id === updated.id ? updated : product));
        this.editing.set(null);
        this.notice.show('Existencia actualizada');
      },
      error: (error: unknown) => this.error.set(this.errorText(error)),
    });
  }
  private errorText(error: unknown): string {
    return error instanceof HttpErrorResponse && typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudo actualizar el inventario.';
  }
}
