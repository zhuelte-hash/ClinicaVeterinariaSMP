import { ChangeDetectionStrategy, Component, computed, HostListener, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { RouterLink, ActivatedRoute } from '@angular/router';
import { distinctUntilChanged, finalize, forkJoin, map } from 'rxjs';
import { environment } from '../../../environments/environment';
import { VeterinarianApiService } from './veterinarian-api.service';
import { clinicToday, ClinicalRecord, VeterinarianPatient } from './veterinarian.models';
import { NoticeService } from '../../core/services/notice.service';
import { clinicalDate, VeterinarianIconComponent, VeterinarianPaginationComponent, VeterinarianStatusComponent, VeterinarianTableState } from './veterinarian-table';
import { PetEditorComponent } from '../appointments/pet-editor.component';
import { Pet } from '../appointments/appointments.models';
import { WeightEvolutionComponent } from './weight-evolution.component';
import { PatientAlertsComponent } from './patient-alerts.component';

type HistoryTab = 'resumen' | 'historia' | 'preventivos' | 'examenes' | 'laboratorio';

@Component({
  selector: 'app-veterinarian-pet-history',
  standalone: true,
  imports: [RouterLink, FormsModule, VeterinarianIconComponent, VeterinarianPaginationComponent, VeterinarianStatusComponent, PetEditorComponent, WeightEvolutionComponent, PatientAlertsComponent],
  templateUrl: './veterinarian-pet-history.component.html',
  styles: [`
    .field-label { font-size: .8125rem; font-weight: 600; color: var(--vet-muted); }
    .field-value { margin-top: .3rem; font-size: .9375rem; line-height: 1.6; color: var(--vet-ink); }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class VeterinarianPetHistoryComponent {
  private readonly api = inject(VeterinarianApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly notice = inject(NoticeService);
  private loadVersion = 0;
  readonly tab = signal<HistoryTab>('resumen');
  readonly patient = signal<VeterinarianPatient | null>(null);
  readonly history = signal<ClinicalRecord[]>([]);
  readonly loading = signal(true);
  readonly error = signal('');
  readonly expandedRecordId = signal<number | null>(null);
  readonly uploading = signal(false);
  readonly labSaving = signal(false);
  readonly table = new VeterinarianTableState(this.history);
  readonly dateLabel = clinicalDate;
  uploadRecordId = 0;
  labRecordId = 0;
  readonly selectedImage = signal<{ url: string; type: string; date: string } | null>(null);
  studyType = 'Radiografía';
   studyDate = clinicToday();
  labResultText = '';
  readonly pet = computed(() => this.patient());
  readonly latest = computed<ClinicalRecord | null>(() => this.history()[0] || null);
  readonly vaccines = computed(() => this.history().filter((item) => !!item.vacunas));
  readonly deworming = computed(() => this.history().filter((item) => !!item.desparasitaciones));
  readonly exams = computed(() => this.history().filter((item) => !!item.examenes_resultados));
  readonly images = computed(() => this.history().flatMap((item) => item.archivos.map((archivo) => ({ ...archivo, recordId: item.id }))));
  readonly ultrasoundImages = computed(() => this.images().filter((image) => /ecograf/i.test(image.tipo_examen)));
  readonly xrayImages = computed(() => this.images().filter((image) => /radiograf|rayos/i.test(image.tipo_examen)));
  readonly medicalRecords = computed(() => this.history().filter(record => record.tipo === 'medica'));
  readonly preventiveRows = computed(() => this.history().flatMap(record => [
    ...record.aplicaciones_preventivas.map(item => ({ ...item, key: `application-${item.id}`, source: record.servicio_nombre })),
    ...([{ field: record.vacunas, type: 'vacuna' }, { field: record.desparasitaciones, type: 'desparasitacion' }] as const)
      .filter(item => !!item.field).map(item => ({ key: `legacy-${record.id}-${item.type}`, tipo: item.type, producto: item.field, lote: null, fecha_vencimiento: null, fecha_aplicacion: record.fecha_inicio, proxima_fecha: record.proxima_fecha_control, observaciones: 'Anotación de la ficha clínica', source: record.servicio_nombre })),
  ]));
  readonly labRows = computed(() => this.history().flatMap(record => [
    ...record.ordenes_examen.filter(exam => !/radiograf|rayos|ecograf|imagen/i.test(exam.tipo)).map(exam => ({ key: `exam-${exam.id}`, fecha: exam.fecha_solicitud, tipo: exam.tipo, estado: exam.estado.replaceAll('_', ' '), resultado: exam.resultado, interpretacion: exam.interpretacion })),
    ...(record.examenes_resultados && !/radiograf|rayos|ecograf|imagen/i.test(record.servicio_nombre)
      ? [{ key: `result-${record.id}`, fecha: record.fecha_inicio, tipo: record.servicio_nombre, estado: 'Resultado registrado', resultado: record.examenes_resultados, interpretacion: null }] : []),
  ]));
  readonly detailFields = [
    { key: 'motivo_consulta', label: 'Motivo de consulta' }, { key: 'anamnesis', label: 'Anamnesis' },
    { key: 'observaciones', label: 'Exploración y observaciones' }, { key: 'diagnostico', label: 'Diagnóstico' },
    { key: 'tratamiento', label: 'Tratamiento e indicaciones' }, { key: 'historial_alergias', label: 'Alergias' },
    { key: 'medicamentos', label: 'Medicamentos' }, { key: 'procedimientos', label: 'Procedimientos' },
    { key: 'vacunas', label: 'Vacunas' }, { key: 'desparasitaciones', label: 'Desparasitación' },
    { key: 'examenes_resultados', label: 'Resultados registrados' },
  ] as const;
  readonly age = computed(() => {
    const birth = this.pet()?.fecha_nacimiento;
    if (!birth) return 'Edad no registrada';
    const years = Math.floor((Date.now() - new Date(`${birth}T00:00:00`).getTime()) / 31_557_600_000);
    return years > 0 ? `${years} año(s)` : 'Menor de un año';
  });

  constructor() {
    this.route.queryParamMap.pipe(takeUntilDestroyed()).subscribe(params => {
      const tab = params.get('tab') as HistoryTab | null;
      if (tab && ['resumen', 'historia', 'preventivos', 'examenes', 'laboratorio'].includes(tab)) this.tab.set(tab);
    });
    this.route.paramMap.pipe(map(params => params.get('id')), distinctUntilChanged(), takeUntilDestroyed()).subscribe(() => this.load());
  }

  load(): void {
    const version = ++this.loadVersion;
    const petId = Number(this.route.snapshot.paramMap.get('id'));
    this.loading.set(true);
    this.expandedRecordId.set(null);
    this.table.reset();
    forkJoin({ patient: this.api.getPatient(petId), history: this.api.getPetHistory(petId) }).pipe(finalize(() => { if (version === this.loadVersion) this.loading.set(false); })).subscribe({
      next: ({ patient, history }) => {
        if (version !== this.loadVersion) return;
        this.patient.set(patient);
        this.history.set(history);
        this.error.set('');
        this.uploadRecordId = this.medicalRecords()[0]?.id || 0;
        this.labRecordId = this.uploadRecordId;
      },
      error: (error: unknown) => { if (version === this.loadVersion) { this.patient.set(null); this.error.set(error instanceof HttpErrorResponse && typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudo cargar la ficha clínica.'); } },
    });
  }

  setTab(tab: HistoryTab): void { this.tab.set(tab); }
  updatePatient(pet: Pet): void { this.patient.update(current => current ? { ...current, ...pet } : current); }
  uploadImage(event: Event, record: ClinicalRecord, type = this.studyType): void {
    if (this.uploading()) return;
    if (type === 'Laboratorio') {
      this.error.set('Para laboratorio registra el examen y sus resultados, no subas una imagen.');
      return;
    }
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    this.uploading.set(true);
    this.api.uploadClinicalImage(record.id, type, this.studyDate, file).pipe(finalize(() => this.uploading.set(false))).subscribe({
      next: (archivo) => { this.history.update((items) => items.map((item) => item.id === record.id ? { ...item, archivos: [...item.archivos, archivo] } : item)); this.error.set(''); this.notice.show('Archivo clínico guardado'); },
      error: () => this.error.set('No se pudo cargar la imagen.'),
    });
    input.value = '';
  }
  saveLabResult(record: ClinicalRecord | null): void {
    if (!record || !this.labResultText.trim() || this.labSaving()) return;
    this.labSaving.set(true);
    this.api.updateClinicalResults(record.id, `${this.studyDate} · ${this.labResultText.trim()}`).pipe(finalize(() => this.labSaving.set(false))).subscribe({
      next: (updated) => { this.history.update((items) => items.map((item) => item.id === updated.id ? updated : item)); this.labResultText = ''; this.error.set(''); this.notice.show('Resultado de laboratorio guardado'); },
      error: () => this.error.set('No se pudo guardar el resultado de laboratorio.'),
    });
  }
  imageUrl(path: string): string { return `${environment.apiUrl}${path}`; }
  openImage(image: { archivo_ruta: string; tipo_examen: string; fecha_estudio: string }): void {
    if (!this.isPdf(image.archivo_ruta)) this.selectedImage.set({ url: this.imageUrl(image.archivo_ruta), type: image.tipo_examen, date: image.fecha_estudio });
  }
  closeImage(): void { this.selectedImage.set(null); }
  @HostListener('document:keydown.escape') onEscape(): void { this.closeImage(); }
  isPdf(path: string): boolean { return /\.pdf(?:$|\?)/i.test(path); }
  selectedMedicalRecord(id: number): ClinicalRecord | null { return this.medicalRecords().find(record => record.id === Number(id)) || null; }
  toggleRecord(record: ClinicalRecord): void { this.expandedRecordId.update(id => id === record.id ? null : record.id); }
  formatDate(value: string): string { return new Intl.DateTimeFormat('es-PE', { dateStyle: 'medium', timeZone: 'America/Lima' }).format(new Date(value)); }
}
