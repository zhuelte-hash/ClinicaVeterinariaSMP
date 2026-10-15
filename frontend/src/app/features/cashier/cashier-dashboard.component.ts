import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize, forkJoin } from 'rxjs';
import { CashierApiService } from './cashier-api.service';
import { CashierOrder, CashierSummary, CashRegister, CashierPendingPayment } from './cashier.models';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-cashier-dashboard',
  standalone: true,
  imports: [ReactiveFormsModule],
  template: `
    <section class="mx-auto max-w-7xl">
      <div class="mb-7 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div><p class="text-sm font-bold uppercase tracking-[.18em] text-[#168ba1]">Hoy</p><h2 class="text-3xl font-black tracking-tight text-[#111827]">Control de caja</h2><p class="mt-2 text-sm text-slate-500">Abre tu turno y supervisa los pagos asignados.</p></div>
        <button (click)="loadSummary()" [disabled]="loading()" class="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 hover:border-[#56c4d8] disabled:opacity-50">Actualizar</button>
      </div>

      @if (errorMessage()) { <p class="mb-5 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm font-semibold text-rose-700">{{ errorMessage() }}</p> }

      <div class="grid gap-5 md:grid-cols-3">
        <article class="metric-card"><p class="metric-label">Estado del turno</p><p class="mt-3 text-2xl font-black" [class.text-emerald-600]="register()" [class.text-slate-500]="!register()">{{ register() ? 'Caja abierta' : 'Caja cerrada' }}</p><span class="mt-4 inline-flex rounded-full px-3 py-1 text-xs font-bold" [class.bg-emerald-100]="register()" [class.text-emerald-700]="register()" [class.bg-slate-100]="!register()">{{ register() ? 'Operando' : 'Sin turno activo' }}</span></article>
        <article class="metric-card"><p class="metric-label">Ingresos del turno</p><p class="mt-3 text-3xl font-black text-[#111827]">S/ {{ money(register()?.total_ingresos_validados) }}</p><p class="mt-3 text-xs text-slate-500">Efectivo S/ {{ money(summary()?.ingresos_efectivo) }} · Digital S/ {{ money(summary()?.ingresos_digitales) }}</p></article>
        <article class="metric-card"><p class="metric-label">Pagos por revisar</p><p class="mt-3 text-3xl font-black text-amber-600">{{ summary()?.ordenes_pendientes ?? 0 }}</p><p class="mt-3 text-xs text-slate-500">Comprobantes pendientes</p></article>
      </div>

      <div class="mt-6 grid gap-6 lg:grid-cols-[.8fr_1.2fr]">
        <article class="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          @if (register(); as current) {
            <p class="text-xs font-bold uppercase tracking-[.18em] text-[#168ba1]">Turno #{{ current.id }}</p>
            <h3 class="mt-2 text-xl font-black text-[#111827]">Caja en operación</h3>
            <div class="mt-6 space-y-3 rounded-2xl bg-slate-50 p-5 text-sm">
              <div class="flex justify-between"><span class="text-slate-500">Fondo inicial</span><b>S/ {{ money(current.fondo_inicial) }}</b></div>
              <div class="flex justify-between"><span class="text-slate-500">Ventas en efectivo</span><b>S/ {{ money(summary()?.ingresos_efectivo) }}</b></div>
              <div class="flex justify-between"><span class="text-slate-500">Ventas digitales</span><b>S/ {{ money(summary()?.ingresos_digitales) }}</b></div>
              <div class="border-t border-slate-200 pt-3 flex justify-between text-base"><span>Efectivo esperado</span><b class="text-[#168ba1]">S/ {{ expectedTotal() }}</b></div>
            </div>
            <form [formGroup]="closeForm" (ngSubmit)="closeRegister()" class="mt-5 grid gap-3"><label class="text-sm font-bold">Efectivo contado (S/)<input type="number" step="0.01" min="0" formControlName="efectivoContado" class="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3"></label><p class="text-xs text-slate-500">Diferencia estimada: S/ {{ difference() }}</p><button type="submit" [disabled]="actionLoading() || closeForm.invalid" class="w-full rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 font-bold text-rose-700 hover:bg-rose-100 disabled:opacity-50">Cerrar y arquear caja</button></form>
          } @else {
            <p class="text-xs font-bold uppercase tracking-[.18em] text-amber-600">Inicio de turno</p>
            <h3 class="mt-2 text-xl font-black text-[#111827]">Abrir una caja</h3>
            <p class="mt-2 text-sm leading-6 text-slate-500">Registra el efectivo disponible antes de comenzar a validar cobros.</p>
            <form class="mt-6" [formGroup]="openForm" (ngSubmit)="openRegister()">
              <label for="opening-balance" class="mb-2 block text-sm font-bold">Fondo inicial</label>
              <div class="flex rounded-xl border border-slate-300 bg-white focus-within:border-[#56c4d8] focus-within:ring-2 focus-within:ring-[#56c4d8]/20"><span class="px-4 py-3 text-slate-500">S/</span><input id="opening-balance" type="number" min="0" step="0.01" formControlName="fondoInicial" class="min-w-0 flex-1 rounded-r-xl px-3 py-3 outline-none" /></div>
              @if (openForm.controls.fondoInicial.invalid && openForm.controls.fondoInicial.touched) { <p class="mt-2 text-xs font-semibold text-rose-600">Ingresa un fondo inicial valido.</p> }
              <button type="submit" [disabled]="openForm.invalid || actionLoading()" class="mt-5 w-full rounded-xl bg-[#111827] px-4 py-3 font-black text-white transition hover:bg-[#56c4d8] hover:text-[#111827] disabled:opacity-50">Abrir caja</button>
            </form>
          }
        </article>

        <article class="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
          <div class="border-b border-slate-100 p-6"><h3 class="text-xl font-black text-[#111827]">Órdenes recientes</h3><p class="mt-1 text-sm text-slate-500">Actividad asociada a tu usuario.</p></div>
          @if (summary()?.ordenes_recientes?.length) {
            <div class="overflow-x-auto"><table class="w-full text-left text-sm"><thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th class="px-6 py-3">Orden</th><th class="px-6 py-3">Estado</th><th class="px-6 py-3 text-right">Monto</th></tr></thead><tbody>@for (order of summary()!.ordenes_recientes; track order.id) {<tr class="border-t border-slate-100"><td class="px-6 py-4 font-bold text-[#111827]">{{ order.codigo_orden }}</td><td class="px-6 py-4"><span class="rounded-full px-3 py-1 text-xs font-bold" [class]="statusClass(order)">{{ statusLabel(order) }}</span></td><td class="px-6 py-4 text-right font-black">S/ {{ money(order.monto_total) }}</td></tr>}</tbody></table></div>
          } @else {
            <div class="grid min-h-64 place-items-center p-8 text-center"><div><span class="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-slate-100 text-2xl">▤</span><p class="mt-4 font-bold text-slate-700">Aun no hay ordenes</p><p class="mt-1 text-sm text-slate-500">Las operaciones asignadas apareceran aqui.</p></div></div>
          }
        </article>
      </div>
      <article class="mt-6 rounded-3xl border border-slate-200 bg-white p-6"><h3 class="text-xl font-black">Pagos por revisar</h3>@for (order of pending(); track order.id) { <div class="mt-3 flex flex-wrap items-center justify-between gap-3 border-t pt-3"><span>{{ order.codigo_orden }} · S/ {{ money(order.monto_total) }} · Operación {{ order.codigo_operacion || 'sin comprobante' }}</span><div class="flex gap-3">@if (order.captura_imagen) { <a [href]="receiptUrl(order.captura_imagen)" target="_blank" rel="noopener" class="font-bold text-[#168ba1]">Ver comprobante</a> }<button type="button" (click)="rejectPayment(order)" [disabled]="actionLoading() || !register()" class="rounded-xl border border-rose-200 px-4 py-2 font-bold text-rose-700 disabled:opacity-40">Rechazar</button><button type="button" (click)="validatePayment(order)" [disabled]="actionLoading() || !register() || !order.captura_imagen" class="rounded-xl bg-[#168ba1] px-4 py-2 font-bold text-white disabled:opacity-40">Validar pago</button></div></div> } @empty { <p class="mt-3 text-sm text-slate-500">No hay pagos pendientes asignados.</p> }</article>
      @if (lastClose(); as closed) { <p class="mt-4 rounded-xl bg-slate-100 p-4 font-bold">Turno #{{ closed.id }} cerrado. Efectivo contado S/ {{ money(closed.efectivo_contado ?? undefined) }} · Diferencia S/ {{ money(closed.diferencia ?? undefined) }}</p> }
      <section class="mt-6 rounded-3xl border border-slate-200 bg-white p-6"><h3 class="text-xl font-black">Últimos arqueos</h3>@for (closed of closedRegisters(); track closed.id) {<div class="mt-3 flex flex-wrap justify-between gap-2 border-t pt-3 text-sm"><span>Turno #{{ closed.id }} · {{ closed.fecha_cierre ? formatDate(closed.fecha_cierre) : 'Fecha no registrada' }}</span><span>Contado S/ {{ money(closed.efectivo_contado ?? undefined) }} · Diferencia S/ {{ money(closed.diferencia ?? undefined) }}</span></div>} @empty {<p class="mt-3 text-sm text-slate-500">No hay cierres registrados.</p>}</section>
    </section>
  `,
  styles: [`
    .metric-card { border: 1px solid #d8e6e9; border-radius: 1.5rem; background: white; padding: 1.5rem; box-shadow: 0 8px 24px rgb(17 24 39 / .05); transition: .2s; }
    .metric-card:hover { border-color: #56c4d8; transform: translateY(-2px); box-shadow: 0 14px 30px rgb(17 24 39 / .09); }
    .metric-label { font-size: .72rem; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; color: rgb(100 116 139); }
  `],
})
export class CashierDashboardComponent {
  private readonly api = inject(CashierApiService);
  private readonly formBuilder = inject(FormBuilder);
  readonly summary = signal<CashierSummary | null>(null);
  readonly loading = signal(false);
  readonly actionLoading = signal(false);
  readonly errorMessage = signal('');
  readonly pending = signal<CashierPendingPayment[]>([]);
  readonly lastClose = signal<CashierSummary['caja']>(null);
  readonly closedRegisters = signal<CashRegister[]>([]);
  readonly register = computed(() => this.summary()?.caja ?? null);
  readonly expectedTotal = computed(() => {
    const register = this.register();
    return register ? Number(this.summary()?.efectivo_esperado ?? 0).toFixed(2) : '0.00';
  });
  readonly closeForm = this.formBuilder.nonNullable.group({ efectivoContado: [0, [Validators.required, Validators.min(0)]] });
  difference(): string { return (Number(this.closeForm.controls.efectivoContado.value) - Number(this.summary()?.efectivo_esperado ?? 0)).toFixed(2); }
  readonly openForm = this.formBuilder.nonNullable.group({
    fondoInicial: [100, [Validators.required, Validators.min(0)]],
  });

