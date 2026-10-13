import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { VeterinarianApiService } from './veterinarian-api.service';
import { AppointmentSummary, VeterinarianAppointment } from './veterinarian.models';

@Component({
  selector: 'app-veterinarian-home',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './veterinarian-home.component.html',
  styles: [`
    .home-welcome { position: relative; background: #fff; border: 1px solid #dfe7ed; box-shadow: 0 2px 8px rgb(35 55 72 / .04); color: #233748; }
    .home-glow { position: absolute; right: -6rem; bottom: -9rem; width: 24rem; height: 24rem; border: 1px solid rgb(140 233 220 / .2); border-radius: 999px; box-shadow: 0 0 0 2.5rem rgb(140 233 220 / .04), 0 0 0 5rem rgb(140 233 220 / .025); }
    .stat-card { transition: transform .18s ease, box-shadow .18s ease; }
    .stat-card:hover { transform: translateY(-2px); box-shadow: 0 12px 28px rgb(16 43 53 / .08); }
    .home-welcome .text-white { color: #233748; }
    .home-welcome .text-slate-200 { color: #637888; }
    .home-welcome > div:first-child > p { color: #087f83; }
    .home-welcome a:last-child { border-color: #dfe7ed; color: #087f83; background: #fff; }
    .home-welcome .home-glow { display: none; }
  `],
})
export class VeterinarianHomeComponent {
  private readonly api = inject(VeterinarianApiService);
  readonly summary = signal<AppointmentSummary>({ pendientes: 0, confirmadas: 0, atendidas: 0, proximas: 0 });
  readonly appointments = signal<VeterinarianAppointment[]>([]);
  readonly statusChart = computed(() => [
    { label: 'Confirmadas', value: this.summary().confirmadas, color: '#35c9b5' },
    { label: 'Pendientes', value: this.summary().pendientes, color: '#fbbf24' },
    { label: 'Atendidas', value: this.summary().atendidas, color: '#60a5fa' },
  ]);
  readonly serviceChart = computed(() => {
    const counts = new Map<string, number>();
    this.appointments().forEach((appointment) => counts.set(appointment.servicio.nombre, (counts.get(appointment.servicio.nombre) || 0) + 1));
    return [...counts.entries()].map(([label, value]) => ({ label, value })).slice(0, 4);
  });
  chartWidth(value: number, values: number[]): number { return Math.max(8, (value / Math.max(...values, 1)) * 100); }

  constructor() {
    this.api.getSummary().subscribe({ next: (summary) => this.summary.set(summary) });
    this.api.getRequests().subscribe({ next: (appointments) => this.appointments.set(appointments.slice(0, 4)) });
  }

  formatDate(value: string): string { return new Intl.DateTimeFormat('es-PE', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'America/Lima' }).format(new Date(value)); }
  statusLabel(status: string): string { return ({ confirmada: 'Confirmada', reprogramada: 'Reprogramada', pendiente_contacto: 'Pendiente', contactando_cliente: 'Contactando' } as Record<string, string>)[status] || status; }
}
