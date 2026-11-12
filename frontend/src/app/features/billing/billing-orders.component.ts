import { Component, computed, inject, OnDestroy, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { RouterLink } from '@angular/router';
import { finalize, forkJoin, Observable } from 'rxjs';
import { AuthService } from '../../core/auth/auth.service';
import { apiError, BillingApiService, BillingAttention, BillingCatalog, BillingOrder, DiscountAuthorization, OrderLine, OwnPayments, PaymentMethod, StaffSale } from './billing-api.service';
import { DiscountAuthorizationsComponent } from './discount-authorizations.component';

@Component({
  selector: 'app-billing-orders', standalone: true, imports: [FormsModule, RouterLink, DiscountAuthorizationsComponent],
  templateUrl: './billing-orders.component.html', styleUrl: '../admin/shared/admin-ui.css',
})
export class BillingOrdersComponent implements OnDestroy {
  readonly auth = inject(AuthService); private readonly api = inject(BillingApiService); private readonly sanitizer = inject(DomSanitizer);
  readonly client = computed(() => this.auth.currentUser()?.tipo === 'cliente');
  readonly receiving = computed(() => this.auth.isCashier() || this.auth.isAdmin());
  readonly loading = signal(false); readonly busy = signal(false); readonly error = signal(''); readonly message = signal('');
  readonly orders = signal<BillingOrder[]>([]); readonly selected = signal<BillingOrder | null>(null); readonly sales = signal<StaffSale[]>([]); readonly own = signal<OwnPayments | null>(null);
  readonly catalog = signal<BillingCatalog>({ clientes: [], productos: [], servicios: [] }); readonly attentions = signal<BillingAttention[]>([]);
  readonly lines = signal<OrderLine[]>([]); readonly discount = signal<DiscountAuthorization | null>(null); readonly createOpen = signal(false);
  readonly preview = signal<{ url: string; pdf: boolean; safe: SafeResourceUrl } | null>(null);
  readonly reasonAction = signal<{ kind: 'ordenes' | 'ventas' | 'pagos'; id: number; label: string } | null>(null);
  readonly methods: PaymentMethod[] = ['efectivo', 'yape', 'plin', 'tarjeta', 'transferencia'];
  filters = { fecha_inicial: '', fecha_final: '', estado: '', sin_comprobante: false }; search = '';
  clientId = 0; processId = 0; choice = ''; quantity = 1; amount = ''; method: PaymentMethod = 'yape'; channel = 'whatsapp'; operation = ''; file: File | null = null; reason = '';
  private orderKey: { payload: string; key: string } | null = null; private paymentKey: { payload: string; key: string } | null = null;
  readonly visibleOrders = computed(() => this.orders());
  readonly estimatedTotal = computed(() => this.lines().reduce((sum, item) => sum + Number(item.precio_unitario) * Number(item.cantidad), 0) - Number(this.discount()?.monto || 0));
  constructor() { this.auth.refreshPermissions().subscribe({ next: () => this.load(), error: error => this.error.set(apiError(error)) }); }
  ngOnDestroy(): void { this.closePreview(); }
  money(value: unknown): string { return Number(value || 0).toFixed(2); }
  date(value: string): string { if (!value) return 'Sin fecha'; return new Intl.DateTimeFormat('es-PE', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Lima' }).format(new Date(/Z$|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`)); }
  matches(order: BillingOrder): boolean { return `${order.codigo} ${order.cliente_nombre}`.toLocaleLowerCase('es').includes(this.search.trim().toLocaleLowerCase('es')); }
  load(): void {
    if (this.filters.fecha_inicial && this.filters.fecha_final && this.filters.fecha_inicial > this.filters.fecha_final) { this.error.set('La fecha inicial no puede ser posterior a la final.'); return; }
    this.loading.set(true); this.error.set('');
    if (this.client()) { this.api.ownPayments().pipe(finalize(() => this.loading.set(false))).subscribe({ next: data => { this.own.set(data); this.orders.set(data.ordenes); }, error: error => this.error.set(apiError(error)) }); return; }
    forkJoin({ orders: this.api.orders(this.filters), catalog: this.api.catalog(), sales: this.receiving() ? this.api.sales() : new Observable<StaffSale[]>(subscriber => { subscriber.next([]); subscriber.complete(); }) }).pipe(finalize(() => this.loading.set(false))).subscribe({ next: data => { this.orders.set(data.orders); this.catalog.set(data.catalog); this.sales.set(data.sales); }, error: error => this.error.set(apiError(error)) });
  }
  chooseClient(): void { this.processId = 0; this.attentions.set([]); this.discount.set(null); if (this.clientId) { const id = this.clientId; this.api.attentions(id).subscribe({ next: rows => { if (this.clientId === id) this.attentions.set(rows); }, error: error => this.error.set(apiError(error)) }); } }
  chooseAttention(): void { const row = this.attentions().find(item => item.id === this.processId); if (row) this.lines.set(row.detalles.map(item => this.describe(item))); }
  describe(line: OrderLine): OrderLine { const product = this.catalog().productos.find(item => item.id === line.producto_id); const service = this.catalog().servicios.find(item => item.id === line.servicio_id); return { ...line, nombre: product?.nombre || service?.nombre, precio_unitario: product?.precio || service?.precio || 0 }; }
  addLine(): void { const [type, id] = this.choice.split(':'); if (!id || !Number.isFinite(this.quantity) || this.quantity <= 0) return; const line = this.describe({ producto_id: type === 'p' ? Number(id) : null, servicio_id: type === 's' ? Number(id) : null, cantidad: this.quantity }); const old = this.lines().find(item => item.producto_id === line.producto_id && item.servicio_id === line.servicio_id); this.lines.update(rows => old ? rows.map(item => item === old ? { ...item, cantidad: Number(item.cantidad) + this.quantity } : item) : [...rows, line]); }
  removeLine(index: number): void { this.lines.update(rows => rows.filter((_, i) => i !== index)); }
  create(): void {
    if (this.busy() || !this.clientId || !this.lines().length) return;
    const data = { cliente_id: this.clientId, proceso_id: this.processId || null, autorizacion_id: this.discount()?.id || null, detalles: this.lines().map(({ producto_id, servicio_id, cantidad }) => ({ producto_id, servicio_id, cantidad })) };
    const payload = JSON.stringify(data); if (this.orderKey?.payload !== payload) this.orderKey = { payload, key: crypto.randomUUID() };
    this.run(this.api.createOrder({ ...data, clave_idempotencia: this.orderKey.key }), order => { this.createOpen.set(false); this.lines.set([]); this.discount.set(null); this.orderKey = null; this.openOrder(order.id); this.message.set(`Orden ${order.codigo} creada antes del pago.`); });
  }
  openOrder(id: number): void { this.error.set(''); this.api.order(id).subscribe({ next: order => { this.selected.set(order); this.amount = this.money(order.saldo); this.file = null; this.operation = ''; this.paymentKey = null; }, error: error => this.error.set(apiError(error)) }); }
  selectFile(event: Event): void { const input = event.target as HTMLInputElement; const file = input.files?.[0] || null; if (file && (!['image/jpeg', 'image/png', 'application/pdf'].includes(file.type) || file.size === 0 || file.size > 5 * 1024 * 1024)) { this.error.set('Adjunta una imagen JPG/PNG o PDF de hasta 5 MB.'); input.value = ''; this.file = null; return; } this.file = file; }
  registerPayment(): void {
    const order = this.selected(); if (!order || this.busy()) return;
    const amount = Number(this.amount); const channel = this.client() ? 'web' : this.channel;
    if (!Number.isFinite(amount) || amount <= 0 || amount > Number(order.saldo)) { this.error.set('El importe debe ser positivo y no superar el saldo.'); return; }
    if ((channel !== 'caja' && !this.file) || (this.file && this.method === 'efectivo')) { this.error.set('Adjunta el comprobante de un pago digital.'); return; }
    const data = { monto: amount.toFixed(2), medio: this.method, canal: channel, codigo_operacion: this.operation.trim() || null };
    const payload = JSON.stringify([order.id, data, this.file?.name, this.file?.size, this.file?.lastModified]); if (this.paymentKey?.payload !== payload) this.paymentKey = { payload, key: crypto.randomUUID() };
    this.run(this.api.payment(order.id, { ...data, clave_idempotencia: this.paymentKey.key }, this.file), updated => { this.selected.set(updated); this.file = null; this.paymentKey = null; this.amount = this.money(updated.saldo); this.message.set(updated.estado === 'pagada' ? 'Pago confirmado y boleta generada.' : 'Pago registrado. Los comprobantes adjuntos requieren revisión por caja.'); });
  }
  validate(id: number): void { this.run(this.api.validatePayment(id), order => { this.selected.set(order); this.message.set('Pago validado. El saldo y la caja fueron actualizados.'); }); }
  askReason(kind: 'ordenes' | 'ventas' | 'pagos', id: number, label: string): void { this.reason = ''; this.reasonAction.set({ kind, id, label }); }
  confirmReason(): void { const action = this.reasonAction(); if (!action || this.reason.trim().length < 3) return; this.run(this.api.reason(action.kind, action.id, this.reason.trim()), () => { this.reasonAction.set(null); this.message.set('Operación registrada con motivo y responsable.'); if (this.selected()) this.openOrder(this.selected()!.id); }); }
  download(path: string, filename: string): void { this.api.file(path).subscribe({ next: blob => this.api.download(blob, filename), error: error => this.error.set(apiError(error)) }); }
  showProof(id: number): void { this.api.file(`/operaciones/pagos/${id}/comprobante`).subscribe({ next: blob => { this.closePreview(); const url = URL.createObjectURL(blob); this.preview.set({ url, pdf: blob.type.includes('pdf'), safe: this.sanitizer.bypassSecurityTrustResourceUrl(url) }); }, error: error => this.error.set(apiError(error)) }); }
  closePreview(): void { const item = this.preview(); if (item) URL.revokeObjectURL(item.url); this.preview.set(null); }
  private run<T>(request: Observable<T>, next: (value: T) => void): void { if (this.busy()) return; this.busy.set(true); this.error.set(''); request.pipe(finalize(() => this.busy.set(false))).subscribe({ next: value => { next(value); this.load(); }, error: error => this.error.set(apiError(error)) }); }
}
