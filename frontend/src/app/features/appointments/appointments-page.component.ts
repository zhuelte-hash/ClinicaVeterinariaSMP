import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { finalize, forkJoin } from 'rxjs';
import { NoticeService } from '../../core/services/notice.service';
import { AuthService } from '../../core/auth/auth.service';
import { AppointmentsApiService } from './appointments-api.service';
import { Appointment, AppointmentStatus, AvailabilitySlot, ClinicalRecord, ClinicService, Pet } from './appointments.models';

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
  private readonly auth = inject(AuthService);
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
  readonly minDate = this.minDateTime.slice(0, 10);
  readonly availability = signal<AvailabilitySlot[]>([]);
  readonly availabilityLoading = signal(false);
  readonly historyPetId = signal<number | null>(null);
  readonly petHistory = signal<ClinicalRecord[]>([]);

  readonly petForm = this.formBuilder.nonNullable.group({
    nombre: ['', [Validators.required, Validators.maxLength(100)]],
    especie: ['Perro', [Validators.required, Validators.maxLength(80)]],
    raza: ['', Validators.maxLength(100)],
    sexo: [''],
    fecha_nacimiento: [''],
    peso_actual: [''],
    caracteristicas: ['', Validators.maxLength(2000)],
  });
  readonly appointmentForm = this.formBuilder.nonNullable.group({
    mascotaId: [0, Validators.min(1)],
    servicioId: [0, Validators.min(1)],
    fecha: [this.minDate, Validators.required],
    slot: ['', Validators.required],
    motivo: ['', Validators.maxLength(500)],
    esUrgente: [false],
    telefono: [this.auth.currentUser()?.telefono ?? '', Validators.maxLength(30)],
    preferenciaContacto: ['llamada'],
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
        if (this.appointmentForm.controls.servicioId.value) this.loadAvailability();
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
     this.api.createPet({
       ...value,
       raza: value.raza || undefined,
       sexo: value.sexo || undefined,
       fecha_nacimiento: value.fecha_nacimiento || undefined,
       peso_actual: value.peso_actual || undefined,
       caracteristicas: value.caracteristicas || undefined,
     })
      .pipe(finalize(() => this.petSubmitting.set(false)))
      .subscribe({
        next: (pet) => {
          this.pets.update((pets) => [...pets, pet]);
          this.appointmentForm.controls.mascotaId.setValue(pet.id);
           this.petForm.reset({ nombre: '', especie: 'Perro', raza: '', sexo: '', fecha_nacimiento: '', peso_actual: '', caracteristicas: '' });
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
    const selectedSlot = this.availability().find((slot) => slot.fecha_hora === value.slot);
    if (!selectedSlot) {
      this.errorMessage.set('Selecciona un horario disponible actualizado.');
      return;
    }
    this.submitting.set(true);
    this.errorMessage.set('');
    this.api.createAppointment({
      mascota_id: value.mascotaId,
      servicio_id: value.servicioId,
      veterinario_id: selectedSlot.veterinario_id,
      fecha_hora_programada: value.slot,
      motivo: value.motivo || undefined,
        es_urgente: value.esUrgente,
        telefono_contacto: value.telefono || undefined,
        preferencia_contacto: value.preferenciaContacto || undefined,
    }).pipe(finalize(() => this.submitting.set(false))).subscribe({
      next: (appointment) => {
        this.appointments.update((items) => [appointment, ...items]);
          this.appointmentForm.patchValue({ slot: '', motivo: '', esUrgente: false });
          this.loadAvailability();
         this.notice.show('Recibimos tu solicitud. El veterinario se comunicará contigo para coordinar y confirmar la cita.');
      },
      error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
  }

  loadAvailability(): void {
    const { servicioId, fecha } = this.appointmentForm.getRawValue();
    if (!servicioId || !fecha) {
      this.availability.set([]);
      return;
    }
    this.availabilityLoading.set(true);
    this.api.getAvailability(servicioId, fecha)
      .pipe(finalize(() => this.availabilityLoading.set(false)))
      .subscribe({
        next: (slots) => this.availability.set(slots),
        error: (error: unknown) => {
          this.availability.set([]);
          this.errorMessage.set(this.errorText(error));
        },
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

  acceptProposedTime(appointment: Appointment): void {
    this.api.acceptProposedTime(appointment.id).subscribe({
      next: (updated) => {
        this.appointments.update((items) => items.map((item) => item.id === updated.id ? updated : item));
        this.notice.show('Horario confirmado');
      },
      error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
  }

  showHistory(pet: Pet): void {
    if (this.historyPetId() === pet.id) {
      this.historyPetId.set(null);
      return;
    }
    this.api.getPetHistory(pet.id).subscribe({
      next: (history) => { this.petHistory.set(history); this.historyPetId.set(pet.id); },
      error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
  }

  canCancel(appointment: Appointment): boolean {
    return !['cancelada', 'atendida', 'no_asistio'].includes(appointment.estado);
  }

  statusLabel(status: AppointmentStatus): string {
    const labels: Record<AppointmentStatus, string> = {
       pendiente: 'Pendiente', pendiente_contacto: 'Pendiente de confirmación',
      contactando_cliente: 'Contactando al cliente', esperando_respuesta: 'Esperando respuesta',
      requiere_otro_horario: 'Requiere otro horario', confirmada: 'Confirmada',
      reprogramada: 'Reprogramada', atendida: 'Atendida', cancelada: 'Cancelada',
      cliente_no_respondio: 'Cliente no respondió', no_asistio: 'No asistió',
    };
    return labels[status];
  }

  statusClass(status: AppointmentStatus): string {
    if (status === 'confirmada' || status === 'atendida') return 'bg-emerald-100 text-emerald-700';
    if (status === 'cancelada' || status === 'no_asistio') return 'bg-rose-100 text-rose-700';
    return 'bg-amber-100 text-amber-800';
  }

  statusDescription(status: AppointmentStatus): string {
    const descriptions: Partial<Record<AppointmentStatus, string>> = {
      pendiente_contacto: 'Solicitud recibida. El veterinario revisará y confirmará contigo.',
      contactando_cliente: 'El veterinario está intentando contactarte.',
      esperando_respuesta: 'El veterinario espera tu respuesta para continuar.',
      requiere_otro_horario: 'El veterinario propuso otro horario. Revísalo y acéptalo.',
      confirmada: 'Tu cita está confirmada.',
      reprogramada: 'Aceptaste el nuevo horario y la cita está confirmada.',
      atendida: 'La atención fue registrada en el historial de tu mascota.',
      cancelada: 'Esta solicitud fue cancelada.',
    };
    return descriptions[status] ?? 'Solicitud en revisión.';
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
