import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize, forkJoin, of } from 'rxjs';
import { NoticeService } from '../../../../core/services/notice.service';
import { AdminApiService, AdminAppointment, AppointmentReport, CatalogOption } from '../../services/admin-api.service';
import { clinicToday } from '../../../veterinarian/veterinarian.models';
import { PageHeaderComponent } from '../../shared/page-header.component';

@Component({ selector: 'app-admin-citas', standalone: true, imports: [FormsModule, PageHeaderComponent], templateUrl: './citas.component.html', styleUrl: '../../shared/admin-ui.css', changeDetection: ChangeDetectionStrategy.OnPush })
export class CitasComponent {
  private readonly api = inject(AdminApiService);
  private readonly notice = inject(NoticeService);
  readonly date = signal(clinicToday().slice(0, 7) + '-01'); readonly status = signal(''); readonly appointments = signal<AdminAppointment[]>([]); readonly loading = signal(true); readonly error = signal('');
  readonly endDate = signal(clinicToday());
  readonly onlyUrgent = signal(false);
  readonly report = signal<AppointmentReport | null>(null);
  readonly reportRows = computed(() => Object.entries(this.report()?.por_estado || {}).map(([state, count]) => ({ state, count, label: this.statusLabel(state) })));
  readonly urgentPending = computed(() => this.appointments().filter(item => item.es_urgente && this.canEdit(item)).length);
  readonly veterinarians = signal<CatalogOption[]>([]);
  readonly editing = signal<AdminAppointment | null>(null);
  readonly saving = signal(false);
  readonly formError = signal('');
  readonly states = [
    { value: 'pendiente', label: 'Pendiente' }, { value: 'pendiente_contacto', label: 'Por confirmar' },
    { value: 'contactando_cliente', label: 'Contactando' }, { value: 'esperando_respuesta', label: 'Esperando respuesta' },
    { value: 'requiere_otro_horario', label: 'Requiere otro horario' }, { value: 'confirmada', label: 'Confirmada' },
    { value: 'reprogramada', label: 'Reprogramada' }, { value: 'cancelada', label: 'Cancelada' },
    { value: 'cliente_no_respondio', label: 'Cliente no respondió' }, { value: 'no_asistio', label: 'No asistió' },
  ];
  form = { estado: '', veterinario_id: null as number | null, fecha: '', nota_coordinacion: '' };
  private loadVersion = 0;
  constructor() { this.load(); }
  load(): void {
    if (this.date() && this.endDate() && this.date() > this.endDate()) { this.error.set('La fecha inicial debe ser anterior o igual a la final.'); return; }
    const version = ++this.loadVersion;
    this.loading.set(true);
    forkJoin({ appointments: this.api.getAppointments(this.date() || undefined, this.status() || undefined, this.endDate() || undefined, this.onlyUrgent()), veterinarians: this.api.getAppointmentVeterinarians(), report: this.date() && this.endDate() ? this.api.getAppointmentReport(this.date(), this.endDate()) : of(null) })
      .pipe(finalize(() => { if (version === this.loadVersion) this.loading.set(false); })).subscribe({
        next: ({ appointments, veterinarians, report }) => { if (version !== this.loadVersion) return; this.appointments.set(appointments); this.veterinarians.set(veterinarians); this.report.set(report); this.error.set(''); },
        error: (error: unknown) => { if (version === this.loadVersion) this.error.set(this.errorText(error)); },
      });
  }
  canEdit(item: AdminAppointment): boolean { return !['atendida', 'cancelada', 'no_asistio'].includes(item.estado); }
  edit(item: AdminAppointment): void {
    this.form = { estado: item.estado, veterinario_id: item.veterinario_id, fecha: this.localDate(item.fecha_hora_programada), nota_coordinacion: item.nota_coordinacion || '' };
    this.formError.set(''); this.editing.set(item);
  }
  close(): void { if (!this.saving()) this.editing.set(null); }
  save(): void {
    const item = this.editing();
    if (!item || this.saving() || !this.form.fecha) return;
    const changedTime = this.form.fecha !== this.localDate(item.fecha_hora_programada);
    const changedVet = this.form.veterinario_id !== item.veterinario_id;
    const state = (changedTime || changedVet) && ['confirmada', 'reprogramada'].includes(item.estado) && this.form.estado === item.estado ? 'reprogramada' : this.form.estado;
    this.saving.set(true); this.formError.set('');
    this.api.updateAppointment(item.id, {
      estado: state, nota_coordinacion: this.form.nota_coordinacion.trim(),
      ...(changedTime ? { fecha_hora_programada: `${this.form.fecha}:00-05:00` } : {}),
      ...(changedVet ? { veterinario_id: this.form.veterinario_id } : {}),
    }).pipe(finalize(() => this.saving.set(false))).subscribe({
      next: () => { this.editing.set(null); this.notice.show('Cita actualizada'); this.load(); },
      error: (error: unknown) => this.formError.set(this.errorText(error)),
    });
  }
  statusLabel(state: string): string { return state === 'atendida' ? 'Atendida' : this.states.find(item => item.value === state)?.label || state; }
  private localDate(value: string): string { return new Intl.DateTimeFormat('sv-SE', { timeZone: 'America/Lima', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date(value)).replace(' ', 'T'); }
  formatDate(value: string): string { return new Intl.DateTimeFormat('es-PE', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Lima' }).format(new Date(value)); }
  private errorText(error: unknown): string { if (error instanceof HttpErrorResponse && typeof error.error?.detail === 'string') return error.error.detail; if (error instanceof HttpErrorResponse && Array.isArray(error.error?.detail)) return error.error.detail.map((item: { msg: string }) => item.msg).join(' · '); return 'No se pudo completar la operación de citas.'; }
}
