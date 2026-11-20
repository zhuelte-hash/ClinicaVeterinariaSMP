import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { AdminApiService, AdminAppointment, CatalogOption } from '../../services/admin-api.service';
import { operationError } from '../../services/operations-api.service';
import { clinicToday } from '../../../veterinarian/veterinarian.models';
import { AppointmentHistoryComponent } from './appointment-history.component';

@Component({
  selector: 'app-appointment-calendar', standalone: true, imports: [FormsModule, AppointmentHistoryComponent],
  template: `<section class="admin-card mb-5 space-y-4 p-4" aria-labelledby="monthly-calendar-title">
    <h2 id="monthly-calendar-title" class="text-xl font-bold">Calendario mensual administrativo</h2>
    <div class="flex flex-wrap items-end gap-3">
      <button type="button" class="admin-secondary" (click)="move(-1)" [disabled]="loading()">Mes anterior</button>
      <label>Mes del calendario<input type="month" class="admin-input" [ngModel]="month()" (ngModelChange)="setMonth($event)"></label>
      <button type="button" class="admin-secondary" (click)="move(1)" [disabled]="loading()">Mes siguiente</button>
      <label>Veterinario del calendario<select class="admin-input" [ngModel]="vet()" (ngModelChange)="vet.set(+$event)"><option [ngValue]="0">Todos los veterinarios</option><option [ngValue]="-1">Sin asignar</option>@for (item of vets(); track item.id) { <option [ngValue]="item.id">{{ item.nombre }}</option> }</select></label>
      <button type="button" class="admin-secondary" (click)="load()" [disabled]="loading()">Actualizar calendario</button>
    </div>
    <p class="text-sm text-slate-500">Todos los estados · Horario de Perú · {{ filtered().length }} citas. El calendario es independiente de los filtros del listado.</p>
    @if (error()) { <p role="alert" class="text-rose-700">{{ error() }}</p> }
    @if (loading()) { <p role="status">Cargando calendario…</p> } @else {
      <div class="overflow-x-auto"><div class="grid min-w-[700px] grid-cols-7 gap-1">
        @for (day of ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']; track day) { <b class="p-2 text-center">{{ day }}</b> }
        @for (cell of cells(); track $index) {
          <div class="min-h-24 rounded-lg border border-slate-200 p-2" [class.bg-slate-50]="!cell.date">
            @if (cell.date) { <b>{{ cell.day }}</b>@for (item of cell.items; track item.id) { <button type="button" class="mt-1 block w-full rounded bg-teal-50 p-1 text-left text-xs text-teal-900" (click)="selected.set(item)">{{ time(item.fecha_hora_programada) }} · {{ item.mascota_nombre }}<span class="block">{{ item.veterinario_nombre || 'Sin asignar' }} · {{ item.estado.replaceAll('_', ' ') }}</span></button> } }
          </div>
        }
      </div></div>
      @if (!filtered().length) { <p>No hay citas en este mes para el veterinario seleccionado.</p> }
    }
  </section>
  @if (selected(); as item) {
    <div class="admin-modal" (click)="selected.set(null)"><section class="admin-modal-panel" role="dialog" aria-modal="true" aria-labelledby="calendar-detail-title" (click)="$event.stopPropagation()">
      <h2 id="calendar-detail-title" class="text-xl font-bold">Detalle de cita #{{ item.id }}</h2>
      <p>{{ item.mascota_nombre }} · {{ item.cliente_nombre }}</p><p>{{ item.servicio_nombre }} · {{ item.veterinario_nombre || 'Sin asignar' }}</p><p>{{ date(item.fecha_hora_programada) }} · {{ item.estado.replaceAll('_', ' ') }}</p><p>{{ item.nota_coordinacion }}</p>
      <app-appointment-history [appointmentId]="item.id" /><button type="button" class="admin-secondary mt-4" (click)="selected.set(null)">Cerrar detalle</button>
    </section></div>
  }`, styleUrl: '../../shared/admin-ui.css',
})
export class AppointmentCalendarComponent {
  private readonly api = inject(AdminApiService); private version = 0;
  readonly month = signal(clinicToday().slice(0, 7)); readonly vet = signal(0); readonly vets = signal<CatalogOption[]>([]);
  readonly items = signal<AdminAppointment[]>([]); readonly loading = signal(false); readonly error = signal(''); readonly selected = signal<AdminAppointment | null>(null);
  readonly filtered = computed(() => this.items().filter(item => !this.vet() || (this.vet() === -1 ? item.veterinario_id == null : item.veterinario_id === this.vet())));
  readonly cells = computed(() => {
    const [year, month] = this.month().split('-').map(Number); const first = new Date(Date.UTC(year, month - 1, 1));
    const offset = (first.getUTCDay() + 6) % 7; const count = new Date(Date.UTC(year, month, 0)).getUTCDate();
    return Array.from({ length: Math.ceil((offset + count) / 7) * 7 }, (_, index) => {
      const day = index - offset + 1; const date = day > 0 && day <= count ? `${this.month()}-${String(day).padStart(2, '0')}` : '';
      return { day, date, items: date ? this.filtered().filter(item => this.localDay(item.fecha_hora_programada) === date).sort((a, b) => Date.parse(a.fecha_hora_programada) - Date.parse(b.fecha_hora_programada) || a.id - b.id) : [] };
    });
  });
  constructor() { this.load(); }
  setMonth(value: string): void { if (/^[1-9]\d{3}-(0[1-9]|1[0-2])$/.test(value)) { this.month.set(value); this.load(); } }
  move(delta: number): void { const [y, m] = this.month().split('-').map(Number); const date = new Date(Date.UTC(y, m - 1 + delta, 1)); this.setMonth(date.toISOString().slice(0, 7)); }
  load(): void {
    const version = ++this.version; const [y, m] = this.month().split('-').map(Number); const last = new Date(Date.UTC(y, m, 0)).getUTCDate();
    this.loading.set(true); this.error.set(''); this.items.set([]); this.selected.set(null);
    forkJoin({ items: this.api.getAppointments(`${this.month()}-01`, undefined, `${this.month()}-${last}`), vets: this.api.getAppointmentVeterinarians() }).subscribe({ next: data => { if (version === this.version) { this.items.set(data.items); this.vets.set(data.vets); this.loading.set(false); } }, error: error => { if (version === this.version) { this.error.set(operationError(error)); this.loading.set(false); } } });
  }
  private localDay(value: string): string { return new Intl.DateTimeFormat('sv-SE', { timeZone: 'America/Lima', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(value)); }
  time(value: string): string { return new Intl.DateTimeFormat('es-PE', { timeZone: 'America/Lima', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date(value)); }
  date(value: string): string { return new Intl.DateTimeFormat('es-PE', { timeZone: 'America/Lima', dateStyle: 'short', timeStyle: 'short' }).format(new Date(value)); }
}
