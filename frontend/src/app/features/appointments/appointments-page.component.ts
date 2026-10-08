import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toObservable } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { finalize, forkJoin } from 'rxjs';
import { NoticeService } from '../../core/services/notice.service';
import { AuthService } from '../../core/auth/auth.service';
import { AuthDialogService } from '../../core/auth/auth-dialog.service';
import { AppointmentsApiService } from './appointments-api.service';
import { Appointment, AppointmentStatus, AvailabilitySlot, ClinicalRecord, ClinicService, Pet } from './appointments.models';

const BOOKING_DRAFT_KEY = 'clinic_booking_draft_v1';
type BookingDraft = {
  nombreReserva: string;
  servicioId: number;
  fecha: string;
  slot: string;
  motivo: string;
  esUrgente: boolean;
  telefono: string;
  preferenciaContacto: string;
  savedAt: number;
};

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
  readonly auth = inject(AuthService);
  private readonly authDialog = inject(AuthDialogService);
  private readonly router = inject(Router);
  private readonly requestedService = inject(ActivatedRoute).snapshot.queryParamMap.get('servicio');

  readonly pets = signal<Pet[]>([]);
  readonly services = signal<ClinicService[]>([]);
  readonly appointments = signal<Appointment[]>([]);
  readonly loading = signal(true);
  readonly privateLoading = signal(false);
  readonly submitting = signal(false);
  readonly loginPromptOpen = signal(false);
  readonly petSubmitting = signal(false);
  readonly showPetForm = signal(false);
  readonly errorMessage = signal('');
  readonly minDateTime = this.toDateTimeLocal(new Date(Date.now() + 60 * 60 * 1000));
  readonly minDate = this.minDateTime.slice(0, 10);
  readonly availability = signal<AvailabilitySlot[]>([]);
  readonly availabilityLoading = signal(false);
  readonly historyPetId = signal<number | null>(null);
  readonly petHistory = signal<ClinicalRecord[]>([]);
  private availabilityRequest = 0;

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
    nombreReserva: ['', [Validators.required, Validators.maxLength(150)]],
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
    this.restoreDraft();
    this.loadServices();
    toObservable(this.auth.currentUser).pipe(
      takeUntilDestroyed(),
    ).subscribe((user) => {
      this.appointmentForm.controls.nombreReserva.setValue(user?.nombre ?? this.appointmentForm.controls.nombreReserva.value);
      this.pets.set([]);
      this.appointments.set([]);
      this.historyPetId.set(null);
      this.appointmentForm.controls.mascotaId.setValue(0);
      if (user?.tipo === 'cliente') this.loadData();
    });
  }

  private loadServices(): void {
    this.loading.set(true);
    this.errorMessage.set('');
    this.api.getServices().pipe(finalize(() => this.loading.set(false))).subscribe({
      next: (services) => {
        this.services.set(services);
        if (this.appointmentForm.controls.servicioId.value
          && !services.some((service) => service.id === this.appointmentForm.controls.servicioId.value)) {
          this.appointmentForm.patchValue({ servicioId: 0, slot: '' });
          sessionStorage.removeItem(BOOKING_DRAFT_KEY);
          this.errorMessage.set('El servicio seleccionado ya no está disponible. Elige otro.');
        }
        const requested = services.find((service) => service.codigo === this.requestedService);
        if (requested && !this.appointmentForm.controls.servicioId.value) {
          this.appointmentForm.controls.servicioId.setValue(requested.id);
        }
        if (this.appointmentForm.controls.servicioId.value) this.loadAvailability();
      },
      error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
  }

  loadData(): void {
    if (!this.auth.isAuthenticated() || this.auth.currentUser()?.tipo !== 'cliente') return;
    const clientId = this.auth.currentUser()!.id;
    this.privateLoading.set(true);
    forkJoin({
      pets: this.api.getPets(),
      appointments: this.api.getAppointments(),
    }).pipe(finalize(() => this.privateLoading.set(false))).subscribe({
      next: ({ pets, appointments }) => {
        if (this.auth.currentUser()?.id !== clientId) return;
        this.pets.set(pets);
        this.appointments.set(appointments);
        if (!this.appointmentForm.controls.mascotaId.value && pets.length) {
          this.appointmentForm.controls.mascotaId.setValue(pets[0].id);
        }
      },
      error: (error: unknown) => {
        if (this.auth.currentUser()?.id === clientId) this.errorMessage.set(this.errorText(error));
      },
    });
  }

  createPet(): void {
    if (!this.auth.isAuthenticated() || this.auth.currentUser()?.tipo !== 'cliente') return;
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
    if (this.submitting() || this.loginPromptOpen()) return;
    const value = this.appointmentForm.getRawValue();
    if (!value.nombreReserva.trim() || !value.servicioId || !value.fecha || value.fecha < this.minDate || !value.slot || this.availabilityLoading()) {
      this.appointmentForm.markAllAsTouched();
      this.errorMessage.set('Indica el nombre de quien reserva, un servicio, una fecha válida y un horario disponible.');
      return;
    }
    const selectedSlot = this.availability().find((slot) => slot.fecha_hora === value.slot);
    if (!selectedSlot) {
      this.errorMessage.set('Selecciona un horario disponible actualizado.');
      return;
    }
    if (this.auth.isLoading()) return;
    if (!this.auth.isAuthenticated()) {
      this.saveDraft();
      this.notice.show('Para confirmar tu reserva, inicia sesión.');
      this.loginPromptOpen.set(true);
      this.authDialog.open(this.router.url).pipe(
        finalize(() => this.loginPromptOpen.set(false)),
      ).subscribe((authenticated) => {
        if (!authenticated) return;
        if (this.auth.currentUser()?.tipo !== 'cliente') {
          this.errorMessage.set('Para solicitar una cita necesitas una cuenta de cliente.');
          return;
        }
        this.loadAvailability();
        this.notice.show('Sesión iniciada. Revisa tu mascota y confirma la solicitud.');
      });
      return;
    }
    if (this.auth.currentUser()?.tipo !== 'cliente') {
      this.errorMessage.set('Para solicitar una cita necesitas una cuenta de cliente.');
      return;
    }
    if (this.privateLoading()) return;
    if (this.appointmentForm.invalid || !this.pets().some((pet) => pet.id === value.mascotaId)) {
      this.appointmentForm.markAllAsTouched();
      this.showPetForm.set(this.pets().length === 0);
      this.errorMessage.set('Selecciona o registra una mascota para completar la solicitud.');
      return;
    }
    this.submitting.set(true);
    this.errorMessage.set('');
    // A slot may have been taken while the visitor was signing in or editing the form.
    this.api.getAvailability(value.servicioId, value.fecha).subscribe({
      next: (slots) => {
        this.availability.set(slots);
        if (!slots.some((slot) => slot.fecha_hora === selectedSlot.fecha_hora && slot.veterinario_id === selectedSlot.veterinario_id)) {
          this.appointmentForm.controls.slot.setValue('');
          this.submitting.set(false);
          this.errorMessage.set('Ese horario ya no está disponible. Selecciona otro.');
          return;
        }
        if (this.appointmentForm.controls.servicioId.value !== value.servicioId
          || this.appointmentForm.controls.fecha.value !== value.fecha
          || this.appointmentForm.controls.slot.value !== value.slot) {
          this.submitting.set(false);
          return;
        }
        this.createAppointment(value, selectedSlot);
      },
      error: (error: unknown) => {
        this.submitting.set(false);
        this.errorMessage.set(this.errorText(error));
      },
    });
  }

  private createAppointment(value: ReturnType<typeof this.appointmentForm.getRawValue>, selectedSlot: AvailabilitySlot): void {
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
        sessionStorage.removeItem(BOOKING_DRAFT_KEY);
        this.appointments.update((items) => [appointment, ...items]);
          this.appointmentForm.patchValue({ slot: '', motivo: '', esUrgente: false });
          this.loadAvailability();
         this.notice.show('Recibimos tu solicitud. El veterinario se comunicará contigo para coordinar y confirmar la cita.');
      },
      error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
  }

  loadAvailability(clearSlot = false): void {
    const request = ++this.availabilityRequest;
    if (clearSlot) this.appointmentForm.controls.slot.setValue('');
    const { servicioId, fecha } = this.appointmentForm.getRawValue();
    if (!servicioId || !fecha || fecha < this.minDate) {
      this.availability.set([]);
      this.appointmentForm.controls.slot.setValue('');
      this.availabilityLoading.set(false);
      return;
    }
    this.availability.set([]);
    this.availabilityLoading.set(true);
    this.api.getAvailability(servicioId, fecha)
      .pipe(finalize(() => {
        if (request === this.availabilityRequest) this.availabilityLoading.set(false);
      }))
      .subscribe({
        next: (slots) => {
          if (request !== this.availabilityRequest || this.appointmentForm.controls.servicioId.value !== servicioId || this.appointmentForm.controls.fecha.value !== fecha) return;
          this.availability.set(slots);
          if (this.appointmentForm.controls.slot.value && !slots.some((slot) => slot.fecha_hora === this.appointmentForm.controls.slot.value)) {
            this.appointmentForm.controls.slot.setValue('');
            this.errorMessage.set('El horario seleccionado ya no está disponible. Elige otro.');
          }
        },
        error: (error: unknown) => {
          if (request !== this.availabilityRequest) return;
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
       cliente_no_respondio: 'Cliente no respondió', no_asistio: 'Cancelada por inasistencia',
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
       cancelada: 'Esta solicitud fue cancelada.', no_asistio: 'La cita fue cancelada porque no registramos tu llegada dentro del tiempo de tolerancia.',
    };
    return descriptions[status] ?? 'Solicitud en revisión.';
  }

  formatDate(value: string): string {
    return new Intl.DateTimeFormat('es-PE', {
      dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Lima',
    }).format(new Date(value));
  }

  private saveDraft(): void {
    const { nombreReserva, servicioId, fecha, slot, motivo, esUrgente, telefono, preferenciaContacto } = this.appointmentForm.getRawValue();
    const draft: BookingDraft = { nombreReserva, servicioId, fecha, slot, motivo, esUrgente, telefono, preferenciaContacto, savedAt: Date.now() };
    sessionStorage.setItem(BOOKING_DRAFT_KEY, JSON.stringify(draft));
  }

  private restoreDraft(): void {
    const saved = sessionStorage.getItem(BOOKING_DRAFT_KEY);
    if (!saved) return;
    try {
      const draft: BookingDraft = JSON.parse(saved);
      if (typeof draft.servicioId !== 'number' || typeof draft.fecha !== 'string'
        || typeof draft.slot !== 'string' || typeof draft.savedAt !== 'number'
        || Date.now() - draft.savedAt > 60 * 60 * 1000 || draft.fecha < this.minDate) {
        sessionStorage.removeItem(BOOKING_DRAFT_KEY);
        return;
      }
      this.appointmentForm.patchValue({
        nombreReserva: draft.nombreReserva ?? '',
        servicioId: draft.servicioId, fecha: draft.fecha, slot: draft.slot,
        motivo: draft.motivo ?? '', esUrgente: draft.esUrgente ?? false,
        telefono: draft.telefono ?? '', preferenciaContacto: draft.preferenciaContacto ?? 'llamada',
      });
    } catch {
      sessionStorage.removeItem(BOOKING_DRAFT_KEY);
    }
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
