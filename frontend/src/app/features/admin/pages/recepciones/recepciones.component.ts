import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { AdminApiService, AdminProduct } from '../../services/admin-api.service';
import { Lot, OperationsApiService, operationError, PurchaseLine, Unit } from '../../services/operations-api.service';
import { PageHeaderComponent } from '../../shared/page-header.component';

@Component({ standalone: true, imports: [FormsModule, PageHeaderComponent], styleUrl: '../../shared/admin-ui.css', template: `
  <admin-page-header title="Recepción, lotes y unidades" description="Ingresa mercadería con documento, costo, lote y vencimiento. Las recepciones actualizan existencias y egresos." />
  @if (error()) { <p class="mb-4 rounded-xl bg-rose-50 p-4 text-rose-700" role="alert">{{ error() }}</p> }
  @if (message()) { <p class="mb-4 rounded-xl bg-teal-50 p-4 text-teal-800" role="status">{{ message() }}</p> }
  @if (loading()) { <p role="status">Cargando inventario…</p> }
  <form class="admin-card mb-6 grid gap-4 p-5" #receiptForm="ngForm" (ngSubmit)="receive()">
    <h2 class="text-xl font-bold">Recepción de proveedor</h2>
    <div class="grid gap-4 sm:grid-cols-2"><label>Proveedor<select required class="admin-input" name="supplier" [(ngModel)]="supplierId"><option [ngValue]="0">Selecciona</option>@for (supplier of suppliers(); track supplier.id) { <option [ngValue]="supplier.id">{{ supplier.razon_social }}</option> }</select></label><label>Documento del proveedor<input required minlength="3" maxlength="100" class="admin-input" name="document" [(ngModel)]="document"></label></div>
    @for (line of lines; track $index; let i = $index) {
      <fieldset class="grid gap-3 rounded-xl border p-4 sm:grid-cols-3"><legend>Artículo {{ i+1 }}</legend>
        <label>Producto<select required class="admin-input" [name]="'product'+i" [(ngModel)]="line.producto_id" (ngModelChange)="selectProduct(line)"><option [ngValue]="0">Selecciona</option>@for (product of products(); track product.id) { <option [ngValue]="product.id">{{ product.nombre }} ({{ product.unidad_medida }})</option> }</select></label>
        <label>Unidad recibida<select required class="admin-input" [name]="'unit'+i" [(ngModel)]="line.unidad">@for (unit of compatibleUnits(line.producto_id); track unit.codigo) { <option [ngValue]="unit.codigo">{{ unit.nombre }} ({{ unit.codigo }})</option> }</select></label>
        <label>Cantidad<input required type="number" min="0.001" step="0.001" class="admin-input" [name]="'quantity'+i" [(ngModel)]="line.cantidad"></label>
        <label>Costo por unidad recibida (S/)<input required type="number" min="0" step="0.0001" class="admin-input" [name]="'cost'+i" [(ngModel)]="line.costo_unitario"></label>
        <label>Lote<input required maxlength="100" class="admin-input" [name]="'lot'+i" [(ngModel)]="line.lote"></label>
        <label>Vencimiento<input type="date" class="admin-input" [name]="'expiry'+i" [(ngModel)]="line.vencimiento" [required]="requiresExpiry(line.producto_id)"><small>Obligatorio si el producto es medicamento o perecible.</small></label>
        <p class="text-sm text-slate-500 sm:col-span-2">{{ conversion(line) }}</p><button type="button" class="admin-secondary" [disabled]="lines.length === 1" (click)="lines.splice(i,1)">Quitar artículo</button>
      </fieldset>
    }
    <div class="flex flex-wrap gap-3"><button type="button" class="admin-secondary" (click)="addLine()">Agregar artículo</button><button class="admin-primary" [disabled]="busy() || loading() || receiptForm.invalid || !supplierId">Registrar recepción</button></div>
    <p class="text-sm text-slate-500">Las conversiones requieren unidades de la misma dimensión. Se rechazan lotes vencidos, documentos duplicados y fracciones en productos no fraccionables.</p>
  </form>
  <section class="admin-card mb-6 p-5">
    <div class="flex flex-wrap items-center justify-between gap-3"><h2 class="text-xl font-bold">Existencias por lote</h2><label><input type="checkbox" [(ngModel)]="expiring" (ngModelChange)="loadLots()"> Solo vencidos / próximos a vencer</label><button class="admin-secondary" (click)="loadLots()">Actualizar</button></div>
    <div class="overflow-x-auto"><table class="admin-table"><thead><tr><th>Producto</th><th>Lote</th><th>Vencimiento</th><th>Cantidad</th><th>Costo</th><th>Estado</th></tr></thead><tbody>@for (lot of lots(); track lot.id) { <tr><td>{{ lot.producto_nombre }}</td><td>{{ lot.codigo }}</td><td>{{ lot.vencimiento || 'Sin vencimiento' }}</td><td>{{ lot.cantidad }}</td><td>S/ {{ lot.costo_unitario }}</td><td>{{ lotState(lot) }}</td></tr> } @empty { <tr><td colspan="6">No hay lotes para el filtro.</td></tr> }</tbody></table></div>
  </section>
  <form class="admin-card grid gap-4 p-5 sm:grid-cols-3" #unitForm="ngForm" (ngSubmit)="createUnit()">
    <h2 class="text-xl font-bold sm:col-span-3">Unidades de medida</h2>
    <p class="text-sm text-slate-500 sm:col-span-3">{{ unitSummary() }}. El factor convierte a la unidad base de la dimensión: por ejemplo kg = 1000 g, litro = 1000 ml. Las unidades existentes conservan sus factores para proteger movimientos históricos.</p>
    <label>Código<input required pattern="[a-z0-9]+" maxlength="15" class="admin-input" name="code" [(ngModel)]="unit.codigo"></label>
    <label>Nombre<input required minlength="2" maxlength="80" class="admin-input" name="name" [(ngModel)]="unit.nombre"></label>
    <label>Dimensión<select class="admin-input" name="dimension" [(ngModel)]="unit.dimension"><option value="conteo">Conteo</option><option value="masa">Masa (g)</option><option value="volumen">Volumen (ml)</option></select></label>
    <label>Factor a unidad base<input required type="number" min="0.000001" step="0.000001" class="admin-input" name="factor" [(ngModel)]="unit.factor_base"></label>
    <label><input type="checkbox" name="fractional" [(ngModel)]="unit.fraccionable"> Admite fracciones</label><button class="admin-primary" [disabled]="busy() || unitForm.invalid">Crear unidad</button>
  </form>
` })
export class RecepcionesComponent {
  private readonly api = inject(OperationsApiService); private readonly admin = inject(AdminApiService);
  readonly products = signal<AdminProduct[]>([]); readonly suppliers = signal<{ id: number; razon_social: string }[]>([]); readonly units = signal<Unit[]>([]); readonly lots = signal<Lot[]>([]);
  readonly busy = signal(false); readonly loading = signal(true); readonly error = signal(''); readonly message = signal('');
  supplierId = 0; document = ''; expiring = false; lines: PurchaseLine[] = [];
  unit: Unit = { codigo: '', nombre: '', dimension: 'conteo', factor_base: 1, fraccionable: false };
  constructor() { this.addLine(); this.load(); }
  load() { this.loading.set(true); forkJoin({ products: this.admin.getInventory(), suppliers: this.api.suppliers(), units: this.api.units(), lots: this.api.lots(this.expiring) }).subscribe({ next: data => { this.products.set(data.products); this.suppliers.set(data.suppliers); this.units.set(data.units); this.lots.set(data.lots); this.loading.set(false); }, error: error => { this.loading.set(false); this.error.set(operationError(error)); } }); }
  addLine() { this.lines.push({ producto_id: 0, cantidad: 1, costo_unitario: 0, lote: '', vencimiento: null, unidad: null }); }
  selectProduct(line: PurchaseLine) { line.unidad = this.products().find(p => p.id === line.producto_id)?.unidad_medida ?? null; }
  requiresExpiry(id: number) { return this.products().find(p => p.id === id)?.requiere_vencimiento ?? false; }
  compatibleUnits(id: number) { const product = this.products().find(p => p.id === id); const target = this.units().find(u => u.codigo === product?.unidad_medida); return this.units().filter(u => u.dimension === target?.dimension); }
  conversion(line: PurchaseLine) { const product = this.products().find(p => p.id === line.producto_id); const target = this.units().find(u => u.codigo === product?.unidad_medida); const source = this.units().find(u => u.codigo === line.unidad); return source && target ? `Ingreso: ${Number(line.cantidad) * Number(source.factor_base) / Number(target.factor_base)} ${target.codigo}.` : 'Selecciona producto y unidad.'; }
  receive() { if (this.busy()) return; this.busy.set(true); this.error.set(''); this.message.set(''); this.api.receive({ proveedor_id: this.supplierId, documento: this.document, detalles: this.lines.map(line => ({ ...line, vencimiento: line.vencimiento || null })) }).subscribe({ next: () => { this.busy.set(false); this.message.set('Recepción registrada. Existencias, lotes y egreso actualizados.'); this.document = ''; this.lines = []; this.addLine(); this.load(); }, error: error => this.fail(error) }); }
  createUnit() { if (this.busy()) return; this.busy.set(true); this.error.set(''); this.api.createUnit(this.unit).subscribe({ next: unit => { this.units.update(rows => [...rows, unit]); this.unit = { codigo: '', nombre: '', dimension: 'conteo', factor_base: 1, fraccionable: false }; this.busy.set(false); this.message.set('Unidad creada; ya puede asignarse desde Productos.'); }, error: error => this.fail(error) }); }
  loadLots() { this.api.lots(this.expiring).subscribe({ next: rows => this.lots.set(rows), error: error => this.error.set(operationError(error)) }); }
  lotState(lot: Lot) { if (Number(lot.cantidad) === 0) return 'Agotado'; if (lot.vencimiento && lot.vencimiento < new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima' }).format(new Date())) return 'Vencido · no vendible'; return 'Disponible'; }
  unitSummary() { return this.units().map(u => `${u.codigo}: ${u.nombre}`).join(' · '); }
  private fail(error: unknown) { this.busy.set(false); this.error.set(operationError(error)); }
}
