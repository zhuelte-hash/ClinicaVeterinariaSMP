import { ChangeDetectionStrategy, Component, computed, HostListener, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink, ActivatedRoute } from '@angular/router';
import { forkJoin } from 'rxjs';
import { environment } from '../../../environments/environment';
import { VeterinarianApiService } from './veterinarian-api.service';
import { ClinicalRecord, VeterinarianAppointment } from './veterinarian.models';

type HistoryTab = 'resumen' | 'historia' | 'preventivos' | 'examenes' | 'laboratorio';

@Component({
  selector: 'app-veterinarian-pet-history',
  standalone: true,
  imports: [RouterLink, FormsModule],
  templateUrl: './veterinarian-pet-history.component.html',
  styles: [`
    .field-label { font-size: .7rem; font-weight: 800; text-transform: uppercase; letter-spacing: .08em; color: #94a3b8; }
    .field-value { margin-top: .25rem; font-size: .875rem; line-height: 1.5; color: #334155; }
    :host select option:nth-child(3) { display: none; }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class VeterinarianPetHistoryComponent {
  private readonly api = inject(VeterinarianApiService);
  private readonly route = inject(ActivatedRoute);
  readonly tab = signal<HistoryTab>('resumen');
  readonly appointment = signal<VeterinarianAppointment | null>(null);
  readonly history = signal<ClinicalRecord[]>([]);
  readonly loading = signal(true);
  readonly error = signal('');
  readonly selectedImage = signal<{ url: string; type: string; date: string } | null>(null);
  studyType = 'Radiografía';
  studyDate = new Date().toISOString().slice(0, 10);
  labResultText = '';
  readonly pet = computed(() => this.appointment()?.mascota);
  readonly latest = computed(() => this.history()[0] || null);
  readonly vaccines = computed(() => this.history().filter((item) => !!item.vacunas));
  readonly deworming = computed(() => this.history().filter((item) => !!item.desparasitaciones));
  readonly exams = computed(() => this.history().filter((item) => !!item.examenes_resultados));
  readonly images = computed(() => this.history().flatMap((item) => item.archivos.map((archivo) => ({ ...archivo, recordId: item.id }))));
  readonly age = computed(() => {
    const birth = this.pet()?.fecha_nacimiento;
    if (!birth) return 'Edad no registrada';
    const years = Math.floor((Date.now() - new Date(`${birth}T00:00:00`).getTime()) / 31_557_600_000);
    return years > 0 ? `${years} año(s)` : 'Menor de un año';
  });

  constructor() {
    const petId = Number(this.route.snapshot.paramMap.get('id'));
    forkJoin({ active: this.api.getRequests(), attended: this.api.getRequests(undefined, 'atendida'), history: this.api.getPetHistory(petId) }).subscribe({
      next: ({ active, attended, history }) => {
        const appointments = [...active, ...attended];
        this.appointment.set(appointments.find((item) => item.mascota.id === petId) || null);
        this.history.set(history);
        this.loading.set(false);
      },
      error: () => { this.error.set('No se pudo cargar la ficha clínica.'); this.loading.set(false); },
    });
  }

  setTab(tab: HistoryTab): void { this.tab.set(tab); }
  uploadImage(event: Event, record: ClinicalRecord): void {
    if (this.studyType === 'Laboratorio') {
      this.error.set('Para laboratorio registra el examen y sus resultados, no subas una imagen.');
      return;
    }
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    this.api.uploadClinicalImage(record.id, this.studyType, this.studyDate, file).subscribe({
      next: (archivo) => this.history.update((items) => items.map((item) => item.id === record.id ? { ...item, archivos: [...item.archivos, archivo] } : item)),
      error: () => this.error.set('No se pudo cargar la imagen.'),
    });
    input.value = '';
  }
  saveLabResult(record: ClinicalRecord | null): void {
    if (!record?.cita_id || !this.labResultText.trim()) return;
    this.api.registerAttention(record.cita_id, { examenes_resultados: `${this.studyDate} · ${this.labResultText.trim()}` }).subscribe({
      next: (updated) => { this.history.update((items) => items.map((item) => item.id === updated.id ? updated : item)); this.labResultText = ''; this.error.set(''); },
      error: () => this.error.set('No se pudo guardar el resultado de laboratorio.'),
    });
  }
  imageUrl(path: string): string { return `${environment.apiUrl}${path}`; }
  openImage(image: { archivo_ruta: string; tipo_examen: string; fecha_estudio: string }): void {
    if (!image.archivo_ruta.endsWith('.pdf')) this.selectedImage.set({ url: this.imageUrl(image.archivo_ruta), type: image.tipo_examen, date: image.fecha_estudio });
  }
  closeImage(): void { this.selectedImage.set(null); }
  @HostListener('document:click', ['$event'])
  handleImageClick(event: Event): void {
    const target = event.target as HTMLElement;
    if (target.tagName !== 'IMG' || !target.closest('figure')) return;
    const image = target as HTMLImageElement;
    this.selectedImage.set({ url: image.src, type: image.alt, date: '' });
  }
  formatDate(value: string): string { return new Intl.DateTimeFormat('es-PE', { dateStyle: 'medium', timeZone: 'America/Lima' }).format(new Date(value)); }
}
