import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { ClinicService, Pet } from '../appointments/appointments.models';
import { VeterinarianApiService } from './veterinarian-api.service';
import { VeterinarianClient } from './veterinarian.models';

interface ClinicalField {
  key: 'anamnesis' | 'observaciones' | 'diagnostico' | 'tratamiento' | 'historial_alergias' | 'vacunas' | 'desparasitaciones' | 'medicamentos' | 'procedimientos' | 'examenes_resultados';
  label: string;
  placeholder: string;
}

interface ClinicalProfile {
  title: string;
  hint: string;
  fields: ClinicalField[];
}

const FIELD = (key: ClinicalField['key'], label: string, placeholder: string): ClinicalField => ({ key, label, placeholder });

const PROFILES: Array<{ match: RegExp; profile: ClinicalProfile }> = [
  { match: /urgencia|emergencia/i, profile: { title: 'Triaje y estabilización', hint: 'Registra la prioridad y las medidas tomadas durante la emergencia.', fields: [FIELD('anamnesis', 'Motivo de emergencia', 'Signos, tiempo de evolución y antecedentes relevantes'), FIELD('observaciones', 'Estado y nivel de triaje', 'Conciencia, mucosas, hidratación y prioridad'), FIELD('procedimientos', 'Estabilización', 'Oxígeno, fluidoterapia, procedimientos realizados'), FIELD('medicamentos', 'Medicación administrada', 'Fármaco, dosis, vía y hora'), FIELD('diagnostico', 'Destino del paciente', 'Alta, hospitalización, cirugía o referencia')] } },
  { match: /vacun/i, profile: { title: 'Control de vacunación', hint: 'Completa los datos de la vacuna para mantener el carné del paciente.', fields: [FIELD('vacunas', 'Vacuna, dosis y lote', 'Ej.: Quíntuple · 1ra dosis · lote A123 · laboratorio'), FIELD('observaciones', 'Evaluación previa y reacción', 'Estado general, indicaciones y reacción adversa')] } },
  { match: /desparasit|antiparas/i, profile: { title: 'Control antiparasitario', hint: 'Registra producto, dosis y la fecha del siguiente control.', fields: [FIELD('desparasitaciones', 'Producto y aplicación', 'Interna o externa, producto, dosis y vía'), FIELD('observaciones', 'Indicaciones', 'Cuidados, alertas y recomendaciones al propietario')] } },
  { match: /rayos|radiograf|ecograf|imagen/i, profile: { title: 'Estudio diagnóstico', hint: 'Deja trazabilidad del estudio, hallazgos e impresión diagnóstica.', fields: [FIELD('examenes_resultados', 'Estudio y resultados', 'Región, proyecciones, hallazgos y conclusión'), FIELD('observaciones', 'Preparación o sedación', 'Ayuno, sedación, técnica y observaciones')] } },
  { match: /laboratorio|hemograma|urian|bioquím|citolog|raspado/i, profile: { title: 'Laboratorio y análisis', hint: 'Asocia la muestra y la interpretación al historial clínico.', fields: [FIELD('examenes_resultados', 'Muestra y resultados', 'Examen, muestra, valores relevantes y unidades'), FIELD('diagnostico', 'Interpretación', 'Lectura clínica y diagnóstico sugerido')] } },
  { match: /cirug|esteriliz|castr|operac/i, profile: { title: 'Registro quirúrgico', hint: 'Documenta el procedimiento y las indicaciones posteriores.', fields: [FIELD('procedimientos', 'Procedimiento quirúrgico', 'Técnica, cirujano, anestesia, duración y complicaciones'), FIELD('medicamentos', 'Anestesia y medicación', 'Inducción, mantenimiento, analgésicos y antibióticos'), FIELD('observaciones', 'Indicaciones postoperatorias', 'Cuidados, retiro de puntos y signos de alarma')] } },
  { match: /hospital|intern/i, profile: { title: 'Evolución de hospitalización', hint: 'Registra la evolución, fluidoterapia, alimentación y medicación.', fields: [FIELD('observaciones', 'Evolución diaria', 'Signos, respuesta al tratamiento y alimentación'), FIELD('medicamentos', 'Medicación y fluidoterapia', 'Fármaco, dosis, vía, frecuencia y fluidos'), FIELD('procedimientos', 'Cuidados y procedimientos', 'Curaciones, controles y fecha de alta')] } },
  { match: /baño|bano|est[eé]tica|peluquer|corte|uñas|unas|oído|oido|groom/i, profile: { title: 'Ficha de estética y bienestar', hint: 'Registra el servicio realizado y cualquier hallazgo que requiera seguimiento.', fields: [FIELD('procedimientos', 'Servicio realizado', 'Baño, corte, uñas, oídos, productos y estilista'), FIELD('observaciones', 'Estado de piel y conducta', 'Piel, nudos, parásitos, reacción y recomendaciones')] } },
];

