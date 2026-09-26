import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { finalize, forkJoin } from 'rxjs';
import { NoticeService } from '../../core/services/notice.service';
import { AppointmentStatus } from '../appointments/appointments.models';
import { VeterinarianApiService } from './veterinarian-api.service';
import { AppointmentSummary, ClinicalRecord, Notification, ScheduleBlock, VeterinarianAppointment, VeterinarianSchedule } from './veterinarian.models';

@Component({
  selector: 'app-veterinarian-dashboard',
  standalone: true,
  imports: [FormsModule, ReactiveFormsModule],
  templateUrl: './veterinarian-dashboard.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class VeterinarianDashboardComponent {
  private readonly api = inject(VeterinarianApiService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly notice = inject(NoticeService);

  readonly requests = signal<VeterinarianAppointment[]>([]);
  readonly loading = signal(true);
  readonly savingId = signal<number | null>(null);
  readonly errorMessage = signal('');
  readonly summary = signal<AppointmentSummary>({ pendientes: 0, confirmadas: 0, atendidas: 0, proximas: 0 });
  readonly schedules = signal<VeterinarianSchedule[]>([]);
  readonly blocks = signal<ScheduleBlock[]>([]);
  readonly notifications = signal<Notification[]>([]);
  readonly history = signal<ClinicalRecord[]>([]);
  readonly historyPetId = signal<number | null>(null);
  readonly editingScheduleId = signal<number | null>(null);
  readonly attentionId = signal<number | null>(null);
  readonly scheduleForm = { dia_semana: 0, hora_inicio: '08:00', hora_fin: '19:00', activo: true };
  readonly blockForm = { fecha_hora_inicio: '', fecha_hora_fin: '', motivo: '' };
  readonly attentionForm = { observaciones: '', diagnostico: '', tratamiento: '', peso: '', temperatura: '', historial_alergias: '', vacunas: '', desparasitaciones: '', medicamentos: '', procedimientos: '', examenes_resultados: '' };
  readonly filterForm = this.formBuilder.nonNullable.group({ fecha: [''], estado: ['' as AppointmentStatus | ''], busqueda: [''] });
  readonly coordinationNotes: Record<number, string> = {};
  readonly coordinationDates: Record<number, string> = {};

  constructor() { this.load(); }

  load(): void {
    const { fecha, estado, busqueda } = this.filterForm.getRawValue();
    this.loading.set(true);
    forkJoin({
      requests: this.api.getRequests(fecha || undefined, estado || undefined, busqueda || undefined),
      summary: this.api.getSummary(),
      schedules: this.api.getSchedules(),
      blocks: this.api.getBlocks(),
      notifications: this.api.getNotifications(),
    })
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: ({ requests, summary, schedules, blocks, notifications }) => {
          this.requests.set(requests); this.summary.set(summary); this.schedules.set(schedules); this.blocks.set(blocks); this.notifications.set(notifications); this.errorMessage.set('');
        },
        error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
      });
  }

  update(request: VeterinarianAppointment, estado: AppointmentStatus): void {
    const nota = this.coordinationNotes[request.id] || '';
    const propuesta = this.coordinationDates[request.id] || '';
    if (estado === 'requiere_otro_horario' && !propuesta) {
      this.errorMessage.set('Indica el horario alternativo antes de proponerlo.');
      return;
    }
    this.savingId.set(request.id);
    this.api.updateRequest(request.id, {
      estado,
      nota_coordinacion: nota || undefined,
      fecha_hora_propuesta: propuesta ? new Date(propuesta).toISOString() : undefined,
    }).pipe(finalize(() => this.savingId.set(null))).subscribe({
      next: (updated) => {
        this.requests.update((items) => items.map((item) => item.id === updated.id ? updated : item));
        delete this.coordinationNotes[request.id];
        delete this.coordinationDates[request.id];
        this.notice.show('Solicitud actualizada');
      },
      error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
  }

  showHistory(request: VeterinarianAppointment): void {
    if (this.historyPetId() === request.mascota.id) { this.historyPetId.set(null); return; }
    this.api.getPetHistory(request.mascota.id).subscribe({
      next: (history) => { this.history.set(history); this.historyPetId.set(request.mascota.id); },
      error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
  }

  registerAttention(request: VeterinarianAppointment): void {
    this.attentionId.set(request.id);
    this.api.registerAttention(request.id, {
      observaciones: this.attentionForm.observaciones || null,
      diagnostico: this.attentionForm.diagnostico || null,
      tratamiento: this.attentionForm.tratamiento || null,
      peso: this.attentionForm.peso || null,
      temperatura: this.attentionForm.temperatura || null,
      historial_alergias: this.attentionForm.historial_alergias || null,
      vacunas: this.attentionForm.vacunas || null,
      desparasitaciones: this.attentionForm.desparasitaciones || null,
      medicamentos: this.attentionForm.medicamentos || null,
      procedimientos: this.attentionForm.procedimientos || null,
      examenes_resultados: this.attentionForm.examenes_resultados || null,
    }).pipe(finalize(() => this.attentionId.set(null))).subscribe({
      next: () => { this.resetAttention(); this.notice.show('Atención registrada'); this.load(); },
      error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
  }

  createInitialRecord(request: VeterinarianAppointment): void {
    this.attentionId.set(request.id);
    this.api.createInitialHistory(request.mascota.id, this.attentionPayload())
      .pipe(finalize(() => this.attentionId.set(null)))
      .subscribe({
        next: () => { this.resetAttention(); this.notice.show('Ficha clínica creada'); this.load(); },
        error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
      });
  }

  addSchedule(): void {
    const request = this.editingScheduleId() === null
      ? this.api.createSchedule(this.scheduleForm)
      : this.api.updateSchedule(this.editingScheduleId() as number, this.scheduleForm);
    request.subscribe({ next: (schedule) => { this.schedules.update((items) => this.editingScheduleId() === null ? [...items, schedule] : items.map((item) => item.id === schedule.id ? schedule : item)); this.editingScheduleId.set(null); this.notice.show('Horario guardado'); }, error: (error: unknown) => this.errorMessage.set(this.errorText(error)) });
  }

  editSchedule(schedule: VeterinarianSchedule): void { this.editingScheduleId.set(schedule.id); Object.assign(this.scheduleForm, { dia_semana: schedule.dia_semana, hora_inicio: schedule.hora_inicio, hora_fin: schedule.hora_fin, activo: schedule.activo }); }

  addBlock(): void {
    if (!this.blockForm.fecha_hora_inicio || !this.blockForm.fecha_hora_fin || !this.blockForm.motivo) return;
    this.api.createBlock({ ...this.blockForm, fecha_hora_inicio: new Date(this.blockForm.fecha_hora_inicio).toISOString(), fecha_hora_fin: new Date(this.blockForm.fecha_hora_fin).toISOString() }).subscribe({ next: (block) => { this.blocks.update((items) => [...items, block]); this.blockForm.fecha_hora_inicio = ''; this.blockForm.fecha_hora_fin = ''; this.blockForm.motivo = ''; this.notice.show('Bloqueo guardado'); }, error: (error: unknown) => this.errorMessage.set(this.errorText(error)) });
  }

  removeBlock(block: ScheduleBlock): void { this.api.deleteBlock(block.id).subscribe({ next: () => this.blocks.update((items) => items.filter((item) => item.id !== block.id)), error: (error: unknown) => this.errorMessage.set(this.errorText(error)) }); }
  markNotificationRead(notification: Notification): void { if (notification.leida) return; this.api.markNotificationRead(notification.id).subscribe({ next: (updated) => this.notifications.update((items) => items.map((item) => item.id === updated.id ? updated : item)) }); }
  dayLabel(day: number): string { return ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'][day] ?? 'Día'; }

  setProposal(id: number, value: string): void { this.coordinationDates[id] = value; }
  setNote(id: number, value: string): void { this.coordinationNotes[id] = value; }

  resetAttention(): void { Object.assign(this.attentionForm, { observaciones: '', diagnostico: '', tratamiento: '', peso: '', temperatura: '', historial_alergias: '', vacunas: '', desparasitaciones: '', medicamentos: '', procedimientos: '', examenes_resultados: '' }); }

  private attentionPayload(): Record<string, string | null> {
    return Object.fromEntries(Object.entries(this.attentionForm).map(([key, value]) => [key, value || null]));
  }

  formatDate(value: string): string {
    return new Intl.DateTimeFormat('es-PE', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Lima' }).format(new Date(value));
  }

  statusLabel(status: AppointmentStatus): string {
    const labels: Partial<Record<AppointmentStatus, string>> = {
      pendiente_contacto: 'Pendiente de confirmación', contactando_cliente: 'Contactando al cliente',
      esperando_respuesta: 'Esperando respuesta', requiere_otro_horario: 'Requiere otro horario',
      confirmada: 'Confirmada', cancelada: 'Cancelada', cliente_no_respondio: 'Cliente no respondió', atendida: 'Atendida',
    };
    return labels[status] ?? status;
  }

  canUpdate(request: VeterinarianAppointment, next: AppointmentStatus): boolean {
    const transitions: Partial<Record<AppointmentStatus, AppointmentStatus[]>> = {
      pendiente_contacto: ['contactando_cliente', 'esperando_respuesta', 'requiere_otro_horario', 'confirmada', 'cancelada', 'cliente_no_respondio'],
      contactando_cliente: ['esperando_respuesta', 'requiere_otro_horario', 'confirmada', 'cancelada', 'cliente_no_respondio'],
      esperando_respuesta: ['requiere_otro_horario', 'confirmada', 'cancelada', 'cliente_no_respondio'],
      requiere_otro_horario: ['contactando_cliente', 'confirmada', 'cancelada'],
      confirmada: ['cancelada'],
    };
    return transitions[request.estado]?.includes(next) ?? false;
  }

  whatsappUrl(request: VeterinarianAppointment): string {
    if (!request.telefono_contacto) return '';
    const phone = request.telefono_contacto.replace(/\D/g, '');
    const message = encodeURIComponent(`Hola ${request.cliente_nombre}, te contactamos de la Clínica Veterinaria San Martín de Porres por la solicitud para ${request.mascota.nombre}.`);
    return `https://wa.me/${phone}?text=${message}`;
  }

  private errorText(error: unknown): string {
    if (error instanceof HttpErrorResponse && typeof error.error?.detail === 'string') return error.error.detail;
    return 'No se pudo cargar o actualizar la solicitud.';
  }
}
