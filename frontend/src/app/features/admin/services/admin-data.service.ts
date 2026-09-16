import { Injectable, Signal, inject } from '@angular/core';
import { environment } from '../../../../environments/environment';
import { AdminNotification, AdminSettings, AdminUser, AdminUserDraft, Appointment, AppointmentDraft, Category, CategoryDraft, ChartPoint, ClinicalRecord, ClinicalRecordDraft, DashboardSummary, InventoryItem, Product, ProductDraft, Sale, SaleDraft, Activity } from '../models/admin.models';
import { AdminMockDataService } from './admin-mock-data.service';

@Injectable({ providedIn: 'root' })
export class AdminDataService {
  private readonly mock = inject(AdminMockDataService);
  readonly useMockData = (environment as typeof environment & { useAdminMockData?: boolean }).useAdminMockData ?? true;
  readonly products: Signal<Product[]> = this.mock.products;
  readonly categories: Signal<Category[]> = this.mock.categories;
  readonly appointments: Signal<Appointment[]> = this.mock.appointments;
  readonly sales: Signal<Sale[]> = this.mock.sales;
  readonly records: Signal<ClinicalRecord[]> = this.mock.records;
  readonly notifications: Signal<AdminNotification[]> = this.mock.notifications;
  readonly users: Signal<AdminUser[]> = this.mock.users;
  readonly activities: Signal<Activity[]> = this.mock.activities;
  readonly summary: Signal<DashboardSummary> = this.mock.summary;
  readonly salesChart: Signal<ChartPoint[]> = this.mock.salesChart;
  readonly settings: Signal<AdminSettings> = this.mock.settings;

  inventory(): InventoryItem[] { return this.mock.inventory(); }
  addProduct(value: ProductDraft): void { this.mock.addProduct(value); }
  updateProduct(id: number, value: ProductDraft): void { this.mock.updateProduct(id, value); }
  deleteProduct(id: number): void { this.mock.deleteProduct(id); }
  updateStock(id: number, stock: number): void { this.mock.updateStock(id, stock); }
  addCategory(value: CategoryDraft): void { this.mock.addCategory(value); }
  addAppointment(value: AppointmentDraft): void { this.mock.addAppointment(value); }
  setAppointmentStatus(id: number, status: Appointment['status']): void { this.mock.setAppointmentStatus(id, status); }
  addSale(value: SaleDraft): void { this.mock.addSale(value); }
  addRecord(value: ClinicalRecordDraft): void { this.mock.addRecord(value); }
  markNotification(id: number): void { this.mock.markNotification(id); }
  markAllNotifications(): void { this.mock.markAllNotifications(); }
  addUser(value: AdminUserDraft): void { this.mock.addUser(value); }
  toggleUser(id: number): void { this.mock.toggleUser(id); }
  saveSettings(value: AdminSettings): void { this.mock.saveSettings(value); }
}
