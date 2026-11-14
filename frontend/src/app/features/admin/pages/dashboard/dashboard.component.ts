import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { finalize, forkJoin } from 'rxjs';
import { AuthService } from '../../../../core/auth/auth.service';
import { AdminApiService, AdminAppointment, AdminProduct, Sale, AdminCategory, AdminSettings, AdminUserNotification, SalesSummary } from '../../services/admin-api.service';
import { StatCardComponent } from '../../shared/stat-card.component';
import { OperationsApiService, OperationsDashboard } from '../../services/operations-api.service';

@Component({ selector: 'app-admin-dashboard', standalone: true, imports: [RouterLink, FormsModule, StatCardComponent], templateUrl: './dashboard.component.html', styleUrl: './dashboard.component.css' })
export class DashboardComponent {
  private readonly api = inject(AdminApiService);
  private readonly operations = inject(OperationsApiService);
  readonly overview = signal<OperationsDashboard | null>(null);
  readonly appointmentStates = computed(() => Object.entries(this.overview()?.citas_por_estado ?? {}));
  readonly rankings = computed(() => [
    { title: 'Productos más vendidos', description: 'Unidades vendidas; excluye ventas anuladas.', items: this.overview()?.productos_mas_vendidos ?? [] },
    { title: 'Servicios más solicitados', description: 'Citas por servicio y fecha programada, incluidos todos sus estados.', items: this.overview()?.servicios_mas_solicitados ?? [] },
    { title: 'Servicios más atendidos', description: 'Solo citas con atención completada.', items: this.overview()?.servicios_mas_atendidos ?? [] },
  ].map(group => ({ ...group, max: Math.max(1, ...group.items.map(item => Number(item.cantidad))) })));
  readonly categories = signal<AdminCategory[]>([]);
  readonly todayAppointments = signal<AdminAppointment[]>([]);
  readonly recentSales = signal<Sale[]>([]);
  readonly salesSummary = signal<SalesSummary | null>(null);
  readonly settings = signal<AdminSettings | null>(null);
  readonly activity = signal<AdminUserNotification[]>([]);
  readonly catalogProducts = signal<AdminProduct[]>([]);
  readonly operationalLoading = signal(true);
  readonly operationalError = signal('');
  readonly lowStock;
  readonly maxChart;
  readonly period = signal<'dia' | 'semana' | 'mes'>('dia');
  readonly currentMonth = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima', year: 'numeric', month: '2-digit' }).format(new Date()).slice(0, 7);
  readonly month = signal(this.currentMonth);
  readonly today = new Intl.DateTimeFormat('es-PE', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: 'America/Lima' }).format(new Date());
  readonly administratorName;
  readonly todaySales = computed(() => Number(this.overview()?.ventas ?? 0));
  readonly periodLabel = computed(() => this.period() === 'mes' && this.month() !== this.currentMonth ? this.month() : ({ dia: 'hoy', semana: 'los últimos 7 días', mes: 'este mes' })[this.period()]);
  private loadVersion = 0;
  readonly highestStock;
  readonly categoryChart;
  readonly periodOptions = ['dia', 'semana', 'mes'] as const;

  constructor(auth: AuthService) {
    this.lowStock = computed(() => this.catalogProducts().filter((item) => item.stock_actual <= item.stock_minimo));
    this.highestStock = computed(() => [...this.catalogProducts()].sort((a, b) => b.stock_actual - a.stock_actual).slice(0, 3));
    this.categoryChart = computed(() => this.categories().map((category) => ({ label: category.nombre, value: category.productos })));
    this.maxChart = computed(() => Math.max(1, ...this.categoryChart().map((item) => item.value)));
    this.administratorName = computed(() => (auth.currentUser()?.nombre || 'Administrador').split(' ')[0]);
    this.load();
  }

  load(): void {
    const version = ++this.loadVersion;
    const localDate = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima' }).format(new Date());
    const start = new Date(`${localDate}T12:00:00Z`);
    if (this.period() === 'semana') start.setUTCDate(start.getUTCDate() - 6);
    let end = localDate;
    if (this.period() === 'mes') {
      start.setTime(new Date(`${this.month()}-01T12:00:00Z`).getTime());
      const monthEnd = new Date(start);
      monthEnd.setUTCMonth(monthEnd.getUTCMonth() + 1, 0);
      end = monthEnd.toISOString().slice(0, 10) < localDate ? monthEnd.toISOString().slice(0, 10) : localDate;
    }
    const filters = { fecha_inicial: start.toISOString().slice(0, 10), fecha_final: end, estado: 'PAGADA' };
    this.operationalLoading.set(true); this.operationalError.set('');
    forkJoin({
      appointments: this.api.getAppointments(localDate), sales: this.api.getSales({ ...filters, tamano_pagina: 4 }),
      summary: this.api.getSalesSummary(filters), products: this.api.getProducts(), categories: this.api.getCategories(),
      settings: this.api.getSettings(), activity: this.api.getAdminNotifications(),
      overview: this.operations.dashboard(filters.fecha_inicial, filters.fecha_final),
    }).pipe(finalize(() => { if (version === this.loadVersion) this.operationalLoading.set(false); })).subscribe({
      next: ({ appointments, sales, summary, products, categories, settings, activity, overview }) => {
        if (version !== this.loadVersion) return;
        this.todayAppointments.set(appointments); this.recentSales.set(sales.ventas); this.salesSummary.set(summary);
        this.catalogProducts.set(products); this.categories.set(categories); this.settings.set(settings); this.activity.set(activity.slice(0, 5));
        this.overview.set(overview);
      },
      error: () => { if (version === this.loadVersion) this.operationalError.set('No se pudo cargar el resumen operativo. Intenta actualizar los datos.'); },
    });
  }

  setPeriod(period: 'dia' | 'semana' | 'mes'): void {
    this.period.set(period);
    this.load();
  }

  selectMonth(value: string): void {
    if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(value) || value > this.currentMonth || value < '1900-01') return;
    this.month.set(value);
    this.period.set('mes');
    this.load();
  }

  money(value: string): string { return Number(value).toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  formatTime(value: string): string { return new Intl.DateTimeFormat('es-PE', { timeStyle: 'short', timeZone: 'America/Lima' }).format(new Date(value)); }
}
