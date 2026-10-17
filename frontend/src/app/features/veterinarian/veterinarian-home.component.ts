import { Component, computed, inject, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { VeterinarianApiService } from './veterinarian-api.service';
import { AppointmentSummary, VeterinarianAppointment } from './veterinarian.models';

@Component({
  selector: 'app-veterinarian-home',
  standalone: true,
  imports: [RouterLink, DecimalPipe],
  templateUrl: './veterinarian-home.component.html',
  styles: [`
    .dashboard-hero { background: linear-gradient(120deg, #152b3b 0%, #184d58 58%, #197f79 100%); }
    .dashboard-hero::after { content: ''; position: absolute; inset: 0; background: linear-gradient(90deg, rgb(13 31 45 / 20%), transparent 65%); pointer-events: none; }
    .eyebrow-chip { display: inline-flex; border: 1px solid rgb(151 245 230 / 28%); border-radius: 999px; background: rgb(255 255 255 / 10%); padding: .42rem .75rem; color: #a5f3e5; font-size: .68rem; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; }
    .hero-action { display: inline-flex; align-items: center; gap: .7rem; border-radius: .8rem; background: #8de8d5; padding: .72rem 1rem; color: #12313c; font-size: .8rem; font-weight: 800; transition: transform .2s, background .2s; }
    .hero-action:hover { transform: translateY(-2px); background: #c4fff3; }
    .hero-action.secondary { border: 1px solid rgb(255 255 255 / 18%); background: rgb(255 255 255 / 9%); color: white; }
    .hero-action.secondary:hover { background: rgb(255 255 255 / 18%); }
    .hero-orb { position: absolute; border: 1px solid rgb(167 255 237 / 18%); border-radius: 999px; }
    .hero-orb-one { right: 5%; top: -7rem; height: 22rem; width: 22rem; box-shadow: 0 0 0 2rem rgb(155 248 228 / 4%), 0 0 0 5rem rgb(155 248 228 / 3%); }
    .hero-orb-two { right: 17%; bottom: -8rem; height: 14rem; width: 14rem; border-color: rgb(255 255 255 / 12%); }
    .hero-pattern { position: absolute; right: 3rem; top: 2rem; height: 9rem; width: 9rem; opacity: .25; background-image: radial-gradient(#b8fff1 1px, transparent 1px); background-size: 12px 12px; transform: rotate(15deg); }
    .modern-stat, .modern-card { border: 1px solid #e1ebed; border-radius: 1.15rem; background: rgb(255 255 255 / 94%); box-shadow: 0 10px 35px rgb(23 43 58 / 5%); }
    .modern-stat { position: relative; overflow: hidden; padding: 1.15rem; transition: transform .2s, box-shadow .2s; }
    .modern-stat:hover { transform: translateY(-3px); box-shadow: 0 18px 40px rgb(23 43 58 / 10%); }
    .stat-icon { display: grid; height: 2.5rem; width: 2.5rem; place-items: center; border-radius: .8rem; background: #e8faf5; color: #167a72; font-size: 1.1rem; }
    .amber .stat-icon { background: #fff5dc; color: #b7791f; }
    .blue .stat-icon { background: #eaf2ff; color: #3478c7; }
    .stat-arrow { color: #b5c4c9; font-size: 1.1rem; }
    .stat-line { position: absolute; right: 1.15rem; bottom: 1.05rem; left: 1.15rem; height: .22rem; overflow: hidden; border-radius: 99px; background: #eef4f4; }
    .stat-line span { display: block; height: 100%; width: 55%; border-radius: inherit; background: #63cfbd; }
    .amber .stat-line span { width: 38%; background: #f3c45f; }
    .blue .stat-line span { width: 72%; background: #76aee8; }
    .section-kicker { color: #188c83; font-size: .65rem; font-weight: 900; letter-spacing: .16em; text-transform: uppercase; }
    .section-kicker.light { color: #9dece0; }
    .live-dot, .chart-badge { border-radius: 999px; background: #e9faf5; padding: .35rem .6rem; color: #198578; font-size: .65rem; font-weight: 800; }
    .live-dot::before { content: ''; display: inline-block; height: .4rem; width: .4rem; margin-right: .35rem; border-radius: 50%; background: #35c9a7; }
    .chart-badge { background: #f0f4ff; color: #6179b8; }
    .donut-wrap { display: grid; height: 9rem; width: 9rem; place-items: center; border-radius: 50%; }
    .donut-hole { display: grid; height: 6.2rem; width: 6.2rem; place-content: center; border-radius: 50%; background: white; text-align: center; box-shadow: inset 0 0 0 1px #edf2f2; }
    .donut-hole strong { color: #172b3a; font-size: 1.65rem; line-height: 1; }
    .donut-hole span { margin-top: .3rem; color: #91a2a8; font-size: .65rem; font-weight: 700; text-transform: uppercase; }
    .legend-dot { height: .65rem; width: .65rem; flex: 0 0 auto; border-radius: 50%; }
    .chart-track { height: .55rem; overflow: hidden; border-radius: 999px; background: #edf3f3; }
    .chart-bar { display: block; height: 100%; border-radius: inherit; background: #54c8b5; transition: width .5s ease; }
    .bar-1 { background: #77a9e4; }.bar-2 { background: #f2c45f; }.bar-3 { background: #ae91d8; }
    .empty-chart { display: grid; place-items: center; min-height: 8rem; color: #8da0a7; font-size: .85rem; text-align: center; }.empty-chart span { color: #63cfbd; font-size: 2rem; }
    .appointment-row { display: flex; align-items: center; gap: 1rem; padding: 1rem 1.5rem; transition: background .2s; }.appointment-row:hover { background: #f7fcfb; }
    .pet-avatar { display: grid; height: 2.8rem; width: 2.8rem; flex: 0 0 auto; place-items: center; border-radius: .9rem; background: #e4f8f3; color: #197e75; font-weight: 900; }
    .status-pill { display: inline-block; margin-top: .35rem; border-radius: 999px; background: #f1f5f5; padding: .3rem .55rem; color: #64777e; font-size: .62rem; font-weight: 800; }
    .view-link { color: #17887f; font-size: .78rem; font-weight: 800; }.view-link span { margin-left: .25rem; transition: margin .2s; }.view-link:hover span { margin-left: .5rem; }
    .quick-panel { position: relative; overflow: hidden; border-radius: 1.15rem; background: linear-gradient(145deg, #172d3b, #12655f); box-shadow: 0 16px 38px rgb(18 87 83 / 16%); }.quick-panel::after { content: ''; position: absolute; right: -4rem; top: -4rem; height: 13rem; width: 13rem; border: 1px solid rgb(164 255 235 / 20%); border-radius: 50%; box-shadow: 0 0 0 1.5rem rgb(164 255 235 / 5%), 0 0 0 3rem rgb(164 255 235 / 4%); }.quick-panel > * { position: relative; z-index: 1; }.quick-panel-icon { display: grid; height: 2.25rem; width: 2.25rem; place-items: center; margin-bottom: 1.2rem; border-radius: .7rem; background: rgb(159 245 226 / 16%); color: #a5f3e5; }.quick-link { display: flex; align-items: center; justify-content: space-between; gap: .75rem; border: 1px solid rgb(255 255 255 / 10%); border-radius: .8rem; padding: .7rem .8rem; color: white; transition: background .2s, transform .2s; }.quick-link:hover { transform: translateX(3px); background: rgb(255 255 255 / 12%); }.quick-link b, .quick-link small { display: block; }.quick-link b { font-size: .75rem; }.quick-link small { margin-top: .15rem; color: #a8c7c7; font-size: .65rem; }
    @media (max-width: 639px) { .donut-wrap { height: 7.5rem; width: 7.5rem; }.donut-hole { height: 5.2rem; width: 5.2rem; }.appointment-row { align-items: flex-start; padding-inline: 1rem; }.appointment-row > div:last-child { margin-left: auto; }.hero-pattern { right: -2rem; } }
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
  readonly statusTotal = computed(() => this.statusChart().reduce((total, item) => total + item.value, 0));
  readonly statusDonut = computed(() => {
    const total = Math.max(this.statusTotal(), 1);
    let start = 0;
    const stops = this.statusChart().map((item) => {
      const end = start + (item.value / total) * 360;
      const stop = `${item.color} ${start}deg ${end}deg`;
      start = end;
      return stop;
    });
    return `conic-gradient(${stops.join(', ')})`;
  });
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
