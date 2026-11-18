import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, input, output, signal } from '@angular/core';
import { environment } from '../../../environments/environment';
import { Appointment } from './appointments.models';
import { operationError } from '../admin/services/operations-api.service';

@Component({ selector: 'app-attendance-confirmation', standalone: true, template: `
  <section class="mt-6 grid gap-3 rounded-2xl border bg-white p-5" aria-labelledby="attendance-title">
    <h2 id="attendance-title" class="text-lg font-bold">Confirmar asistencia por WhatsApp</h2>
    <p class="text-sm text-slate-600">Para citas de hoy o mañana, envía el mensaje preparado desde el número de contacto de la reserva. Abrir WhatsApp no confirma la asistencia: debe recibirse el mensaje en la clínica.</p>
    <button type="button" class="justify-self-start rounded-xl border px-3 py-2 text-sm font-bold" (click)="refresh.emit()" [disabled]="busy()">Ya envié el mensaje: actualizar asistencia</button>
    @if (!eligibleAppointments().length) { <p class="text-sm text-slate-500">No hay citas de hoy o mañana disponibles para confirmar asistencia.</p> }
    @if (error()) { <p role="alert" class="text-rose-700">{{ error() }}</p> }
    @for (appointment of appointments(); track appointment.id) {
      @if (eligible(appointment)) {
        <div class="flex flex-wrap items-center gap-3 border-t pt-3"><b>{{ appointment.mascota.nombre }} · Cita #{{ appointment.id }}</b>
          @if (appointment.asistencia_confirmada_en) { <span class="text-teal-700">Asistencia confirmada por WhatsApp</span> }
          @else { <button type="button" class="rounded-xl border px-3 py-2 text-sm font-bold" [disabled]="busy()" (click)="prepare(appointment.id)">Preparar confirmación</button>
            @if (linkId() === appointment.id && link()) { <a [href]="link()" target="_blank" rel="noopener noreferrer" class="font-bold text-teal-700">Abrir WhatsApp para enviar</a> }
          }
        </div>
      }
    }
  </section>
` })
export class AttendanceConfirmationComponent {
  readonly appointments = input<Appointment[]>([]);
  readonly refresh = output<void>();
  readonly eligibleAppointments = computed(() => this.appointments().filter(appointment => this.eligible(appointment)));
  private readonly http = inject(HttpClient);
  readonly busy = signal(false); readonly error = signal(''); readonly link = signal(''); readonly linkId = signal(0);
  eligible(appointment: Appointment): boolean {
    const scheduled = new Date(appointment.fecha_hora_programada);
    const tomorrow = new Date(Date.now() + 86400000);
    const day = (value: Date) => new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima' }).format(value);
    return ['confirmada', 'reprogramada'].includes(appointment.estado) && scheduled.getTime() > Date.now() && day(scheduled) <= day(tomorrow) && !appointment.fecha_hora_llegada;
  }
  prepare(id: number) {
    if (this.busy()) return;
    this.busy.set(true); this.error.set(''); this.link.set(''); this.linkId.set(id);
    this.http.get<{ whatsapp_url: string }>(`${environment.apiUrl}/portal/citas/${id}/asistencia-whatsapp`).subscribe({ next: data => { this.link.set(data.whatsapp_url); this.busy.set(false); }, error: error => { this.error.set(operationError(error)); this.busy.set(false); } });
  }
}
