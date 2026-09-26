import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { finalize, forkJoin } from 'rxjs';
import { CashierApiService } from './cashier-api.service';
import {
  CashierCategory,
  CashierClient,
  CashierProduct,
  CashierService,
  Receipt,
} from './cashier.models';

interface SaleCartItem {
  type: 'product' | 'service';
  id: number;
  code: string;
  name: string;
  price: number;
  stock: number | null;
  quantity: number;
}

type PaymentMethod = 'efectivo' | 'yape' | 'plin' | 'tarjeta';

@Component({
  selector: 'app-cashier-sales',
  standalone: true,
  imports: [FormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="mx-auto max-w-[1500px]">
      <header class="mb-6 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div><p class="text-xs font-black uppercase tracking-[.18em] text-[#168ba1]">Venta presencial</p><h2 class="mt-2 text-3xl font-black text-[#111827]">Punto de venta</h2><p class="mt-2 text-sm text-slate-500">Cobra productos y servicios en una sola boleta.</p></div>
        <button (click)="loadData()" class="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold">Actualizar catálogo</button>
      </header>

      @if (errorMessage()) { <p class="mb-5 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm font-semibold text-rose-700">{{ errorMessage() }}</p> }
      @if (!registerOpen() && !loading()) { <div class="mb-6 flex flex-col gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-5 sm:flex-row sm:items-center sm:justify-between"><div><b class="text-amber-900">Debes abrir una caja antes de vender</b><p class="mt-1 text-sm text-amber-700">El cobro no se procesará hasta iniciar el turno.</p></div><a routerLink="../dashboard" class="rounded-xl bg-amber-500 px-5 py-2.5 text-center font-black text-white">Abrir caja</a></div> }

      <div class="grid gap-6 xl:grid-cols-[1fr_390px]">
        <div>
          <div class="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div class="mb-4 grid grid-cols-2 gap-2 rounded-xl bg-slate-100 p-1">
              <button (click)="catalogMode.set('products')" class="mode-button" [class.mode-active]="catalogMode() === 'products'">Productos</button>
              <button (click)="catalogMode.set('services')" class="mode-button" [class.mode-active]="catalogMode() === 'services'">Servicios de atención</button>
            </div>
            <div class="grid gap-3 md:grid-cols-[1fr_auto]">
              <input [ngModel]="search()" (ngModelChange)="search.set($event)" [placeholder]="catalogMode() === 'products' ? 'Buscar producto o SKU...' : 'Buscar servicio...'" class="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-[#56c4d8] focus:ring-2 focus:ring-[#56c4d8]/20">
              @if (catalogMode() === 'products') { <div class="flex max-w-full gap-2 overflow-x-auto"><button (click)="selectedCategory.set(null)" class="category-button" [class.category-active]="selectedCategory() === null">Todos</button>@for (category of categories(); track category.id) {<button (click)="selectedCategory.set(category.id)" class="category-button" [class.category-active]="selectedCategory() === category.id">{{ category.nombre }}</button>}</div> }
            </div>
          </div>

          @if (loading()) { <p class="py-20 text-center text-slate-500">Cargando catálogo...</p> }
          @else {
            <div class="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              @if (catalogMode() === 'products') {
                @for (product of filteredProducts(); track product.id) {
                  <article class="catalog-card"><div class="flex items-start justify-between gap-3"><span class="item-icon bg-[#56c4d8]/15 text-[#111827]">{{ product.nombre.charAt(0) }}</span><span class="stock-badge" [class.low-stock]="product.stock_actual <= 5">Stock {{ product.stock_actual }}</span></div><p class="item-code">{{ product.sku }} · {{ product.categoria.nombre }}</p><h3 class="item-name">{{ product.nombre }}</h3><div class="mt-4 flex items-center justify-between"><b class="text-xl text-[#168ba1]">S/ {{ money(product.precio_venta) }}</b><button (click)="addProduct(product)" [disabled]="product.stock_actual === 0 || !registerOpen()" class="add-button bg-[#111827] hover:bg-[#56c4d8] hover:text-[#111827]">+</button></div></article>
                } @empty { <p class="col-span-full py-16 text-center text-slate-500">No hay productos con esos filtros.</p> }
              } @else {
                @for (service of filteredServices(); track service.id) {
                  <article class="catalog-card border-sky-200"><div class="flex items-start justify-between gap-3"><span class="item-icon bg-sky-50 text-sky-700">+</span><span class="rounded-full bg-sky-100 px-2.5 py-1 text-xs font-bold text-sky-700">{{ service.duracion_estimada_min }} min</span></div><p class="item-code">{{ service.codigo }}</p><h3 class="item-name">{{ service.nombre }}</h3><p class="mt-2 min-h-10 text-xs leading-5 text-slate-500">{{ service.descripcion }}</p><div class="mt-4 flex items-center justify-between"><b class="text-xl text-sky-700">S/ {{ money(service.precio_referencial) }}</b><button (click)="addService(service)" [disabled]="!registerOpen()" class="add-button bg-sky-700 hover:bg-sky-600">+</button></div></article>
                } @empty { <p class="col-span-full py-16 text-center text-slate-500">No hay servicios con ese filtro.</p> }
              }
            </div>
          }
        </div>

        <aside class="h-fit rounded-3xl border border-slate-200 bg-white shadow-lg xl:sticky xl:top-24">
          <div class="border-b border-slate-100 p-5"><div class="flex items-center justify-between"><h3 class="text-xl font-black text-[#111827]">Venta actual</h3><span class="rounded-full bg-[#56c4d8]/15 px-3 py-1 text-xs font-bold text-[#168ba1]">{{ cartCount() }} items</span></div></div>
          <div class="max-h-72 space-y-3 overflow-y-auto p-5">
            @for (item of cart(); track item.type + '-' + item.id) {
              <div class="rounded-xl bg-slate-50 p-3"><div class="flex gap-3"><div class="min-w-0 flex-1"><p class="truncate text-sm font-bold text-slate-800">{{ item.name }}</p><p class="text-xs text-slate-500">{{ item.type === 'service' ? 'Servicio' : item.code }} · S/ {{ item.price.toFixed(2) }}</p></div><button (click)="removeItem(item.type, item.id)" class="text-xs font-bold text-rose-600">Quitar</button></div><div class="mt-3 flex items-center justify-between"><div class="flex items-center gap-2"><button (click)="setQuantity(item.type, item.id, item.quantity - 1)" class="quantity-button">−</button><b>{{ item.quantity }}</b><button (click)="setQuantity(item.type, item.id, item.quantity + 1)" [disabled]="item.stock !== null && item.quantity >= item.stock" class="quantity-button">+</button></div><b>S/ {{ lineTotal(item) }}</b></div></div>
            } @empty { <div class="py-8 text-center"><p class="text-3xl">▤</p><p class="mt-2 text-sm font-semibold text-slate-500">Agrega productos o servicios</p></div> }
          </div>

          <div class="space-y-5 border-t border-slate-100 p-5">
            <label class="grid gap-2 text-sm font-bold">Cliente<select [ngModel]="selectedClientId()" (ngModelChange)="selectedClientId.set(+$event)" class="rounded-xl border border-slate-300 bg-white px-3 py-3 font-normal"><option [ngValue]="0">Selecciona un cliente</option>@for (client of clients(); track client.id) {<option [ngValue]="client.id">{{ client.nombre }} · {{ client.correo }}</option>}</select></label>
            <div><p class="mb-2 text-sm font-bold">Método de pago</p><div class="grid grid-cols-2 gap-2">@for (method of paymentMethods; track method.value) {<button (click)="paymentMethod.set(method.value)" class="payment-button" [class.payment-active]="paymentMethod() === method.value">{{ method.label }}</button>}</div></div>
            <div class="rounded-2xl bg-[#111827] p-4 text-white shadow-lg"><div class="flex justify-between text-sm text-slate-300"><span>Subtotal</span><span>S/ {{ subtotalWithoutTax() }}</span></div><div class="mt-2 flex justify-between text-sm text-slate-300"><span>IGV (18%)</span><span>S/ {{ tax() }}</span></div><div class="mt-3 flex justify-between border-t border-white/15 pt-3 text-xl font-black"><span>Total</span><span class="text-[#56c4d8]">S/ {{ total() }}</span></div></div>
            <button (click)="charge()" [disabled]="!canCharge() || charging()" class="w-full rounded-xl bg-[#56c4d8] px-5 py-3.5 font-black text-[#111827] transition hover:bg-[#111827] hover:text-white disabled:cursor-not-allowed disabled:opacity-40">{{ charging() ? 'Procesando...' : 'Cobrar y generar boleta' }}</button>
          </div>
        </aside>
      </div>
    </section>

    @if (receipt(); as currentReceipt) {
      <div class="fixed inset-0 z-[100] grid place-items-center bg-slate-950/70 p-4 backdrop-blur-sm"><section class="max-h-[94vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white shadow-2xl"><div class="no-print flex items-center justify-between border-b p-4"><h2 class="font-black text-[#102a43]">Venta completada</h2><button (click)="receipt.set(null)" class="rounded-lg p-2 hover:bg-slate-100">✕</button></div><div class="print-receipt p-7 font-mono text-sm text-slate-900"><div class="text-center"><img src="/logo.png" alt="Logo" class="mx-auto h-16 w-16 rounded-full"><h2 class="mt-3 text-lg font-black">CLINICA VETERINARIA SMP</h2><p>Jr. Quinua N° 178 · Ayacucho</p><p>BOLETA {{ currentReceipt.serie_correlativo }}</p></div><div class="my-5 border-y border-dashed border-slate-400 py-3"><p>Fecha: {{ formatDate(currentReceipt.fecha_emision) }}</p><p>Cliente: {{ currentReceipt.cliente_nombre }}</p><p>Cajero: {{ currentReceipt.cajero_nombre }}</p><p>Pago: {{ paymentLabel(currentReceipt.medio_pago) }}</p></div><table class="w-full"><thead><tr class="border-b"><th class="py-2 text-left">Detalle</th><th>Cant.</th><th class="text-right">Importe</th></tr></thead><tbody>@for (detail of currentReceipt.detalles; track detail.tipo + '-' + (detail.producto_id || detail.servicio_id)) {<tr><td class="py-2">{{ detail.nombre }}<small class="block text-[10px] uppercase">{{ detail.tipo }}</small></td><td class="text-center">{{ detail.cantidad }}</td><td class="text-right">S/ {{ money(detail.subtotal) }}</td></tr>}</tbody></table><div class="mt-4 border-t border-dashed border-slate-400 pt-3 text-right"><p>Subtotal: S/ {{ money(currentReceipt.subtotal) }}</p><p>IGV: S/ {{ money(currentReceipt.igv) }}</p><p class="mt-1 text-lg font-black">TOTAL: S/ {{ money(currentReceipt.total) }}</p></div><p class="mt-6 text-center">¡Gracias por su compra!</p></div><div class="no-print grid grid-cols-2 gap-3 border-t p-4"><button (click)="receipt.set(null)" class="rounded-xl border border-slate-300 px-4 py-3 font-bold">Cerrar</button><button (click)="printReceipt()" class="rounded-xl bg-[#102a43] px-4 py-3 font-black text-white">Imprimir boleta</button></div></section></div>
    }
  `,
  styles: [`
    .mode-button { border-radius: .5rem; padding: .65rem 1rem; font-size: .875rem; font-weight: 900; color: #64748b; }
    .mode-active { background: white; color: #111827; box-shadow: inset 0 -2px #56c4d8, 0 1px 3px rgb(15 23 42 / .12); }
    .category-button { white-space: nowrap; border: 1px solid #cbd5e1; border-radius: .75rem; padding: .7rem .9rem; font-size: .75rem; font-weight: 800; color: #475569; }
    .category-active { border-color: #56c4d8; background: #eefbfc; color: #111827; }
    .catalog-card { border: 1px solid #e2e8f0; border-radius: 1rem; background: white; padding: 1.25rem; box-shadow: 0 1px 3px rgb(15 23 42 / .05); transition: .2s; }
    .catalog-card:hover { border-color: #56c4d8; transform: translateY(-2px); box-shadow: 0 8px 20px rgb(15 23 42 / .08); }
    .item-icon { display: grid; width: 2.75rem; height: 2.75rem; place-items: center; border-radius: .75rem; font-weight: 900; }
    .stock-badge { border-radius: 999px; background: #d1fae5; padding: .25rem .625rem; color: #047857; font-size: .75rem; font-weight: 800; }
    .low-stock { background: #fef3c7; color: #92400e; }
    .item-code { margin-top: 1rem; color: #94a3b8; font-size: .7rem; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
    .item-name { margin-top: .5rem; min-height: 3rem; color: #111827; font-weight: 900; line-height: 1.5rem; }
    .add-button { display: grid; width: 2.5rem; height: 2.5rem; place-items: center; border-radius: .75rem; color: white; font-size: 1.25rem; font-weight: 900; }
    .add-button:disabled { opacity: .3; }
    .quantity-button { display: grid; width: 1.8rem; height: 1.8rem; place-items: center; border: 1px solid #cbd5e1; border-radius: .5rem; background: white; font-weight: 900; }
    .quantity-button:disabled { opacity: .35; }
    .payment-button { border: 1px solid #e2e8f0; border-radius: .75rem; padding: .625rem .75rem; font-size: .875rem; font-weight: 800; }
    .payment-active { border-color: #56c4d8; background: #eefbfc; color: #111827; box-shadow: inset 0 0 0 1px #56c4d8; }
  `],
})
export class CashierSalesComponent {
  private readonly api = inject(CashierApiService);
  readonly products = signal<CashierProduct[]>([]);
  readonly services = signal<CashierService[]>([]);
  readonly categories = signal<CashierCategory[]>([]);
  readonly clients = signal<CashierClient[]>([]);
  readonly cart = signal<SaleCartItem[]>([]);
  readonly catalogMode = signal<'products' | 'services'>('products');
  readonly search = signal('');
  readonly selectedCategory = signal<number | null>(null);
  readonly selectedClientId = signal(0);
  readonly paymentMethod = signal<PaymentMethod>('efectivo');
  readonly registerOpen = signal(false);
  readonly loading = signal(true);
  readonly charging = signal(false);
  readonly errorMessage = signal('');
  readonly receipt = signal<Receipt | null>(null);
  readonly paymentMethods: { value: PaymentMethod; label: string }[] = [
    { value: 'efectivo', label: 'Efectivo' }, { value: 'yape', label: 'Yape' },
    { value: 'plin', label: 'Plin' }, { value: 'tarjeta', label: 'Tarjeta' },
  ];
  readonly filteredProducts = computed(() => {
    const query = this.search().trim().toLowerCase();
    return this.products().filter((product) =>
      (this.selectedCategory() === null || product.categoria.id === this.selectedCategory())
      && (!query || product.nombre.toLowerCase().includes(query) || product.sku.toLowerCase().includes(query))
    );
  });
  readonly filteredServices = computed(() => {
    const query = this.search().trim().toLowerCase();
    return this.services().filter((service) =>
      !query || service.nombre.toLowerCase().includes(query) || service.codigo.toLowerCase().includes(query)
    );
  });
  readonly cartCount = computed(() => this.cart().reduce((sum, item) => sum + item.quantity, 0));
  readonly totalValue = computed(() => this.cart().reduce((sum, item) => sum + item.price * item.quantity, 0));
  readonly total = computed(() => this.totalValue().toFixed(2));
  readonly subtotalWithoutTax = computed(() => (this.totalValue() / 1.18).toFixed(2));
  readonly tax = computed(() => (this.totalValue() - this.totalValue() / 1.18).toFixed(2));
  readonly canCharge = computed(() => this.registerOpen() && this.cart().length > 0 && this.selectedClientId() > 0);

  constructor() { this.loadData(); }

  loadData(): void {
    this.loading.set(true);
    this.errorMessage.set('');
    forkJoin({ products: this.api.getProducts(), services: this.api.getServices(), categories: this.api.getCategories(), clients: this.api.getClients(), summary: this.api.getSummary() })
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: ({ products, services, categories, clients, summary }) => {
          this.products.set(products); this.services.set(services); this.categories.set(categories);
          this.clients.set(clients); this.registerOpen.set(summary.caja !== null);
        },
        error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
      });
  }

  addProduct(product: CashierProduct): void {
    this.addItem({ type: 'product', id: product.id, code: product.sku, name: product.nombre, price: Number(product.precio_venta), stock: product.stock_actual, quantity: 1 });
  }

  addService(service: CashierService): void {
    this.addItem({ type: 'service', id: service.id, code: service.codigo, name: service.nombre, price: Number(service.precio_referencial), stock: null, quantity: 1 });
  }

  addItem(newItem: SaleCartItem): void {
    this.cart.update((items) => {
      const existing = items.find((item) => item.type === newItem.type && item.id === newItem.id);
      if (!existing) return [...items, newItem];
      return items.map((item) => item === existing
        ? { ...item, quantity: item.stock === null ? item.quantity + 1 : Math.min(item.stock, item.quantity + 1) }
        : item);
    });
  }

  removeItem(type: SaleCartItem['type'], id: number): void {
    this.cart.update((items) => items.filter((item) => item.type !== type || item.id !== id));
  }

  setQuantity(type: SaleCartItem['type'], id: number, quantity: number): void {
    if (quantity <= 0) { this.removeItem(type, id); return; }
    this.cart.update((items) => items.map((item) => item.type === type && item.id === id
      ? { ...item, quantity: item.stock === null ? quantity : Math.min(item.stock, quantity) }
      : item));
  }

  lineTotal(item: SaleCartItem): string { return (item.price * item.quantity).toFixed(2); }
  money(value: string): string { return Number(value).toFixed(2); }

  charge(): void {
    if (!this.canCharge()) return;
    this.charging.set(true);
    this.errorMessage.set('');
    this.api.createSale({
      cliente_id: this.selectedClientId(),
      medio_pago: this.paymentMethod(),
      items: this.cart().map((item) => item.type === 'product'
        ? { producto_id: item.id, cantidad: item.quantity }
        : { servicio_id: item.id, cantidad: item.quantity }),
    }).pipe(finalize(() => this.charging.set(false))).subscribe({
      next: (receipt) => { this.receipt.set(receipt); this.cart.set([]); this.loadData(); },
      error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
  }

  printReceipt(): void { window.print(); }
  formatDate(value: string): string { return new Intl.DateTimeFormat('es-PE', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Lima' }).format(new Date(value)); }
  paymentLabel(value: string): string { return this.paymentMethods.find((method) => method.value === value)?.label ?? value; }
  private errorText(error: unknown): string { return error instanceof HttpErrorResponse && typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudo completar la operación.'; }
}
