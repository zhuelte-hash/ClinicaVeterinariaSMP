import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink, ActivatedRoute } from '@angular/router';
import { forkJoin } from 'rxjs';
import { VeterinarianApiService } from './veterinarian-api.service';
import { ClinicalRecord, VeterinarianAppointment } from './veterinarian.models';

type HistoryTab = 'resumen' | 'historia' | 'preventivos' | 'examenes';

@Component({
  selector: 'app-veterinarian-pet-history',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './veterinarian-pet-history.component.html',
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
  readonly pet = computed(() => this.appointment()?.mascota);
  readonly latest = computed(() => this.history()[0] || null);
  readonly vaccines = computed(() => this.history().filter((item) => !!item.vacunas));
  readonly deworming = computed(() => this.history().filter((item) => !!item.desparasitaciones));
  readonly exams = computed(() => this.history().filter((item) => !!item.examenes_resultados));
  readonly age = computed(() => {
    const birth = this.pet()?.fecha_nacimiento;
    if (!birth) return 'Edad no registrada';
    const years = Math.floor((Date.now() - new Date(`${birth}T00:00:00`).getTime()) / 31_557_600_000);
    return years > 0 ? `${years} año(s)` : 'Menor de un año';
  });

  constructor() {
    const petId = Number(this.route.snapshot.paramMap.get('id'));
    forkJoin({ requests: this.api.getRequests(), history: this.api.getPetHistory(petId) }).subscribe({
      next: ({ requests, history }) => { this.appointment.set(requests.find((item) => item.mascota.id === petId) || null); this.history.set(history); this.loading.set(false); },
      error: () => { this.error.set('No se pudo cargar la ficha clínica.'); this.loading.set(false); },
    });
  }

  setTab(tab: HistoryTab): void { this.tab.set(tab); }
  formatDate(value: string): string { return new Intl.DateTimeFormat('es-PE', { dateStyle: 'medium', timeZone: 'America/Lima' }).format(new Date(value)); }
}
