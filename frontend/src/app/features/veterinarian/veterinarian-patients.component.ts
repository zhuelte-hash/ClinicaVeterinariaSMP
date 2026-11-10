import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { VeterinarianApiService } from './veterinarian-api.service';
import { VeterinarianPatient } from './veterinarian.models';
import { clinicalDate, clinicalSearch, VeterinarianIconComponent, VeterinarianPaginationComponent, VeterinarianTableState } from './veterinarian-table';

@Component({
  selector: 'app-veterinarian-patients', standalone: true,
  imports: [RouterLink, VeterinarianIconComponent, VeterinarianPaginationComponent],
  templateUrl: './veterinarian-patients.component.html', changeDetection: ChangeDetectionStrategy.OnPush,
})
export class VeterinarianPatientsComponent {
  private readonly api = inject(VeterinarianApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  readonly patients = signal<VeterinarianPatient[]>([]);
  readonly loading = signal(true);
  readonly error = signal('');
  readonly query = signal('');
  readonly species = signal('');
  readonly historyFilter = signal('');
  readonly sort = signal('nombre');
  readonly ownerId = signal(Number(this.route.snapshot.queryParamMap.get('cliente')) || null);
  readonly speciesOptions = computed(() => [...new Set(this.patients().map(patient => patient.especie))].sort((a, b) => a.localeCompare(b, 'es')));
  readonly withRecords = computed(() => this.patients().filter(patient => patient.atenciones > 0).length);
  readonly withoutAppointments = computed(() => this.patients().filter(patient => patient.citas === 0).length);
  readonly filteredPatients = computed(() => {
    const query = clinicalSearch(this.query());
    return this.patients().filter(patient =>
      (!this.ownerId() || patient.cliente_id === this.ownerId()) &&
      (!this.species() || patient.especie === this.species()) &&
      (!this.historyFilter() || (this.historyFilter() === 'con' ? patient.atenciones > 0 : patient.atenciones === 0)) &&
      (!query || clinicalSearch(`${patient.id} ${patient.nombre} ${patient.especie} ${patient.raza || ''} ${patient.cliente_nombre} ${patient.cliente_correo} ${patient.telefono_contacto || ''}`).includes(query))
    ).sort((a, b) => this.sort() === 'recientes'
      ? (b.ultima_atencion ? Date.parse(b.ultima_atencion) : 0) - (a.ultima_atencion ? Date.parse(a.ultima_atencion) : 0) || a.nombre.localeCompare(b.nombre, 'es')
      : (this.sort() === 'propietario' ? a.cliente_nombre.localeCompare(b.cliente_nombre, 'es') : a.nombre.localeCompare(b.nombre, 'es')) || a.id - b.id);
  });
  readonly table = new VeterinarianTableState(this.filteredPatients);
  readonly formatDate = clinicalDate;

  constructor() {
    this.route.queryParamMap.pipe(takeUntilDestroyed()).subscribe(params => { this.ownerId.set(Number(params.get('cliente')) || null); this.table.reset(); });
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api.getPatients().pipe(finalize(() => this.loading.set(false))).subscribe({
      next: patients => { this.patients.set(patients); this.error.set(''); },
      error: (error: unknown) => this.error.set(error instanceof HttpErrorResponse && typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudieron cargar los pacientes. Intenta actualizar el listado.'),
    });
  }

  setQuery(value: string): void { this.query.set(value); this.table.reset(); }
  setSpecies(value: string): void { this.species.set(value); this.table.reset(); }
  setHistory(value: string): void { this.historyFilter.set(value); this.table.reset(); }
  setSort(value: string): void { this.sort.set(value); this.table.reset(); }
  clearFilters(): void {
    this.query.set(''); this.species.set(''); this.historyFilter.set(''); this.ownerId.set(null); this.table.reset();
    if (this.route.snapshot.queryParamMap.has('cliente')) void this.router.navigate([], { relativeTo: this.route, queryParams: { cliente: null }, queryParamsHandling: 'merge', replaceUrl: true });
  }
}