const DEFAULT_PROFILE: ClinicalProfile = {
  title: 'Consulta clínica',
  hint: 'Registra la evaluación completa, el diagnóstico y el plan terapéutico.',
  fields: [
    FIELD('anamnesis', 'Anamnesis y antecedentes', 'Lo informado por el propietario y evolución del motivo'),
    FIELD('diagnostico', 'Diagnóstico presuntivo', 'Hallazgos y diagnóstico clínico'),
    FIELD('tratamiento', 'Tratamiento e indicaciones', 'Medicamentos, dosis, cuidados y recomendaciones'),
    FIELD('observaciones', 'Examen físico', 'Mucosas, hidratación, condición corporal y hallazgos'),
  ],
};

@Component({
  selector: 'app-veterinarian-new-attention',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './veterinarian-new-attention.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class VeterinarianNewAttentionComponent {
  private readonly api = inject(VeterinarianApiService);
  private readonly formBuilder = inject(FormBuilder);

  readonly step = signal(1);
  readonly clients = signal<VeterinarianClient[]>([]);
  readonly pets = signal<Pet[]>([]);
  readonly services = signal<ClinicService[]>([]);
  readonly query = signal('');
  readonly selectedClient = signal<VeterinarianClient | null>(null);
  readonly selectedPet = signal<Pet | null>(null);
  readonly selectedService = signal<ClinicService | null>(null);
  readonly saving = signal(false);
  readonly loading = signal(false);
  readonly errorMessage = signal('');
  readonly today = new Date().toISOString().slice(0, 10);

  readonly filteredClients = computed(() => {
    const query = this.query().trim().toLocaleLowerCase('es');
    return this.clients().filter((client) => !query || `${client.nombre} ${client.correo} ${client.telefono || ''}`.toLocaleLowerCase('es').includes(query));
  });
  readonly clinicalProfile = computed(() => {
    const name = this.selectedService()?.nombre || '';
    return PROFILES.find((item) => item.match.test(name))?.profile || DEFAULT_PROFILE;
  });
  readonly isPreventive = computed(() => /vacun|desparasit/i.test(this.selectedService()?.nombre || ''));

  readonly serviceCategories = ['Atención médica', 'Prevención', 'Diagnóstico'];
  readonly clientForm = this.formBuilder.nonNullable.group({ nombre: ['', [Validators.required, Validators.minLength(2)]], correo: ['', [Validators.required, Validators.email]], telefono: [''], direccion: [''] });
  readonly petForm = this.formBuilder.nonNullable.group({ nombre: ['', Validators.required], especie: ['', Validators.required], raza: [''], sexo: [''], fecha_nacimiento: [''], peso_actual: [''], caracteristicas: [''] });
  readonly attentionForm = this.formBuilder.nonNullable.group({ motivo_consulta: [''], anamnesis: [''], observaciones: [''], diagnostico: [''], tratamiento: [''], peso: [''], temperatura: [''], historial_alergias: [''], vacunas: [''], desparasitaciones: [''], medicamentos: [''], procedimientos: [''], examenes_resultados: [''], proxima_fecha_control: [''] });

  constructor() {
    this.loadClients();
  }

  loadClients(): void {
    this.loading.set(true);
    this.api.getClients().pipe(finalize(() => this.loading.set(false))).subscribe({ next: (clients) => this.clients.set(clients), error: (error: unknown) => this.showError(error) });
  }

  selectClient(client: VeterinarianClient): void { this.selectedClient.set(client); }

  createClient(): void {
    if (this.clientForm.invalid) { this.clientForm.markAllAsTouched(); return; }
    this.save(this.api.createClient(this.clientForm.getRawValue()), (client) => { this.clients.update((items) => [...items, client]); this.selectClient(client); this.goToPets(); });
  }

  goToPets(): void {
    const client = this.selectedClient();
    if (!client) return;
    this.api.getPetsForClient(client.id).subscribe({ next: (pets) => { this.pets.set(pets); this.step.set(2); }, error: (error: unknown) => this.showError(error) });
  }

  selectPet(pet: Pet): void { this.selectedPet.set(pet); }

  createPet(): void {
    const client = this.selectedClient();
    if (!client || this.petForm.invalid) { this.petForm.markAllAsTouched(); return; }
    this.save(this.api.createPet(client.id, this.petForm.getRawValue()), (pet) => { this.pets.update((items) => [...items, pet]); this.selectPet(pet); this.petForm.reset(); });
  }

  goToServices(): void {
    this.loading.set(true);
    this.api.getServices().pipe(finalize(() => this.loading.set(false))).subscribe({ next: (services) => { this.services.set(services); this.step.set(3); }, error: (error: unknown) => this.showError(error) });
  }

  selectService(service: ClinicService): void {
    this.selectedService.set(service);
    this.attentionForm.patchValue({ motivo_consulta: '', proxima_fecha_control: '' });
  }

  categoryServices(category: string): ClinicService[] {
    const patterns: Record<string, RegExp> = {
      'Atención médica': /consulta|tratamiento|cirug|traumat|intern|hospital|urgencia|domicilio/i,
      Prevención: /vacun|desparasit|profilaxis|dental|microchip/i,
      Diagnóstico: /laboratorio|ecograf|rayos|imagen|radiograf/i,
    };
    return this.services().filter((service) => patterns[category]?.test(service.nombre));
  }

  goToAttention(): void {
    if (!this.selectedService()) return;
    this.attentionForm.patchValue({ motivo_consulta: this.selectedService()?.nombre || '' });
    this.step.set(4);
  }

  previousStep(): void { this.step.update((value) => Math.max(1, value - 1)); }

  finishAttention(): void {
    const pet = this.selectedPet();
    const service = this.selectedService();
    if (!pet || !service || this.attentionForm.invalid) return;
    this.saving.set(true);
    const raw = this.attentionForm.getRawValue();
    const form = {
      ...raw,
      peso: raw.peso || null,
      temperatura: raw.temperatura || null,
      proxima_fecha_control: raw.proxima_fecha_control || null,
    };
    this.api.startWalkIn({ mascota_id: pet.id, servicio_id: service.id, motivo: form.motivo_consulta || undefined, es_urgente: /urgencia|emergencia/i.test(service.nombre) }).pipe(finalize(() => this.saving.set(false))).subscribe({
      next: (appointment) => this.api.registerAttention(appointment.id, form).subscribe({ next: () => this.resetFlow(), error: (error: unknown) => this.showError(error) }),
      error: (error: unknown) => this.showError(error),
    });
  }

  resetFlow(): void {
    this.step.set(1); this.selectedClient.set(null); this.selectedPet.set(null); this.selectedService.set(null); this.query.set(''); this.clientForm.reset(); this.petForm.reset(); this.attentionForm.reset();
    this.loadClients();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  private save<T>(request: import('rxjs').Observable<T>, success: (value: T) => void): void {
    this.saving.set(true);
    request.pipe(finalize(() => this.saving.set(false))).subscribe({ next: success, error: (error: unknown) => this.showError(error) });
  }

  private showError(error: unknown): void {
    if (error instanceof HttpErrorResponse && typeof error.error?.detail === 'string') this.errorMessage.set(error.error.detail);
    else if (error instanceof HttpErrorResponse && Array.isArray(error.error?.detail)) this.errorMessage.set(error.error.detail.map((item: { loc?: unknown[]; msg?: string }) => `${item.loc?.slice(-1)[0] || 'campo'}: ${item.msg || 'valor inválido'}`).join(' · '));
    else this.errorMessage.set('No se pudo completar este paso. Revisa la conexión e inténtalo nuevamente.');
  }
}
