import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { InventoryValuation, Numeric, OperationsApiService, operationError } from '../../services/operations-api.service';

@Component({
  selector: 'app-inventory-valuation', standalone: true, imports: [FormsModule], styleUrl: '../../shared/admin-ui.css',
  template: `<section class="admin-card mb-5 space-y-3 p-4" aria-labelledby="valuation-title">
    <h2 id="valuation-title" class="text-xl font-bold">Inventario valorizado al costo</h2><button type="button" class="admin-secondary" (click)="load()" [disabled]="loading()">Actualizar valorización</button>
    @if (error()) { <p role="alert" class="text-rose-700">{{ error() }}</p> }
    @if (loading()) { <p role="status">Calculando valor del inventario…</p> }
    @if (data(); as report) {
      <p>{{ report.metodo }}</p><p class="text-sm text-slate-500">{{ report.criterio }}</p>
      <p class="text-lg">Capital total registrado: <b>S/ {{ money(report.total) }}</b></p>
      @if (report.sin_costo) { <p class="rounded-xl bg-amber-50 p-3 text-amber-900">{{ report.sin_costo }} productos con existencias y costo cero. Revisa sus costos de compra; este total puede estar incompleto.</p> }
      <label class="block">Buscar en valorización<input class="admin-input" [ngModel]="query()" (ngModelChange)="query.set($event)" placeholder="Producto o SKU"></label>
      <label class="flex gap-2"><input type="checkbox" [ngModel]="missingOnly()" (ngModelChange)="missingOnly.set($event)">Solo costo pendiente de revisión</label>
      <p>Subtotal del filtro: S/ {{ money(subtotal()) }} · {{ items().length }} productos</p>
      <div class="overflow-x-auto"><table class="admin-table"><thead><tr><th>Producto / SKU</th><th>Estado</th><th>Cantidad</th><th>Unidad</th><th>Costo unitario S/</th><th>Valor al costo S/</th></tr></thead><tbody>@for (row of items(); track row.id) { <tr><td>{{ row.producto }} · {{ row.sku }}</td><td>{{ row.activo ? 'Activo' : 'Inactivo' }}@if (row.costo_pendiente) { <small class="block text-amber-800">Costo pendiente de revisión</small> }</td><td>{{ row.cantidad }}</td><td>{{ row.unidad }}</td><td>{{ cost(row.costo) }}</td><td>{{ money(row.valor) }}</td></tr> } @empty { <tr><td colspan="6">Sin productos para estos filtros.</td></tr> }</tbody></table></div>
    }
  </section>`,
})
export class InventoryValuationComponent {
  private readonly api = inject(OperationsApiService); private version = 0;
  readonly data = signal<InventoryValuation | null>(null); readonly loading = signal(false); readonly error = signal(''); readonly query = signal(''); readonly missingOnly = signal(false);
  readonly items = computed(() => this.data()?.productos.filter(row => (!this.missingOnly() || row.costo_pendiente) && `${row.producto} ${row.sku}`.toLowerCase().includes(this.query().trim().toLowerCase())) || []);
  readonly subtotal = computed(() => this.items().reduce((sum, row) => sum + Math.round(Number(row.valor) * 100), 0) / 100);
  constructor() { this.load(); }
  load(): void { const version = ++this.version; this.loading.set(true); this.error.set(''); this.data.set(null); this.api.valuation().subscribe({ next: data => { if (version === this.version) { this.data.set(data); this.loading.set(false); } }, error: error => { if (version === this.version) { this.error.set(operationError(error)); this.loading.set(false); } } }); }
  money(value: Numeric): string { return Number(value).toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  cost(value: Numeric): string { return Number(value).toLocaleString('es-PE', { minimumFractionDigits: 4, maximumFractionDigits: 4 }); }
}
