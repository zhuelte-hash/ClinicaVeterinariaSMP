import { Component, inject, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { AuthService } from '../../core/auth/auth.service';
import { apiError, BillingApiService, DiscountAuthorization } from './billing-api.service';

@Component({
  selector: 'app-discount-authorizations', standalone: true, imports: [FormsModule],
  template: `<section class="rounded-2xl border border-slate-200 bg-white p-4"><div class="flex flex-wrap items-center justify-between gap-2"><h3 class="font-bold">Descuentos autorizados</h3><button type="button" class="text-sm font-bold text-teal-700" (click)="load()" [disabled]="busy()">Actualizar autorizaciones</button></div>
    @if (error()) { <p role="alert" class="mt-3 text-sm text-rose-700">{{ error() }}</p> } @if (message()) { <p role="status" class="mt-3 text-sm text-emerald-800">{{ message() }}</p> }
    @if (auth.can('ventas', 'crear')) { <div class="mt-3 grid gap-3 sm:grid-cols-2"><label class="grid gap-1 text-sm">Importe a solicitar (S/)<input class="site-input" type="number" min="0.01" step="0.01" [(ngModel)]="amount" [ngModelOptions]="{standalone: true}"></label><label class="grid gap-1 text-sm">Motivo<input class="site-input" maxlength="500" [(ngModel)]="reason" [ngModelOptions]="{standalone: true}"></label></div><p class="mt-2 text-xs text-slate-500">La autorización queda vinculada al cliente seleccionado y a tu usuario; se utiliza una sola vez.</p><button type="button" class="site-button mt-3" [disabled]="busy() || amount <= 0 || reason.trim().length < 3" (click)="request()">Solicitar autorización</button> }
    <div class="mt-3 max-h-72 space-y-3 overflow-auto">@for (item of items(); track item.id) { <article class="rounded-xl border border-slate-200 p-3 text-sm"><p><b>#{{ item.id }} · S/ {{ money(item.monto) }}</b> · {{ item.estado }}{{ item.usada ? ' · utilizada' : '' }}</p><p>{{ item.cliente_nombre }} · {{ item.solicitante_nombre }}</p><p class="mt-1">{{ item.motivo }}</p>@if (item.aprobador_nombre) { <p class="mt-1 text-xs text-slate-500">Revisada por {{ item.aprobador_nombre }}</p> }
      @if (auth.isAdmin() && auth.can('ventas', 'aprobar') && item.estado === 'pendiente') { <div class="mt-2 flex gap-3"><button type="button" class="font-bold text-teal-700" [disabled]="busy()" (click)="review(item.id, true)">Aprobar</button><button type="button" class="font-bold text-rose-700" [disabled]="busy()" (click)="review(item.id, false)">Rechazar</button></div> }
      @if (item.estado === 'aprobada' && !item.usada && item.solicitante_id === auth.currentUser()?.id && item.cliente_id === clienteId()) { <button type="button" class="mt-2 font-bold text-teal-700" (click)="selected.emit(item)">Aplicar autorización #{{ item.id }}</button> }
    </article> } @empty { <p class="text-sm text-slate-500">No hay solicitudes de descuento.</p> }</div></section>`,
})
export class DiscountAuthorizationsComponent {
  readonly auth = inject(AuthService); private readonly api = inject(BillingApiService);
  readonly clienteId = input<number | null>(null); readonly selected = output<DiscountAuthorization>();
  readonly items = signal<DiscountAuthorization[]>([]); readonly busy = signal(false); readonly error = signal(''); readonly message = signal(''); amount = 0; reason = '';
  constructor() { this.load(); }
  money(value: number): string { return Number(value).toFixed(2); }
  load(): void { this.busy.set(true); this.api.discounts().pipe(finalize(() => this.busy.set(false))).subscribe({ next: items => { this.items.set(items); this.error.set(''); }, error: error => this.error.set(apiError(error)) }); }
  request(): void { if (this.busy() || this.amount <= 0 || this.reason.trim().length < 3) return; this.busy.set(true); this.api.requestDiscount(this.clienteId(), this.amount, this.reason.trim()).pipe(finalize(() => this.busy.set(false))).subscribe({ next: () => { this.message.set('Solicitud registrada. Administración debe aprobarla antes de aplicarla.'); this.reason = ''; this.amount = 0; this.load(); }, error: error => this.error.set(apiError(error)) }); }
  review(id: number, approve: boolean): void { this.busy.set(true); this.api.reviewDiscount(id, approve).pipe(finalize(() => this.busy.set(false))).subscribe({ next: () => { this.message.set(approve ? 'Descuento aprobado.' : 'Descuento rechazado.'); this.load(); }, error: error => this.error.set(apiError(error)) }); }
}
