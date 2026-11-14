import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { ClinicPolicy, ClinicPolicyService, WEEKDAYS } from '../../../../core/services/clinic-policy.service';
import { AuthService } from '../../../../core/auth/auth.service';
import { AdminApiService, CatalogOption } from '../../services/admin-api.service';
import { OperationsApiService, operationError, Reschedule, Schedule } from '../../services/operations-api.service';
import { PageHeaderComponent } from '../../shared/page-header.component';

@Component({ standalone: true, imports: [FormsModule, PageHeaderComponent], styleUrl: '../../shared/admin-ui.css', template: `
  <admin-page-header title="Horarios y reprogramaciones" description="Los horarios de clínica, descansos y excepciones se aplican también al portal y a las reservas." />
  @if (error()) { <p class="mb-4 rounded-xl bg-rose-50 p-4 text-rose-700" role="alert">{{ error() }}</p> }
  @if (message()) { <p class="mb-4 rounded-xl bg-teal-50 p-4 text-teal-800" role="status">{{ message() }}</p> }
  @if (!auth.can('citas', 'editar')) { <p class="mb-4 text-sm text-slate-600">Tienes acceso de consulta. Para modificar horarios necesitas el permiso de edición de Citas.</p> }
  @if (policy; as data) {
    <form class="admin-card mb-6 grid gap-4 p-5" #policyForm="ngForm" (ngSubmit)="savePolicy()">
      <fieldset class="grid gap-4" [disabled]="busy() || !auth.can('citas', 'editar')">
      <h2 class="text-xl font-bold">Horario general · America/Lima</h2>
      @for (day of data.horarios; track day.dia) {
        <div class="grid items-end gap-3 rounded-xl border p-3 sm:grid-cols-6">
          <b>{{ days[day.dia] }}</b><label><input type="checkbox" [name]="'closed'+day.dia" [(ngModel)]="day.cerrado"> Cerrado</label>
          <label>Inicio<input class="admin-input" type="time" [name]="'start'+day.dia" [(ngModel)]="day.inicio" [required]="!day.cerrado"></label>
          <label>Fin<input class="admin-input" type="time" [name]="'end'+day.dia" [(ngModel)]="day.fin" [required]="!day.cerrado"></label>
          <label>Descanso desde<input class="admin-input" type="time" [name]="'breakStart'+day.dia" [(ngModel)]="day.descanso_inicio"></label>
          <label>Descanso hasta<input class="admin-input" type="time" [name]="'breakEnd'+day.dia" [(ngModel)]="day.descanso_fin"></label>
        </div>
      }
      <h3 class="font-bold">Excepciones y feriados</h3>
      @for (day of data.excepciones; track $index; let i = $index) {
        <div class="grid items-end gap-3 rounded-xl border p-3 sm:grid-cols-4">
          <label>Fecha<input required class="admin-input" type="date" [name]="'date'+i" [(ngModel)]="day.fecha"></label>
          <label>Motivo<input required minlength="3" maxlength="200" class="admin-input" [name]="'reason'+i" [(ngModel)]="day.motivo"></label>
          <label><input type="checkbox" [name]="'exClosed'+i" [(ngModel)]="day.cerrado"> Cerrado</label>
          <button type="button" class="admin-secondary" (click)="data.excepciones.splice(i,1)">Quitar</button>
          @if (!day.cerrado) {
            <label>Inicio<input required class="admin-input" type="time" [name]="'exStart'+i" [(ngModel)]="day.inicio"></label>
            <label>Fin<input required class="admin-input" type="time" [name]="'exEnd'+i" [(ngModel)]="day.fin"></label>
            <label>Descanso desde<input class="admin-input" type="time" [name]="'exBreakStart'+i" [(ngModel)]="day.descanso_inicio"></label>
            <label>Descanso hasta<input class="admin-input" type="time" [name]="'exBreakEnd'+i" [(ngModel)]="day.descanso_fin"></label>
          }
        </div>
      }
      <div class="flex flex-wrap gap-3"><button type="button" class="admin-secondary" (click)="addException()">Agregar excepción</button><button class="admin-primary" [disabled]="busy() || policyForm.invalid">Guardar horario general</button></div>
      <p class="text-sm text-slate-500">Los cambios afectan nuevas reservas; las citas existentes se conservan y deben coordinarse desde Citas.</p>
      </fieldset>
    </form>
  }
  <section class="admin-card mb-6 grid gap-4 p-5">
    <h2 class="text-xl font-bold">Agenda por profesional</h2>
    <label>Veterinario<select class="admin-input" [(ngModel)]="vetId" (ngModelChange)="loadSchedules()" [disabled]="busy()"><option [ngValue]="0">Selecciona</option>@for (vet of vets(); track vet.id) { <option [ngValue]="vet.id">{{ vet.nombre }}</option> }</select></label>
    @if (schedulesLoading()) { <p role="status">Consultando agenda…</p> }
    @if (vetId) {
      <form class="grid gap-3 sm:grid-cols-5" #scheduleForm="ngForm" (ngSubmit)="saveSchedule()">
        <label>Día<select class="admin-input" name="day" [(ngModel)]="schedule.dia_semana">@for (day of days; track $index) { <option [ngValue]="$index">{{ day }}</option> }</select></label>
        <label>Inicio<input required type="time" class="admin-input" name="start" [(ngModel)]="schedule.hora_inicio"></label>
        <label>Fin<input required type="time" class="admin-input" name="end" [(ngModel)]="schedule.hora_fin"></label>
        <label><input type="checkbox" name="active" [(ngModel)]="schedule.activo"> Activo</label>
        <div><button class="admin-primary" [disabled]="busy() || schedulesLoading() || scheduleForm.invalid || !auth.can('citas', editing ? 'editar' : 'crear')">{{ editing ? 'Guardar edición' : 'Agregar franja' }}</button>@if (editing) { <button type="button" class="admin-secondary" [disabled]="busy()" (click)="resetSchedule()">Cancelar</button> }</div>
      </form>
      @for (item of schedules(); track item.id) { <div class="flex flex-wrap justify-between gap-3 border-t pt-3"><span>{{ days[item.dia_semana] }} · {{ item.hora_inicio }}–{{ item.hora_fin }} · {{ item.activo ? 'Activo' : 'Inactivo' }}</span><button class="admin-secondary" [disabled]="busy() || !auth.can('citas', 'editar')" (click)="editSchedule(item)">Editar</button></div> }
      @empty { <p>Sin franjas registradas.</p> }
    }
  </section>
  <section class="admin-card p-5"><h2 class="text-xl font-bold">Solicitudes de reprogramación</h2><p class="text-sm text-slate-500">La solicitud conserva la cita original hasta que se apruebe. El nuevo horario se vuelve a validar al aceptar.</p>
    @for (item of requests(); track item.id) {
      <article class="mt-4 grid gap-2 border-t pt-4"><b>Solicitud #{{ item.id }} · Cita #{{ item.cita_id }} · {{ item.estado }}</b><p>{{ date(item.fecha_propuesta) }} · {{ item.canal }} · {{ item.motivo }}</p>
        @if (item.estado === 'pendiente' && auth.can('citas', 'editar')) { <label>Respuesta / motivo<input class="admin-input" [(ngModel)]="answers[item.id]" maxlength="500"></label><div class="flex gap-3"><button class="admin-primary" [disabled]="busy() || (answers[item.id] || '').trim().length < 3" (click)="resolve(item, true)">Aceptar horario</button><button class="admin-secondary" [disabled]="busy() || (answers[item.id] || '').trim().length < 3" (click)="resolve(item, false)">Rechazar</button></div> }
      </article>
    } @empty { <p class="py-5">No hay solicitudes.</p> }
  </section>
` })
export class HorariosComponent {
  readonly auth = inject(AuthService);
  private readonly policies = inject(ClinicPolicyService);
  private readonly api = inject(OperationsApiService);
  private readonly admin = inject(AdminApiService);
  readonly days = WEEKDAYS;
  readonly error = signal(''); readonly message = signal(''); readonly busy = signal(false);
  readonly schedulesLoading = signal(false);
  private scheduleVersion = 0;
  readonly vets = signal<CatalogOption[]>([]); readonly schedules = signal<Schedule[]>([]); readonly requests = signal<Reschedule[]>([]);
  policy: ClinicPolicy | null = null; vetId = 0; editing: number | undefined; answers: Record<number, string> = {};
  schedule = { dia_semana: 0, hora_inicio: '08:00', hora_fin: '12:00', activo: true };
  constructor() { forkJoin({ policy: this.policies.get(), vets: this.admin.getAppointmentVeterinarians(), requests: this.api.requests() }).subscribe({ next: data => { this.policy = data.policy; this.vets.set(data.vets); this.requests.set(data.requests); }, error: error => this.error.set(operationError(error)) }); }
  addException() { this.policy?.excepciones.push({ dia: 0, fecha: '', motivo: '', cerrado: true, inicio: '08:00', fin: '20:00', descanso_inicio: null, descanso_fin: null }); }
  savePolicy() {
    if (!this.policy || this.busy() || !this.auth.can('citas', 'editar')) return;
    const data = { horarios: this.policy.horarios.map(day => ({ ...day, descanso_inicio: day.descanso_inicio || null, descanso_fin: day.descanso_fin || null })), excepciones: this.policy.excepciones.map(day => ({ ...day, descanso_inicio: day.descanso_inicio || null, descanso_fin: day.descanso_fin || null })) };
    this.busy.set(true); this.error.set(''); this.message.set('');
    this.policies.saveHours(data).subscribe({ next: policy => { this.policy = policy; this.busy.set(false); this.message.set('Horarios publicados y reservas sincronizados.'); }, error: error => this.fail(error) });
  }
  loadSchedules() {
    const version = ++this.scheduleVersion;
    this.resetSchedule(); this.schedules.set([]); this.error.set(''); this.schedulesLoading.set(!!this.vetId);
    if (this.vetId) this.api.schedules(this.vetId).subscribe({
      next: rows => { if (version === this.scheduleVersion) { this.schedules.set(rows); this.schedulesLoading.set(false); } },
      error: error => { if (version === this.scheduleVersion) { this.error.set(operationError(error)); this.schedulesLoading.set(false); } },
    });
  }
  resetSchedule() { this.editing = undefined; this.schedule = { dia_semana: 0, hora_inicio: '08:00', hora_fin: '12:00', activo: true }; }
  editSchedule(item: Schedule) { this.editing = item.id; this.schedule = { dia_semana: item.dia_semana, hora_inicio: item.hora_inicio, hora_fin: item.hora_fin, activo: item.activo }; }
  saveSchedule() { if (this.busy() || this.schedulesLoading() || !this.vetId || !this.auth.can('citas', this.editing ? 'editar' : 'crear')) return; this.busy.set(true); this.error.set(''); this.message.set(''); this.api.saveSchedule(this.vetId, this.schedule, this.editing).subscribe({ next: () => { this.busy.set(false); this.loadSchedules(); this.message.set('Franja guardada.'); }, error: error => this.fail(error) }); }
  resolve(item: Reschedule, accept: boolean) { if (this.busy() || !this.auth.can('citas', 'editar')) return; this.busy.set(true); this.error.set(''); this.api.resolve(item.id, accept, this.answers[item.id]).subscribe({ next: row => { this.requests.update(rows => rows.map(r => r.id === row.id ? row : r)); this.busy.set(false); this.message.set('Solicitud resuelta.'); }, error: error => this.fail(error) }); }
  date(value: string) { return new Intl.DateTimeFormat('es-PE', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Lima' }).format(new Date(value)); }
  private fail(error: unknown) { this.error.set(operationError(error)); this.busy.set(false); }
}
