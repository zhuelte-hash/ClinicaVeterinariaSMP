import { Component, effect, inject, input, signal } from '@angular/core';
import { AppointmentHistory, OperationsApiService, operationError } from '../../services/operations-api.service';

@Component({
  selector: 'app-appointment-history', standalone: true,
  template: `<section class="mt-4 space-y-3" aria-label="Historial de la cita">
    <h3 class="text-lg font-bold">Historial de cambios</h3>
    @if (loading()) { <p role="status">Consultando historial…</p> }
    @if (error()) { <p role="alert" class="text-rose-700">{{ error() }}</p><button type="button" (click)="load(appointmentId())">Reintentar historial</button> }
    @if (history(); as data) {
      <p>{{ data.reprogramaciones }} reprogramaciones · {{ data.cancelaciones }} cancelaciones · {{ data.cantidad }} eventos</p>
      <p class="text-sm text-slate-500">{{ data.alcance }}</p>
      @for (event of data.eventos; track event.id) {
        <article class="rounded-xl border border-slate-200 p-3">
          <b>{{ label(event.accion) }}</b><p>{{ date(event.fecha) }} · {{ event.autor }}</p>
          @for (change of changes(event.anterior, event.actual); track change.key) { <p class="mt-1 text-sm"><b>{{ label(change.key) }}:</b> {{ change.before }} → {{ change.after }}</p> }
          @if (event.motivo) { <p class="mt-1 text-sm">Motivo / nota: {{ event.motivo }}</p> }
        </article>
      } @empty { <p>No hay cambios registrados para esta cita.</p> }
    }
  </section>`,
})
export class AppointmentHistoryComponent {
  readonly appointmentId = input.required<number>();
  readonly history = signal<AppointmentHistory | null>(null); readonly loading = signal(false); readonly error = signal('');
  private readonly api = inject(OperationsApiService); private version = 0;
  constructor() { effect(() => this.load(this.appointmentId())); }
  load(id: number): void {
    const version = ++this.version; this.loading.set(true); this.error.set(''); this.history.set(null);
    this.api.appointmentHistory(id).subscribe({ next: data => { if (version === this.version) { this.history.set(data); this.loading.set(false); } }, error: error => { if (version === this.version) { this.error.set(operationError(error)); this.loading.set(false); } } });
  }
  label(value: string): string { return ({ fecha_hora_programada: 'Horario', fecha_hora_propuesta: 'Horario propuesto', veterinario_id: 'ID del veterinario', estado: 'Estado', asistencia_confirmada_en: 'Asistencia confirmada' } as Record<string, string>)[value] || value.replaceAll('_', ' '); }
  date(value: string): string { return new Intl.DateTimeFormat('es-PE', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Lima' }).format(new Date(value)); }
  changes(before: Record<string, unknown>, after: Record<string, unknown>) { return Object.keys(after).map(key => ({ key, before: this.value(key, before[key]), after: this.value(key, after[key]) })); }
  private value(key: string, value: unknown): string { return value == null ? 'Sin registrar' : (key.startsWith('fecha_') || key === 'asistencia_confirmada_en') ? this.date(String(value)) : String(value).replaceAll('_', ' '); }
}
