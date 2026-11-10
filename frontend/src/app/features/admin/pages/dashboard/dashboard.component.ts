import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { finalize, forkJoin } from 'rxjs';
import { AuthService } from '../../../../core/auth/auth.service';
import { AdminApiService, AdminAppointment, AdminProduct, Sale, AdminCategory, AdminSettings, AdminUserNotification, SalesSummary } from '../../services/admin-api.service';
import { StatCardComponent } from '../../shared/stat-card.component';

@Component({ selector: 'app-admin-dashboard', standalone: true, imports: [RouterLink, StatCardComponent], templateUrl: './dashboard.component.html', styleUrl: './dashboard.component.css' })
export class DashboardComponent {
  private readonly api = inject(AdminApiService);
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
  readonly today = new Intl.DateTimeFormat('es-PE', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: 'America/Lima' }).format(new Date());
  readonly administratorName;
  readonly todaySales = computed(() => Number(this.salesSummary()?.total_ventas ?? 0));
  readonly periodLabel = computed(() => ({ dia: 'hoy', semana: 'los últimos 7 días', mes: 'este mes' })[this.period()]);
  private loadVersion = 0;
  readonly bestSellers;
  readonly categoryChart;
  readonly periodOptions = ['dia', 'semana', 'mes'] as const;

  constructor(auth: AuthService) {
    this.lowStock = computed(() => this.catalogProducts().filter((item) => item.stock_actual <= Math.max(item.stock_minimo, this.settings()?.umbral_stock_bajo ?? 0)));
    this.bestSellers = computed(() => [...this.catalogProducts()].sort((a, b) => b.stock_actual - a.stock_actual).slice(0, 3));
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
    if (this.period() === 'mes') start.setUTCDate(1);
    const filters = { fecha_inicial: start.toISOString().slice(0, 10), fecha_final: localDate, estado: 'PAGADA' };
    this.operationalLoading.set(true); this.operationalError.set('');
    forkJoin({
      appointments: this.api.getAppointments(localDate), sales: this.api.getSales({ ...filters, tamano_pagina: 4 }),
      summary: this.api.getSalesSummary(filters), products: this.api.getProducts(), categories: this.api.getCategories(),
      settings: this.api.getSettings(), activity: this.api.getAdminNotifications(),
    }).pipe(finalize(() => { if (version === this.loadVersion) this.operationalLoading.set(false); })).subscribe({
      next: ({ appointments, sales, summary, products, categories, settings, activity }) => {
        if (version !== this.loadVersion) return;
        this.todayAppointments.set(appointments); this.recentSales.set(sales.ventas); this.salesSummary.set(summary);
        this.catalogProducts.set(products); this.categories.set(categories); this.settings.set(settings); this.activity.set(activity.slice(0, 5));
      },
      error: () => { if (version === this.loadVersion) this.operationalError.set('No se pudo cargar el resumen operativo. Intenta actualizar los datos.'); },
    });
  }

  setPeriod(period: 'dia' | 'semana' | 'mes'): void {
    this.period.set(period);
    this.load();
  }

  money(value: string): string { return Number(value).toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  formatTime(value: string): string { return new Intl.DateTimeFormat('es-PE', { timeStyle: 'short', timeZone: 'America/Lima' }).format(new Date(value)); }
}
