import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { finalize, forkJoin } from 'rxjs';
import { VeterinarianApiService } from './veterinarian-api.service';
import { AppointmentSummary, VeterinarianAppointment } from './veterinarian.models';
import { clinicalDate, VeterinarianIconComponent, VeterinarianPaginationComponent, VeterinarianStatusComponent, VeterinarianTableState } from './veterinarian-table';

@Component({
  selector: 'app-veterinarian-home', standalone: true,
  imports: [RouterLink, VeterinarianIconComponent, VeterinarianPaginationComponent, VeterinarianStatusComponent],
  templateUrl: './veterinarian-home.component.html', changeDetection: ChangeDetectionStrategy.OnPush,
})
export class VeterinarianHomeComponent {
  private readonly api = inject(VeterinarianApiService);
  readonly error = signal('');
  readonly loading = signal(true);
  readonly summary = signal<AppointmentSummary>({ pendientes: 0, confirmadas: 0, atendidas: 0, proximas: 0 });
  readonly appointments = signal<VeterinarianAppointment[]>([]);
  readonly activeAppointments = computed(() => this.appointments().filter(item => !['atendida', 'cancelada', 'no_asistio'].includes(item.estado)).sort((a, b) => Date.parse(a.fecha_hora_programada) - Date.parse(b.fecha_hora_programada)));
  readonly table = new VeterinarianTableState(this.activeAppointments);
  readonly statusRows = computed(() => {
    const counts = new Map<string, number>();
    this.appointments().forEach(item => counts.set(item.estado, (counts.get(item.estado) || 0) + 1));
    return [...counts].map(([status, total]) => ({ status, total })).sort((a, b) => b.total - a.total);
  });
  readonly serviceRows = computed(() => {
    const counts = new Map<string, number>();
    this.appointments().forEach(item => counts.set(item.servicio.nombre, (counts.get(item.servicio.nombre) || 0) + 1));
    return [...counts].map(([name, total]) => ({ name, total })).sort((a, b) => b.total - a.total || a.name.localeCompare(b.name, 'es'));
  });
  readonly formatDate = clinicalDate;

  constructor() { this.load(); }

  load(): void {
    this.loading.set(true);
    forkJoin({ summary: this.api.getSummary(), appointments: this.api.getRequests(undefined, undefined, undefined, true) })
      .pipe(finalize(() => this.loading.set(false))).subscribe({
        next: ({ summary, appointments }) => { this.summary.set(summary); this.appointments.set(appointments); this.error.set(''); },
        error: () => this.error.set('No se pudo cargar el resumen operativo. Actualiza para volver a consultar los datos.'),
      });
  }
}
