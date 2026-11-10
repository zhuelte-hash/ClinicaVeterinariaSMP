import { CommonModule } from '@angular/common';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { finalize } from 'rxjs';
import { AuthService } from '../../core/auth/auth.service';
import { LocalPurchaseService, WebOrder } from '../../core/services/local-purchase.service';

@Component({
  selector: 'app-purchase-orders', standalone: true, imports: [CommonModule, FormsModule],
  template: `
    <section class="mx-auto max-w-7xl p-4 sm:p-6">
      <h1 class="text-2xl font-black text-slate-900">{{ staff ? 'Pedidos web / Pagos pendientes' : 'Mis compras web' }}</h1>
      <p class="mt-2 text-sm text-slate-600">{{ staff ? 'Revisa el comprobante antes de confirmar. La venta y el stock se registran al aprobar.' : 'Consulta el estado de tus pedidos y el resultado de la revisión de caja.' }}</p>
      <form (ngSubmit)="page = 1; load()" class="my-6 flex flex-wrap items-end gap-3 rounded-2xl bg-white p-4 shadow-sm">
        <label class="text-sm font-semibold">Estado<select name="estado" [(ngModel)]="state" class="mt-1 block rounded-xl border p-2"><option value="">Todos</option>@for (value of states; track value) { <option [value]="value">{{ value }}</option> }</select></label>
        <label class="text-sm font-semibold">Código<input name="codigo" [(ngModel)]="code" maxlength="50" class="mt-1 block rounded-xl border p-2" /></label>
        <label class="text-sm font-semibold">Fecha<input name="fecha" type="date" [(ngModel)]="date" class="mt-1 block rounded-xl border p-2" /></label>
        <button class="rounded-xl bg-[#1A98A2] px-5 py-2 font-bold text-white" [disabled]="loading()">{{ loading() ? 'Consultando…' : 'Buscar / Actualizar' }}</button>
      </form>
      @if (message()) { <p role="status" class="my-4 rounded-xl bg-teal-50 p-3 text-teal-800">{{ message() }}</p> }
      @if (error()) { <p role="alert" class="my-4 rounded-xl bg-rose-50 p-3 text-rose-800">{{ error() }}</p> }
      <div class="overflow-x-auto rounded-2xl bg-white shadow-sm">
        <table class="w-full text-left text-sm"><thead class="bg-slate-100"><tr><th class="p-4">Pedido / Fecha</th><th class="p-4">Cliente</th><th class="p-4">Total / Método</th><th class="p-4">Pedido / Pago</th><th class="p-4">Acciones</th></tr></thead><tbody>
          @for (order of orders(); track order.id) {
            <tr class="border-t"><td class="p-4 font-semibold">{{ order.codigo_pedido }}<p class="mt-1 text-xs text-slate-500">{{ order.fecha_pedido | date:'dd/MM/yyyy HH:mm' }}</p></td><td class="p-4">{{ order.datos_cliente.nombreCompleto }}<p class="text-xs">{{ order.datos_cliente.dni || order.datos_cliente.ruc }} · {{ order.datos_cliente.celular }}</p></td><td class="p-4 font-bold">{{ order.total | currency:'PEN':'S/ ' }}<p class="text-xs uppercase">{{ order.metodo_pago }}</p></td><td class="p-4"><span class="rounded-full px-3 py-1 text-xs font-bold" [class.bg-amber-100]="order.estado_pedido === 'PENDIENTE'" [class.bg-green-100]="order.estado_pedido === 'APROBADO'" [class.bg-rose-100]="order.estado_pedido === 'RECHAZADO'">{{ order.estado_pedido }}</span><p class="mt-2 text-xs">{{ order.estado_pago }}</p></td><td class="p-4"><button (click)="open(order)" class="font-bold text-[#1A98A2] underline">Ver detalle</button></td></tr>
          } @empty { <tr><td colspan="5" class="p-8 text-center text-slate-500">{{ loading() ? 'Cargando pedidos…' : 'No hay pedidos para estos filtros.' }}</td></tr> }
        </tbody></table>
      </div>
      <div class="mt-4 flex items-center justify-end gap-4 text-sm"><button (click)="page = page - 1; load()" [disabled]="page === 1 || loading()" class="rounded-xl border p-2 disabled:opacity-40">Anterior</button><span>Página {{ page }}</span><button (click)="page = page + 1; load()" [disabled]="orders().length < 20 || loading()" class="rounded-xl border p-2 disabled:opacity-40">Siguiente</button></div>
      @if (selected(); as order) {
        <div class="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/60 p-3" (click)="close()">
          <section role="dialog" aria-modal="true" aria-labelledby="order-title" (click)="$event.stopPropagation()" class="max-h-[92vh] w-full max-w-4xl overflow-y-auto rounded-3xl bg-white p-5 sm:p-8">
            <div class="flex justify-between gap-4"><h2 id="order-title" class="text-xl font-black">{{ order.codigo_pedido }}</h2><button (click)="close()" [disabled]="busy()" aria-label="Cerrar detalle" class="rounded-lg border px-3 py-1">✕</button></div>
            <p class="mt-3">{{ order.estado_pedido }} · Pago {{ order.estado_pago }}</p>
            <div class="my-4 grid gap-3 rounded-xl bg-slate-50 p-4 text-sm sm:grid-cols-2"><p><strong>Cliente:</strong> {{ order.datos_cliente.nombreCompleto }}</p><p><strong>DNI / RUC:</strong> {{ order.datos_cliente.dni || order.datos_cliente.ruc }}</p><p><strong>Contacto:</strong> {{ order.datos_cliente.celular }} · {{ order.datos_cliente.correo }}</p><p><strong>Entrega:</strong> {{ order.datos_cliente.tipoEntrega }} {{ order.datos_cliente.direccion }} {{ order.datos_cliente.referencia }}</p><p><strong>Observaciones:</strong> {{ order.observaciones || 'Sin observaciones' }}</p><p><strong>Operación:</strong> {{ order.numero_operacion }}</p></div>
            @for (item of order.detalles; track item.producto_id) { <div class="flex gap-3 border-b py-3 text-sm"><img [src]="item.imagen_url" [alt]="item.nombre_producto" class="h-12 w-12 rounded-lg object-cover" /><div class="flex-1 font-semibold">{{ item.nombre_producto }}<p class="font-normal">{{ item.cantidad }} × {{ item.precio_unitario | currency:'PEN':'S/ ' }}</p></div><strong>{{ item.subtotal | currency:'PEN':'S/ ' }}</strong></div> }
            <p class="mt-4 text-sm">Subtotal: {{ order.subtotal | currency:'PEN':'S/ ' }} · Descuento: {{ order.descuento | currency:'PEN':'S/ ' }} · Delivery: {{ order.costo_delivery | currency:'PEN':'S/ ' }}</p>
            <p class="my-3 text-xl font-black">Total {{ order.total | currency:'PEN':'S/ ' }} · {{ order.metodo_pago }}</p>
            @if (order.motivo_rechazo) { <p class="rounded-xl bg-rose-50 p-3 text-rose-800"><strong>Motivo del rechazo:</strong> {{ order.motivo_rechazo }}</p> }
            @if (order.fecha_revision) { <p class="my-3 text-sm">Revisión: {{ order.fecha_revision | date:'dd/MM/yyyy HH:mm' }} · Usuario #{{ order.usuario_revisor_id }} @if (order.venta_id) { · Venta #{{ order.venta_id }} }</p> }
            <button (click)="viewProof(order)" [disabled]="busy()" class="my-3 rounded-xl border border-[#1A98A2] px-4 py-2 font-bold text-[#1A98A2]">Visualizar comprobante privado</button>
            @if (proofUrl()) {
              @if (order.comprobante_tipo === 'application/pdf') { <iframe [src]="safeProof()" title="Comprobante PDF" class="h-[450px] w-full rounded-xl border"></iframe> }
              @else { <img [src]="proofUrl()" alt="Comprobante de pago" class="max-h-[500px] w-full rounded-xl border object-contain" /> }
              <a [href]="proofUrl()" [download]="order.comprobante_pago" class="my-2 inline-block text-sm font-bold text-[#1A98A2] underline">Descargar comprobante</a>
            }
            @if (staff && order.estado_pedido === 'PENDIENTE') {
              <div class="mt-5 border-t pt-5">
                @if (!action()) {
                  <div class="flex gap-3"><button (click)="action.set('APROBAR')" [disabled]="!proofUrl() || busy()" class="rounded-xl bg-teal-700 px-5 py-3 font-bold text-white disabled:opacity-40">Confirmar pago</button><button (click)="action.set('RECHAZAR')" class="rounded-xl border border-rose-700 px-5 py-3 font-bold text-rose-700">Rechazar pago</button></div>
                  <p class="mt-2 text-xs text-slate-500">Visualiza el comprobante para habilitar la confirmación.</p>
                } @else {
                  <p class="font-bold">{{ action() === 'APROBAR' ? '¿Confirmas que el pago es correcto? Se registrará la venta y se descontará el stock.' : 'Indica por qué rechazas el comprobante.' }}</p>
                  @if (action() === 'RECHAZAR') { <textarea [(ngModel)]="reason" maxlength="500" placeholder="Motivo obligatorio (mínimo 3 caracteres)" class="mt-3 w-full rounded-xl border p-3"></textarea> }
                  <div class="mt-3 flex gap-3"><button (click)="review(order)" [disabled]="busy() || (action() === 'RECHAZAR' && reason.trim().length < 3)" class="rounded-xl bg-slate-900 px-5 py-3 font-bold text-white disabled:opacity-40">{{ busy() ? 'Procesando…' : 'Confirmar operación' }}</button><button (click)="action.set(null)" [disabled]="busy()" class="rounded-xl border px-5 py-3">Volver</button></div>
                }
              </div>
            }
            @if (error()) { <p role="alert" class="mt-4 rounded-xl bg-rose-50 p-3 text-rose-800">{{ error() }}</p> }
          </section>
        </div>
      }
    </section>
  `,
})
export class PurchaseOrdersComponent {
  private readonly api = inject(LocalPurchaseService);
  private readonly auth = inject(AuthService);
  private readonly sanitizer = inject(DomSanitizer);
  readonly staff = this.auth.currentUser()?.tipo !== 'cliente';
  readonly orders = signal<WebOrder[]>([]);
  readonly selected = signal<WebOrder | null>(null);
  readonly proofUrl = signal('');
  readonly safeProof = signal<SafeResourceUrl | null>(null);
  readonly loading = signal(false);
  readonly busy = signal(false);
  readonly error = signal('');
  readonly message = signal('');
  readonly action = signal<'APROBAR' | 'RECHAZAR' | null>(null);
  readonly states = ['PENDIENTE', 'APROBADO', 'RECHAZADO', 'CANCELADO'];
  state = this.staff ? 'PENDIENTE' : '';
  code = '';
  date = '';
  page = 1;
  reason = '';
  constructor() { inject(DestroyRef).onDestroy(() => this.clearProof()); this.load(); }
  load() {
    this.loading.set(true); this.error.set('');
    this.api.list({ estado: this.state, codigo: this.code, fecha: this.date, pagina: this.page })
      .pipe(finalize(() => this.loading.set(false))).subscribe({ next: orders => this.orders.set(orders), error: error => this.fail(error) });
  }
  open(order: WebOrder) {
    this.clearProof(); this.action.set(null); this.reason = ''; this.error.set(''); this.selected.set(order);
    this.api.get(order.id).subscribe({ next: fresh => { if (this.selected()?.id === fresh.id) this.selected.set(fresh); }, error: error => this.fail(error) });
  }
  close() { if (this.busy()) return; this.selected.set(null); this.clearProof(); }
  viewProof(order: WebOrder) {
    this.busy.set(true); this.error.set('');
    this.api.proof(order.id).pipe(finalize(() => this.busy.set(false))).subscribe({
      next: blob => { this.clearProof(); const url = URL.createObjectURL(blob); this.proofUrl.set(url); this.safeProof.set(this.sanitizer.bypassSecurityTrustResourceUrl(url)); },
      error: error => this.fail(error),
    });
  }
  review(order: WebOrder) {
    const action = this.action(); if (!action || this.busy()) return;
    this.busy.set(true); this.error.set('');
    this.api.review(order.id, action, this.reason).pipe(finalize(() => this.busy.set(false))).subscribe({
      next: saved => { this.selected.set(saved); this.action.set(null); this.message.set(action === 'APROBAR' ? 'Pago aprobado. Venta e inventario registrados correctamente.' : 'Pedido rechazado. El cliente puede consultar el motivo.'); this.load(); },
      error: error => this.fail(error),
    });
  }
  private clearProof() { if (this.proofUrl()) URL.revokeObjectURL(this.proofUrl()); this.proofUrl.set(''); this.safeProof.set(null); }
  private fail(error: { error?: { detail?: unknown } }) { this.error.set(typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudo completar la operación. Intenta nuevamente.'); }
}
