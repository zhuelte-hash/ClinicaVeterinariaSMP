import { Component, computed, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../../../core/auth/auth.service';
import { AdminDataService } from '../../services/admin-data.service';
import { StatCardComponent } from '../../shared/stat-card.component';
import { StatusBadgeComponent } from '../../shared/status-badge.component';

@Component({ selector: 'app-admin-dashboard', standalone: true, imports: [RouterLink, StatCardComponent, StatusBadgeComponent], templateUrl: './dashboard.component.html', styleUrl: './dashboard.component.css' })
export class DashboardComponent {
  readonly data: AdminDataService;
  readonly todayAppointments;
  readonly lowStock;
  readonly maxChart;
  readonly period = signal<'dia' | 'semana' | 'mes'>('dia');
  readonly today = new Intl.DateTimeFormat('es-PE', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(new Date());
  readonly administratorName;
  readonly todaySales;
  readonly bestSellers;
  readonly categoryChart;
  readonly periodOptions = ['dia', 'semana', 'mes'] as const;

  constructor(data: AdminDataService, auth: AuthService) {
    const localDate = new Date().toLocaleDateString('en-CA');
    this.data = data;
    this.todayAppointments = computed(() => data.appointments().filter((item) => item.date === localDate));
    this.todaySales = computed(() => data.sales().filter((item) => item.date === localDate).reduce((total, item) => total + item.total, 0));
    this.lowStock = computed(() => data.products().filter((item) => item.stock <= 8));
    this.bestSellers = computed(() => [...data.products()].sort((a, b) => a.stock - b.stock).slice(0, 3));
    this.categoryChart = computed(() => data.categories().map((category) => ({ label: category.name, value: category.products })));
    this.maxChart = computed(() => Math.max(1, ...this.categoryChart().map((item) => item.value)));
    this.administratorName = computed(() => (auth.currentUser()?.nombre || 'Administrador').split(' ')[0]);
  }

  setPeriod(period: 'dia' | 'semana' | 'mes'): void {
    this.period.set(period);
  }
}
