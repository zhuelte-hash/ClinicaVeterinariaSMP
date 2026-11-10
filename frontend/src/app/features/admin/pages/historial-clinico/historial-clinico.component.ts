import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { finalize } from 'rxjs';
import { environment } from '../../../../../environments/environment';
import { clinicalDate, clinicalSearch } from '../../../veterinarian/veterinarian-table';
import { AdminApiService, AdminClinicalRecord } from '../../services/admin-api.service';
import { PageHeaderComponent } from '../../shared/page-header.component';

@Component({ selector: 'app-admin-historial-clinico', standalone: true, imports: [PageHeaderComponent], templateUrl: './historial-clinico.component.html', styleUrl: '../../shared/admin-ui.css' })
export class HistorialClinicoComponent {
  private readonly api = inject(AdminApiService); readonly query = signal(''); readonly expanded = signal<number | null>(null); readonly records = signal<AdminClinicalRecord[]>([]); readonly loading = signal(true); readonly error = signal('');
  readonly dateLabel = clinicalDate;
  readonly fields = [
    { key: 'motivo_consulta', label: 'Motivo de consulta' }, { key: 'anamnesis', label: 'Anamnesis' },
    { key: 'diagnostico', label: 'Diagnóstico' }, { key: 'tratamiento', label: 'Tratamiento' },
    { key: 'observaciones', label: 'Observaciones' }, { key: 'historial_alergias', label: 'Alergias' },
    { key: 'vacunas', label: 'Vacunas' }, { key: 'desparasitaciones', label: 'Desparasitación' },
    { key: 'medicamentos', label: 'Medicamentos' }, { key: 'procedimientos', label: 'Procedimientos' },
    { key: 'examenes_resultados', label: 'Resultados' },
  ] as const;
  readonly filtered = computed(() => { const q = clinicalSearch(this.query()); return this.records().filter(record => !q || clinicalSearch(`${record.mascota_id} ${record.mascota.nombre} ${record.mascota.especie} ${record.cliente_nombre} ${record.veterinario_nombre} ${record.servicio_nombre} ${record.diagnostico ?? ''}`).includes(q)); });
  constructor() { this.load(); }
  load(): void {
    this.loading.set(true);
    this.api.getClinicalRecords().pipe(finalize(() => this.loading.set(false))).subscribe({
      next: items => { this.records.set(items); this.error.set(''); },
      error: (error: unknown) => this.error.set(error instanceof HttpErrorResponse && typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudo cargar el historial clínico.'),
    });
  }
  fileUrl(path: string): string { return /^https?:\/\//i.test(path) ? path : `${environment.apiUrl}${path}`; }
}