  constructor() {
    this.loadSummary();
  }

  loadSummary(): void {
    this.loading.set(true);
    this.errorMessage.set('');
    forkJoin({ summary: this.api.getSummary(), pending: this.api.getPendingPayments(), closed: this.api.getClosedRegisters() }).pipe(finalize(() => this.loading.set(false))).subscribe({
      next: ({ summary, pending, closed }) => { this.summary.set(summary); this.pending.set(pending); this.closedRegisters.set(closed); },
      error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
  }

  openRegister(): void {
    if (this.openForm.invalid) {
      this.openForm.markAllAsTouched();
      return;
    }
    this.actionLoading.set(true);
    this.errorMessage.set('');
    this.api.openRegister(this.openForm.getRawValue().fondoInicial)
      .pipe(finalize(() => this.actionLoading.set(false)))
      .subscribe({
        next: () => this.loadSummary(),
        error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
      });
  }

  closeRegister(): void {
    if (this.closeForm.invalid || !window.confirm(`¿Cerrar caja con diferencia de S/ ${this.difference()}?`)) return;
    this.actionLoading.set(true);
    this.errorMessage.set('');
    this.api.closeRegister(this.closeForm.controls.efectivoContado.value).pipe(finalize(() => this.actionLoading.set(false))).subscribe({
      next: (closed) => { this.lastClose.set(closed); this.loadSummary(); },
      error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
  }

  validatePayment(order: CashierOrder): void {
    if (!window.confirm(`¿Validar el pago de ${order.codigo_orden}?`)) return;
    this.actionLoading.set(true);
    this.api.validatePayment(order.id).pipe(finalize(() => this.actionLoading.set(false))).subscribe({
      next: () => this.loadSummary(), error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
  }

  rejectPayment(order: CashierOrder): void {
    const reason = window.prompt(`Motivo de rechazo para ${order.codigo_orden}:`);
    if (!reason?.trim() || reason.trim().length < 3) return;
    this.actionLoading.set(true);
    this.api.rejectPayment(order.id, reason.trim()).pipe(finalize(() => this.actionLoading.set(false))).subscribe({
      next: () => this.loadSummary(), error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
  }

  money(value: string | undefined): string {
    return Number(value ?? 0).toFixed(2);
  }
  formatDate(value: string): string { return new Intl.DateTimeFormat('es-PE', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Lima' }).format(new Date(value)); }
  receiptUrl(path: string): string { return path.startsWith('/') ? `${environment.apiUrl}${path}` : path; }

  statusLabel(order: CashierOrder): string {
    const labels: Record<CashierOrder['estado_pago'], string> = {
      pendiente: 'Pendiente',
      pago_enviado: 'Por validar',
      validado_confirmado: 'Validado',
      anulado: 'Anulado',
    };
    return labels[order.estado_pago];
  }

  statusClass(order: CashierOrder): string {
    const classes: Record<CashierOrder['estado_pago'], string> = {
      pendiente: 'bg-slate-100 text-slate-700',
      pago_enviado: 'bg-amber-100 text-amber-800',
      validado_confirmado: 'bg-emerald-100 text-emerald-700',
      anulado: 'bg-rose-100 text-rose-700',
    };
    return classes[order.estado_pago];
  }

  private errorText(error: unknown): string {
    if (error instanceof HttpErrorResponse && typeof error.error?.detail === 'string') {
      return error.error.detail;
    }
    return 'No se pudo completar la operacion. Intenta nuevamente.';
  }
}
