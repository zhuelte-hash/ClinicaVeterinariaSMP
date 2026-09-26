import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { AuthService } from '../../../../core/auth/auth.service';
import { AdminDataService } from '../../services/admin-data.service';
import { AdminApiService, AdminAppointment, AdminProduct, SalesDay } from '../../services/admin-api.service';
import { StatCardComponent } from '../../shared/stat-card.component';

@Component({ selector: 'app-admin-dashboard', standalone: true, imports: [RouterLink, StatCardComponent], templateUrl: './dashboard.component.html', styleUrl: './dashboard.component.css' })
export class DashboardComponent {
  private readonly api = inject(AdminApiService);
  readonly data: AdminDataService;
  readonly todayAppointments = signal<AdminAppointment[]>([]);
  readonly salesReport = signal<SalesDay | null>(null);
  readonly catalogProducts = signal<AdminProduct[]>([]);
  readonly operationalLoading = signal(true);
  readonly operationalError = signal('');
  readonly lowStock;
  readonly maxChart;
  readonly period = signal<'dia' | 'semana' | 'mes'>('dia');
  readonly today = new Intl.DateTimeFormat('es-PE', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(new Date());
  readonly administratorName;
  readonly todaySales = computed(() => this.salesReport()?.total ?? 0);
  readonly bestSellers;
  readonly categoryChart;
  readonly periodOptions = ['dia', 'semana', 'mes'] as const;

  constructor(data: AdminDataService, auth: AuthService) {
    const localDate = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima' }).format(new Date());
    this.data = data;
    this.lowStock = computed(() => this.catalogProducts().filter((item) => item.stock_actual <= item.stock_minimo));
    this.bestSellers = computed(() => [...this.catalogProducts()].sort((a, b) => b.stock_actual - a.stock_actual).slice(0, 3));
    this.categoryChart = computed(() => data.categories().map((category) => ({ label: category.name, value: category.products })));
    this.maxChart = computed(() => Math.max(1, ...this.categoryChart().map((item) => item.value)));
    this.administratorName = computed(() => (auth.currentUser()?.nombre || 'Administrador').split(' ')[0]);
    forkJoin({ appointments: this.api.getAppointments(localDate), sales: this.api.getSalesDay(localDate), products: this.api.getProducts() }).subscribe({
      next: ({ appointments, sales, products }) => { this.todayAppointments.set(appointments); this.salesReport.set(sales); this.catalogProducts.set(products); this.operationalLoading.set(false); },
      error: () => { this.operationalError.set('No se pudo cargar el resumen operativo.'); this.operationalLoading.set(false); },
    });
  }

  setPeriod(period: 'dia' | 'semana' | 'mes'): void {
    this.period.set(period);
  }

  formatTime(value: string): string { return new Intl.DateTimeFormat('es-PE', { timeStyle: 'short', timeZone: 'America/Lima' }).format(new Date(value)); }
}
