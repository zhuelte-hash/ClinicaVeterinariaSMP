import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { AdminApiService, CatalogOption } from '../../services/admin-api.service';
import { OccupancyReport, OperationsApiService, operationError } from '../../services/operations-api.service';
import { clinicToday } from '../../../veterinarian/veterinarian.models';

@Component({
  standalone: true, imports: [FormsModule], styleUrl: '../../shared/admin-ui.css',
  template: `<h1 class="mb-4 text-2xl font-bold">Ocupación de agenda veterinaria</h1>
    <form class="admin-card mb-4 flex flex-wrap items-end gap-3 p-4" (ngSubmit)="load()">
      <label>Desde<input class="admin-input" type="date" name="desde" required [(ngModel)]="from"></label>
      <label>Hasta<input class="admin-input" type="date" name="hasta" required [(ngModel)]="to"></label>
      <label>Veterinario<select class="admin-input" name="veterinario" [(ngModel)]="vet"><option value="">Todos</option>@for (item of vets(); track item.id) { <option [value]="item.id">{{ item.nombre }}</option> }</select></label>
      <button class="admin-primary" [disabled]="loading()">Consultar ocupación</button>
    </form>
    @if (error()) { <p role="alert" class="text-rose-700">{{ error() }}</p> }
    @if (loading()) { <p role="status">Calculando ocupación…</p> }
    @if (report(); as data) {
      <section class="admin-card mb-4 space-y-2 p-4"><h2 class="text-xl font-bold">Ocupación: {{ data.porcentaje }} %</h2>
        <p>Capacidad disponible: {{ data.capacidad_minutos }} min · Tiempo ocupado: {{ data.ocupados_minutos }} min</p><p>{{ data.criterio }}</p>
        @if (!data.capacidad_minutos) { <p>No hay capacidad disponible en el período seleccionado.</p> }
      </section>
      <div class="admin-card overflow-x-auto"><table class="admin-table"><thead><tr><th>Fecha</th><th>Veterinario</th><th>Capacidad (min)</th><th>Ocupados (min)</th><th>Ocupación</th></tr></thead><tbody>
      @for (row of data.detalle; track row.fecha + ':' + row.veterinario_id) { <tr><td>{{ row.fecha }}</td><td>{{ row.veterinario }}</td><td>{{ row.capacidad_minutos }}</td><td>{{ row.ocupados_minutos }}</td><td>{{ row.porcentaje }} %</td></tr> }
      @empty { <tr><td colspan="5">Sin horarios registrados para la selección.</td></tr> }
      </tbody></table></div>
    }`,
})
export class OccupancyComponent {
  private readonly api = inject(OperationsApiService); private readonly admin = inject(AdminApiService); private version = 0;
  readonly report = signal<OccupancyReport | null>(null); readonly vets = signal<CatalogOption[]>([]); readonly error = signal(''); readonly loading = signal(false);
  from = clinicToday(); to = clinicToday(); vet = '';
  constructor() { this.load(); }
  load(): void {
    const version = ++this.version; this.error.set(''); this.report.set(null);
    if (!this.from || !this.to || this.from > this.to) { this.error.set('Selecciona un rango de fechas válido.'); this.loading.set(false); return; }
    this.loading.set(true);
    forkJoin({ report: this.api.occupancy(this.from, this.to, this.vet), vets: this.admin.getAppointmentVeterinarians() }).subscribe({ next: data => { if (version !== this.version) return; this.report.set(data.report); this.vets.set(data.vets); this.loading.set(false); }, error: e => { if (version !== this.version) return; this.error.set(operationError(e)); this.loading.set(false); } });
  }
}
