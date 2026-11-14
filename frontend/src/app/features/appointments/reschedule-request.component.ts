import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { environment } from '../../../environments/environment';
import { ClinicPolicyService } from '../../core/services/clinic-policy.service';
import { AppointmentsApiService } from './appointments-api.service';
import { Appointment, AvailabilitySlot } from './appointments.models';
import { operationError, Reschedule } from '../admin/services/operations-api.service';

@Component({ selector: 'app-reschedule-request', standalone: true, imports: [FormsModule], template: `
  <section class="mt-6 rounded-3xl border border-slate-200 bg-white p-6" aria-labelledby="reschedule-title">
    <h2 id="reschedule-title" class="text-xl font-black text-[#0B1B6D]">Solicitar reprogramación por WhatsApp</h2>
    <p class="mt-2 text-sm text-slate-600">Solicita el cambio con al menos {{ minimumHours() }} horas de anticipación. Tu cita conserva su horario hasta que la clínica confirme.</p>
    @if (error()) { <p class="mt-3 rounded-xl bg-rose-50 p-3 text-rose-700" role="alert">{{ error() }}</p> }
    <form class="mt-4 grid gap-4" #form="ngForm" (ngSubmit)="submit()">
      <label>Cita<select required class="site-input" name="appointment" [(ngModel)]="appointmentId" (ngModelChange)="loadSlots()"><option [ngValue]="0">Selecciona una cita</option>@for (appointment of eligible(); track appointment.id) { <option [ngValue]="appointment.id">#{{ appointment.id }} · {{ appointment.mascota.nombre }} · {{ date(appointment.fecha_hora_programada) }}</option> }</select></label>
      <label>Nueva fecha<input required class="site-input" type="date" name="day" [min]="today" [(ngModel)]="day" (ngModelChange)="loadSlots()"></label>
      <label>Horario<select required class="site-input" name="slot" [(ngModel)]="slot"><option value="">{{ loading() ? 'Consultando…' : 'Selecciona un horario' }}</option>@for (item of slots(); track item.fecha_hora) { <option [value]="item.fecha_hora">{{ date(item.fecha_hora) }} · {{ item.veterinario_nombre }}</option> }</select></label>
      <label>Motivo<textarea required minlength="3" maxlength="500" class="site-input" name="reason" [(ngModel)]="reason"></textarea></label>
      <button class="site-button" [disabled]="busy() || loading() || form.invalid || !appointmentId">Registrar solicitud y preparar WhatsApp</button>
    </form>
    @if (whatsappUrl()) { <div class="mt-4 rounded-xl bg-teal-50 p-4" role="status"><p>Solicitud registrada. Abre WhatsApp y envía el mensaje para coordinar con la clínica.</p><a class="site-button mt-3 inline-block" [href]="whatsappUrl()" target="_blank" rel="noopener noreferrer">Abrir WhatsApp con mi solicitud</a></div> }
    <h3 class="mt-6 font-bold">Mis solicitudes</h3>
    @for (item of requests(); track item.id) { <p class="mt-2 text-sm">#{{ item.id }} · Cita #{{ item.cita_id }} · {{ date(item.fecha_propuesta) }} · <b>{{ item.estado }}</b></p> } @empty { <p class="mt-2 text-sm text-slate-500">Sin solicitudes registradas.</p> }
  </section>
` })
export class RescheduleRequestComponent {
  readonly appointments = input.required<Appointment[]>();
  private readonly http = inject(HttpClient); private readonly api = inject(AppointmentsApiService);
  readonly error = signal(''); readonly busy = signal(false); readonly loading = signal(false); readonly whatsappUrl = signal('');
  readonly requests = signal<Reschedule[]>([]); readonly slots = signal<AvailabilitySlot[]>([]); readonly minimumHours = signal(4);
  readonly eligible = computed(() => this.appointments().filter(a => !['atendida', 'cancelada', 'no_asistio', 'cliente_no_respondio'].includes(a.estado) && new Date(a.fecha_hora_programada).getTime() - Date.now() >= this.minimumHours() * 3600000 && !this.requests().some(r => r.cita_id === a.id && r.estado === 'pendiente')));
  readonly today = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima' }).format(new Date());
  appointmentId = 0; day = this.today; slot = ''; reason = ''; private version = 0;
  constructor() { this.loadRequests(); inject(ClinicPolicyService).get().subscribe({ next: policy => this.minimumHours.set(Math.max(4, policy.horas_reprogramacion)), error: error => this.error.set(operationError(error)) }); }
  private loadRequests() { this.http.get<Reschedule[]>(`${environment.apiUrl}/portal/reprogramaciones`).subscribe({ next: rows => this.requests.set(rows), error: error => this.error.set(operationError(error)) }); }
  loadSlots() { const version = ++this.version; this.slots.set([]); this.slot = ''; this.whatsappUrl.set(''); this.error.set(''); const appointment = this.appointments().find(a => a.id === this.appointmentId); if (!appointment || !this.day) { this.loading.set(false); return; } this.loading.set(true); this.api.getAvailability(appointment.servicio.id, this.day).subscribe({ next: rows => { if (version !== this.version) return; const compatible = rows.filter(row => (!appointment.veterinario_id || row.veterinario_id === appointment.veterinario_id) && new Date(row.fecha_hora).getTime() !== new Date(appointment.fecha_hora_programada).getTime()); this.slots.set([...new Map(compatible.map(row => [row.fecha_hora, row])).values()]); this.loading.set(false); }, error: error => { if (version === this.version) { this.loading.set(false); this.error.set(operationError(error)); } } }); }
  submit() { if (this.busy()) return; this.busy.set(true); this.error.set(''); this.whatsappUrl.set(''); this.http.post<Reschedule & { whatsapp_url: string }>(`${environment.apiUrl}/portal/citas/${this.appointmentId}/reprogramacion`, { fecha_propuesta: this.slot, motivo: this.reason, canal: 'whatsapp' }).subscribe({ next: item => { this.busy.set(false); this.whatsappUrl.set(item.whatsapp_url); this.requests.update(rows => [item, ...rows]); this.appointmentId = 0; this.slot = ''; this.reason = ''; }, error: error => { this.busy.set(false); this.error.set(operationError(error)); } }); }
  date(value: string) { return new Intl.DateTimeFormat('es-PE', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Lima' }).format(new Date(value)); }
}
