import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { finalize, forkJoin } from 'rxjs';
import { NoticeService } from '../../core/services/notice.service';
import { AppointmentsApiService } from './appointments-api.service';
import { Appointment, AppointmentStatus, ClinicService, Pet } from './appointments.models';

@Component({
  selector: 'app-appointments-page',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './appointments-page.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppointmentsPageComponent {
  private readonly api = inject(AppointmentsApiService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly notice = inject(NoticeService);
  private readonly requestedService = inject(ActivatedRoute).snapshot.queryParamMap.get('servicio');

  readonly pets = signal<Pet[]>([]);
  readonly services = signal<ClinicService[]>([]);
  readonly appointments = signal<Appointment[]>([]);
  readonly loading = signal(true);
  readonly submitting = signal(false);
  readonly petSubmitting = signal(false);
  readonly showPetForm = signal(false);
  readonly errorMessage = signal('');
  readonly minDateTime = this.toDateTimeLocal(new Date(Date.now() + 60 * 60 * 1000));

  readonly petForm = this.formBuilder.nonNullable.group({
    nombre: ['', [Validators.required, Validators.maxLength(100)]],
    especie: ['Perro', [Validators.required, Validators.maxLength(80)]],
    raza: ['', Validators.maxLength(100)],
  });
  readonly appointmentForm = this.formBuilder.nonNullable.group({
    mascotaId: [0, Validators.min(1)],
    servicioId: [0, Validators.min(1)],
    fechaHora: ['', Validators.required],
    motivo: ['', Validators.maxLength(500)],
    esUrgente: [false],
  });

  constructor() {
    this.loadData();
  }

  loadData(): void {
    this.loading.set(true);
    this.errorMessage.set('');
    forkJoin({
      pets: this.api.getPets(),
      services: this.api.getServices(),
      appointments: this.api.getAppointments(),
    }).pipe(finalize(() => this.loading.set(false))).subscribe({
      next: ({ pets, services, appointments }) => {
        this.pets.set(pets);
        this.services.set(services);
        this.appointments.set(appointments);
        if (!this.appointmentForm.controls.mascotaId.value && pets.length) {
          this.appointmentForm.controls.mascotaId.setValue(pets[0].id);
        }
        const requested = services.find((service) => service.codigo === this.requestedService);
        if (requested) this.appointmentForm.controls.servicioId.setValue(requested.id);
      },
      error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
  }

  createPet(): void {
    if (this.petForm.invalid) {
      this.petForm.markAllAsTouched();
      return;
    }
    this.petSubmitting.set(true);
    const value = this.petForm.getRawValue();
    this.api.createPet({ ...value, raza: value.raza || undefined })
      .pipe(finalize(() => this.petSubmitting.set(false)))
      .subscribe({
        next: (pet) => {
          this.pets.update((pets) => [...pets, pet]);
          this.appointmentForm.controls.mascotaId.setValue(pet.id);
          this.petForm.reset({ nombre: '', especie: 'Perro', raza: '' });
          this.showPetForm.set(false);
          this.notice.show('Mascota registrada');
        },
        error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
      });
  }

  schedule(): void {
    if (this.appointmentForm.invalid) {
      this.appointmentForm.markAllAsTouched();
      return;
    }
    const value = this.appointmentForm.getRawValue();
    this.submitting.set(true);
    this.errorMessage.set('');
    this.api.createAppointment({
      mascota_id: value.mascotaId,
      servicio_id: value.servicioId,
      fecha_hora_programada: new Date(value.fechaHora).toISOString(),
      motivo: value.motivo || undefined,
      es_urgente: value.esUrgente,
    }).pipe(finalize(() => this.submitting.set(false))).subscribe({
      next: (appointment) => {
        this.appointments.update((items) => [appointment, ...items]);
        this.appointmentForm.patchValue({ fechaHora: '', motivo: '', esUrgente: false });
        this.notice.show('Cita registrada y pendiente de confirmacion');
      },
      error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
  }

  cancel(appointment: Appointment): void {
    if (!window.confirm('¿Deseas cancelar esta cita?')) return;
    this.api.cancelAppointment(appointment.id).subscribe({
      next: (updated) => {
        this.appointments.update((items) => items.map((item) => item.id === updated.id ? updated : item));
        this.notice.show('Cita cancelada');
      },
      error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
  }

  canCancel(appointment: Appointment): boolean {
    return ['pendiente', 'confirmada', 'reprogramada'].includes(appointment.estado);
  }

  statusLabel(status: AppointmentStatus): string {
    const labels: Record<AppointmentStatus, string> = {
      pendiente: 'Pendiente', confirmada: 'Confirmada', reprogramada: 'Reprogramada',
      atendida: 'Atendida', cancelada: 'Cancelada', no_asistio: 'No asistio',
    };
    return labels[status];
  }

  statusClass(status: AppointmentStatus): string {
    if (status === 'confirmada' || status === 'atendida') return 'bg-emerald-100 text-emerald-700';
    if (status === 'cancelada' || status === 'no_asistio') return 'bg-rose-100 text-rose-700';
    return 'bg-amber-100 text-amber-800';
  }

  formatDate(value: string): string {
    return new Intl.DateTimeFormat('es-PE', {
      dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Lima',
    }).format(new Date(value));
  }

  money(value: string): string {
    return Number(value).toFixed(2);
  }

  private toDateTimeLocal(date: Date): string {
    const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
    return local.toISOString().slice(0, 16);
  }

  private errorText(error: unknown): string {
    if (error instanceof HttpErrorResponse && typeof error.error?.detail === 'string') {
      return error.error.detail;
    }
    return 'No se pudo completar la operacion. Intenta nuevamente.';
  }
}
