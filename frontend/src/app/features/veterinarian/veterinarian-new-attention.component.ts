import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { ClinicService, Pet } from '../appointments/appointments.models';
import { VeterinarianApiService } from './veterinarian-api.service';
import { clinicToday, VeterinarianClient } from './veterinarian.models';

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

const PROFILES: Array<{ code: RegExp; name: RegExp; profile: ClinicalProfile }> = [
  { code: /urgencias-24-horas/i, name: /urgencia|emergencia/i, profile: { title: 'Triaje y estabilización', hint: 'Registra prioridad, signos críticos y las medidas tomadas durante la emergencia.', fields: [FIELD('anamnesis', 'Motivo y tiempo de emergencia', 'Signos, tiempo de evolución y antecedentes relevantes'), FIELD('observaciones', 'Estado y nivel de triaje', 'Conciencia, mucosas, hidratación y prioridad'), FIELD('procedimientos', 'Estabilización', 'Oxígeno, fluidoterapia y procedimientos realizados'), FIELD('medicamentos', 'Medicación administrada', 'Fármaco, dosis, vía y hora'), FIELD('diagnostico', 'Destino del paciente', 'Alta, hospitalización, cirugía o referencia')] } },
  { code: /vacunacion/i, name: /vacun/i, profile: { title: 'Control de vacunación', hint: 'Estos datos quedan en Vacunas y desparasitación dentro del historial.', fields: [FIELD('vacunas', 'Vacuna, dosis y lote', 'Nombre, número de dosis, lote y laboratorio'), FIELD('observaciones', 'Evaluación y reacción', 'Estado previo, indicaciones y reacción adversa')] } },
  { code: /desparasitacion|aplicacion-de-antipulgas/i, name: /desparasit|antiparas/i, profile: { title: 'Control antiparasitario', hint: 'Registra el producto aplicado y programa el siguiente control.', fields: [FIELD('desparasitaciones', 'Producto y aplicación', 'Interna o externa, producto, dosis y vía'), FIELD('observaciones', 'Indicaciones', 'Cuidados, alertas y recomendaciones al propietario')] } },
  { code: /ecografia|rayos-x/i, name: /rayos|radiograf|ecograf|imagen/i, profile: { title: 'Estudio diagnóstico por imágenes', hint: 'El resultado y los archivos quedarán vinculados a este registro.', fields: [FIELD('examenes_resultados', 'Estudio y hallazgos', 'Región, proyecciones, hallazgos y conclusión'), FIELD('observaciones', 'Preparación o sedación', 'Ayuno, sedación, técnica y observaciones')] } },
  { code: /laboratorio-clinico/i, name: /laboratorio|hemograma|urian|bioquím|citolog|raspado/i, profile: { title: 'Laboratorio y análisis', hint: 'Asocia la muestra, los valores y la interpretación al historial.', fields: [FIELD('examenes_resultados', 'Muestra y resultados', 'Examen, muestra, valores, unidades y rangos'), FIELD('diagnostico', 'Interpretación clínica', 'Lectura de resultados y diagnóstico sugerido')] } },
  { code: /cirugia-general|cirugia-dental/i, name: /cirug|esteriliz|castr|operac/i, profile: { title: 'Registro quirúrgico', hint: 'Documenta el procedimiento, la anestesia y las indicaciones posteriores.', fields: [FIELD('procedimientos', 'Procedimiento quirúrgico', 'Técnica, cirujano, anestesia, duración y complicaciones'), FIELD('medicamentos', 'Anestesia y medicación', 'Inducción, mantenimiento, analgésicos y antibióticos'), FIELD('observaciones', 'Indicaciones postoperatorias', 'Cuidados, retiro de puntos y signos de alarma')] } },
  { code: /internamientos|hospedaje/i, name: /hospital|intern|hospedaje/i, profile: { title: 'Evolución de hospitalización', hint: 'Registra ingreso, evolución, medicación, alimentación y alta.', fields: [FIELD('observaciones', 'Evolución diaria', 'Signos, respuesta al tratamiento y alimentación'), FIELD('medicamentos', 'Medicación y fluidoterapia', 'Fármaco, dosis, vía, frecuencia y fluidos'), FIELD('procedimientos', 'Cuidados, box y alta', 'Curaciones, controles, ubicación y fecha de alta')] } },
  { code: /traumatologia/i, name: /traumatolog/i, profile: { title: 'Evaluación traumatológica', hint: 'Registra la lesión, movilidad, estudios solicitados y plan de recuperación.', fields: [FIELD('anamnesis', 'Lesión y mecanismo', 'Zona afectada, fecha, mecanismo y evolución'), FIELD('observaciones', 'Exploración y movilidad', 'Dolor, inflamación, apoyo, rango articular y hallazgos'), FIELD('examenes_resultados', 'Imágenes y resultados', 'Radiografías, ecografía, hallazgos y conclusión'), FIELD('tratamiento', 'Plan de recuperación', 'Inmovilización, ejercicios, medicación y controles')] } },
  { code: /tratamientos|farmacia-veterinaria/i, name: /tratamiento|farmacia/i, profile: { title: 'Plan de tratamiento', hint: 'Registra la indicación completa y el seguimiento de la terapia.', fields: [FIELD('diagnostico', 'Diagnóstico relacionado', 'Condición tratada y objetivos'), FIELD('medicamentos', 'Medicamentos y dosis', 'Medicamento, presentación, dosis, vía y frecuencia'), FIELD('tratamiento', 'Indicaciones y duración', 'Duración, cuidados, restricciones y próximo control')] } },
  { code: /servicio-a-domicilio/i, name: /domicilio/i, profile: { title: 'Atención a domicilio', hint: 'Registra el lugar, motivo, evaluación y recomendaciones de la visita.', fields: [FIELD('anamnesis', 'Motivo de visita', 'Solicitud del propietario, ubicación y antecedentes'), FIELD('observaciones', 'Evaluación en domicilio', 'Hallazgos, ambiente y condición del paciente'), FIELD('tratamiento', 'Indicaciones y seguimiento', 'Tratamiento, cuidados y próxima visita')] } },
  { code: /bano-|cepillado|limpieza-de-|cortes-|corte-|aplicacion-de-antipulgas/i, name: /baño|bano|est[eé]tica|peluquer|corte|uñas|unas|oído|oido|groom/i, profile: { title: 'Ficha de estética y bienestar', hint: 'Registra el servicio realizado y los hallazgos que requieren seguimiento.', fields: [FIELD('procedimientos', 'Servicio y productos usados', 'Baño, corte, uñas, oídos, productos y estilista'), FIELD('observaciones', 'Piel y conducta', 'Piel, nudos, parásitos, reacción y recomendaciones')] } },
  { code: /profilaxis-dental|microchips/i, name: /profilaxis|microchip/i, profile: { title: 'Procedimiento preventivo', hint: 'Registra el procedimiento, sus materiales y las indicaciones de seguimiento.', fields: [FIELD('procedimientos', 'Procedimiento realizado', 'Técnica, materiales, identificación colocada y responsable'), FIELD('observaciones', 'Indicaciones y control', 'Cuidados posteriores, reacción y fecha de revisión')] } },
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
  readonly imageFile = signal<File | null>(null);
  readonly today = clinicToday();

  readonly filteredClients = computed(() => {
    const query = this.query().trim().toLocaleLowerCase('es');
    return this.clients().filter((client) => !query || `${client.nombre} ${client.correo} ${client.telefono || ''}`.toLocaleLowerCase('es').includes(query));
  });
  readonly clinicalProfile = computed(() => {
    const name = this.selectedService()?.nombre || '';
    const code = this.selectedService()?.codigo || '';
    return PROFILES.find((item) => item.code.test(code) || item.name.test(name))?.profile || DEFAULT_PROFILE;
  });
  readonly formType = computed(() => {
    const service = this.selectedService();
    const value = `${service?.codigo || ''} ${service?.nombre || ''}`;
    if (/ecografia|rayos-x|radiograf|imagen/i.test(value)) return 'imaging';
    if (/laboratorio|hemograma|urian|bioquim|citolog/i.test(value)) return 'laboratory';
    if (/vacun/i.test(value)) return 'vaccination';
    if (/desparasit|antipulga/i.test(value)) return 'deworming';
    if (/cirug|esteriliz|castr|operac/i.test(value)) return 'surgery';
    if (/intern|hospital|hospedaje/i.test(value)) return 'hospitalization';
    if (/bano|baño|estet|peluquer|corte|unas|oido|cepillado/i.test(value)) return 'grooming';
    if (/microchip|profilaxis-dental|profilaxis|microchip/i.test(value)) return 'procedure';
    if (/traumatolog/i.test(value)) return 'trauma';
    if (/tratamiento|farmacia/i.test(value)) return 'treatment';
    if (/domicilio/i.test(value)) return 'home';
    if (/urgencia|emergencia/i.test(value)) return 'emergency';
    return 'clinical';
  });
  readonly isPreventive = computed(() => /vacun|desparasit/i.test(this.selectedService()?.nombre || ''));

  readonly serviceCategories = ['Atención médica', 'Prevención', 'Diagnóstico'];
  readonly clientForm = this.formBuilder.nonNullable.group({ nombre: ['', [Validators.required, Validators.minLength(2)]], correo: ['', [Validators.required, Validators.email]], telefono: ['', [Validators.required, Validators.minLength(9), Validators.maxLength(30)]], direccion: [''] });
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
    this.imageFile.set(null);
    this.attentionForm.patchValue({ motivo_consulta: '', proxima_fecha_control: '' });
  }

  selectImage(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.imageFile.set(input.files?.[0] || null);
  }

  categoryServices(category: string): ClinicService[] {
    const patterns: Record<string, RegExp> = {
      'Atención médica': /consulta|tratamiento|cirug|traumat|intern|hospital|urgencia|domicilio/i,
      Prevención: /vacun|desparasit|profilaxis|dental|microchip/i,
      Diagnóstico: /laboratorio|ecograf|rayos|imagen|radiograf/i,
    };
    return this.services().filter((service) => patterns[category]?.test(`${service.codigo} ${service.nombre}`));
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
    if (this.formType() === 'imaging' && !this.imageFile()) {
      this.errorMessage.set('Adjunta la imagen del estudio antes de guardar la atención.');
      return;
    }
    const raw = this.attentionForm.getRawValue();
    const mainField = this.clinicalProfile().fields[0];
    if (mainField && !String(raw[mainField.key]).trim()) {
      this.errorMessage.set(`Completa el campo "${mainField.label}" para guardar la atención.`);
      return;
    }
    this.errorMessage.set('');
    this.saving.set(true);
    const form = {
      ...raw,
      peso: raw.peso || null,
      temperatura: raw.temperatura || null,
      proxima_fecha_control: raw.proxima_fecha_control || null,
    };
    this.api.startWalkIn({ mascota_id: pet.id, servicio_id: service.id, motivo: form.motivo_consulta || undefined, es_urgente: /urgencia|emergencia/i.test(service.nombre) }).pipe(finalize(() => this.saving.set(false))).subscribe({
      next: (appointment) => this.api.registerAttention(appointment.id, form).subscribe({
        next: (record) => {
          const file = this.imageFile();
          if (this.formType() !== 'imaging' || !file) { this.resetFlow(); return; }
          this.api.uploadClinicalImage(record.id, service.nombre, this.today, file).subscribe({ next: () => this.resetFlow(), error: (error: unknown) => this.showError(error) });
        },
        error: (error: unknown) => this.showError(error),
      }),
      error: (error: unknown) => this.showError(error),
    });
  }

  resetFlow(): void {
    this.step.set(1); this.selectedClient.set(null); this.selectedPet.set(null); this.selectedService.set(null); this.imageFile.set(null); this.query.set(''); this.clientForm.reset(); this.petForm.reset(); this.attentionForm.reset();
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
