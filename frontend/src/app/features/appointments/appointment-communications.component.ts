import { HttpClient } from '@angular/common/http';
import { Component, effect, inject, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { environment } from '../../../environments/environment';
import { Appointment } from './appointments.models';
import { operationError } from '../admin/services/operations-api.service';

interface Communications {
  cita_id: number; estado_cita: string; asistencia_confirmada_en: string | null; receta_disponible: boolean;
  orden: { codigo: string; total: number | string; estado: string } | null;
  mensajes: { id: number; evento: string; estado: string; intentos: number; enviado_en: string | null; entregado_en: string | null }[];
  alcance: string;
}

@Component({ selector: 'app-appointment-communications', standalone: true, imports: [FormsModule], template: `
  <section class="mt-6 space-y-3 rounded-2xl border bg-white p-5" aria-labelledby="appointment-communications-title">
    <h2 id="appointment-communications-title" class="text-lg font-bold">Comunicaciones y receta de mis citas</h2>
    <p class="text-sm text-slate-600">Consulta la confirmación de cancelación, la asistencia recibida y la receta emitida al cerrar la atención.</p>
    <form class="flex flex-wrap items-end gap-3" (ngSubmit)="load()">
      <label>Cita a consultar<select class="block max-w-full rounded-xl border p-2" name="cita" [ngModel]="selected()" (ngModelChange)="select(+$event)">
        <option [ngValue]="0">Selecciona una cita</option>@for (item of appointments(); track item.id) { <option [ngValue]="item.id">#{{ item.id }} · {{ item.mascota.nombre }} · {{ item.estado }}</option> }
      </select></label><button type="submit" class="rounded-xl border px-3 py-2 font-bold" [disabled]="busy() || !selected()">Consultar comunicaciones</button>
    </form>
    @if (busy()) { <p role="status">Consultando comunicaciones…</p> }
    @if (error()) { <p role="alert" class="text-rose-700">{{ error() }}</p> }
    @if (data(); as status) {
      <p>Estado de cita: <b>{{ status.estado_cita }}</b></p>
      <p>{{ status.asistencia_confirmada_en ? 'Asistencia confirmada por WhatsApp' : 'Sin confirmación de asistencia recibida' }}</p>
      @if (status.orden; as order) { <p>Orden: <b>{{ order.codigo }}</b> · S/ {{ money(order.total) }} · {{ order.estado }}</p> }
      @for (message of status.mensajes; track message.id) { <div class="rounded-xl bg-slate-50 p-3 text-sm">
        <b>{{ message.evento === 'receta' ? 'Receta por WhatsApp' : 'Confirmación de cancelación' }}</b><p>{{ stateLabel(message.estado) }}</p>
        @if (message.entregado_en) { <p>Entrega confirmada: {{ date(message.entregado_en) }}</p> }
      </div> } @empty { <p class="text-sm">No hay avisos de cancelación o receta registrados para esta cita.</p> }
      @if (status.receta_disponible) { <button type="button" class="rounded-xl bg-teal-700 px-4 py-2 font-bold text-white" [disabled]="downloading()" (click)="download()">{{ downloading() ? 'Descargando…' : 'Descargar receta PDF' }}</button> }
      <p class="text-xs text-slate-500">{{ status.alcance }}</p>
    }
  </section>`,
})
export class AppointmentCommunicationsComponent {
  readonly appointments = input<Appointment[]>([]); readonly selected = signal(0); readonly data = signal<Communications | null>(null);
  readonly busy = signal(false); readonly downloading = signal(false); readonly error = signal('');
  private readonly http = inject(HttpClient); private version = 0;
  constructor() {
    effect(() => {
      this.appointments();
      if (this.selected() && !this.appointments().some(item => item.id === this.selected())) this.select(0);
      else { this.version++; this.data.set(null); this.busy.set(false); }
    });
  }
  select(id: number): void { this.version++; this.selected.set(id); this.data.set(null); this.busy.set(false); this.error.set(''); }
  load(): void {
    if (this.busy() || !this.selected()) return;
    const version = ++this.version; this.busy.set(true); this.error.set(''); this.data.set(null);
    this.http.get<Communications>(`${environment.apiUrl}/portal/citas/${this.selected()}/comunicaciones`).subscribe({ next: data => { if (version === this.version) { this.data.set(data); this.busy.set(false); } }, error: error => { if (version === this.version) { this.error.set(operationError(error)); this.busy.set(false); } } });
  }
  download(): void {
    const id = this.data()?.cita_id;
    if (!id || this.downloading()) return;
    this.downloading.set(true); this.error.set('');
    this.http.get(`${environment.apiUrl}/portal/citas/${id}/receta-pdf`, { responseType: 'blob' }).subscribe({ next: blob => {
      const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = `receta-cita-${id}.pdf`; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); this.downloading.set(false);
    }, error: () => { this.error.set('No se pudo descargar la receta. Actualiza la consulta e intenta nuevamente.'); this.downloading.set(false); } });
  }
  money(value: number | string): string { return Number(value).toFixed(2); }
  date(value: string): string { return new Intl.DateTimeFormat('es-PE', { timeZone: 'America/Lima', dateStyle: 'short', timeStyle: 'short' }).format(new Date(value)); }
  stateLabel(state: string): string { return ({ pendiente_manual: 'Pendiente de envío manual por la clínica', gestionado_manual: 'La clínica registró su gestión manual; entrega sin confirmar', pendiente: 'Preparado para envío', pendiente_configuracion: 'La clínica debe completar la configuración del envío', error: 'El proveedor informó un fallo; la clínica puede reintentar', enviado: 'Aceptado por el proveedor; entrega aún sin confirmar', entregado: 'Entregado por WhatsApp', leido: 'Leído en WhatsApp', cancelado: 'Aviso cancelado; coordina con la clínica' } as Record<string, string>)[state] || state; }
}
