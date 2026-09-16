import { Injectable, signal } from '@angular/core';
import { AdminNotification, AdminSettings, AdminUser, AdminUserDraft, Appointment, AppointmentDraft, Category, CategoryDraft, ChartPoint, ClinicalRecord, ClinicalRecordDraft, DashboardSummary, InventoryItem, Product, ProductDraft, Sale, SaleDraft, Activity } from '../models/admin.models';

@Injectable({ providedIn: 'root' })
export class AdminMockDataService {
  readonly products = signal<Product[]>([
    { id: 1, name: 'Alimento Premium Adulto', sku: 'ALI-001', category: 'Alimentos', price: 42.9, stock: 34, status: 'Activo', imageUrl: '/logo.png' },
    { id: 2, name: 'Antipulgas 10-20 kg', sku: 'MED-014', category: 'Medicamentos', price: 18.5, stock: 6, status: 'Bajo stock', imageUrl: '/logo.png' },
    { id: 3, name: 'Collar reflectante', sku: 'ACC-008', category: 'Accesorios', price: 12, stock: 21, status: 'Activo', imageUrl: '/logo.png' },
    { id: 4, name: 'Shampoo dermatologico', sku: 'HIG-021', category: 'Higiene', price: 16.75, stock: 3, status: 'Bajo stock', imageUrl: '/logo.png' },
  ]);
  readonly categories = signal<Category[]>([
    { id: 1, name: 'Alimentos', description: 'Nutricion para perros y gatos', products: 18, active: true },
    { id: 2, name: 'Medicamentos', description: 'Productos veterinarios', products: 24, active: true },
    { id: 3, name: 'Accesorios', description: 'Paseo, descanso y juego', products: 12, active: true },
    { id: 4, name: 'Higiene', description: 'Cuidado y limpieza', products: 9, active: true },
  ]);
  readonly appointments = signal<Appointment[]>([
    { id: 1, date: '2026-09-15', time: '09:00', patient: 'Luna', owner: 'Maria Torres', service: 'Vacunacion', veterinarian: 'Dra. Rojas', status: 'Confirmada' },
    { id: 2, date: '2026-09-15', time: '10:30', patient: 'Max', owner: 'Carlos Ruiz', service: 'Consulta general', veterinarian: 'Dr. Salazar', status: 'Pendiente' },
    { id: 3, date: '2026-09-15', time: '12:00', patient: 'Milo', owner: 'Elena Diaz', service: 'Control', veterinarian: 'Dra. Rojas', status: 'Completada' },
    { id: 4, date: '2026-09-16', time: '08:30', patient: 'Nala', owner: 'Pedro Leon', service: 'Desparasitacion', veterinarian: 'Dr. Salazar', status: 'Confirmada' },
  ]);
  readonly sales = signal<Sale[]>([
    { id: 1, code: 'V-1048', client: 'Maria Torres', date: '2026-09-15', total: 61.4, method: 'Tarjeta', status: 'Pagada' },
    { id: 2, code: 'V-1047', client: 'Jose Vega', date: '2026-09-15', total: 42.9, method: 'Efectivo', status: 'Pagada' },
    { id: 3, code: 'V-1046', client: 'Elena Diaz', date: '2026-09-14', total: 89.2, method: 'Transferencia', status: 'Pagada' },
  ]);
  readonly records = signal<ClinicalRecord[]>([
    { id: 1, patient: 'Luna', species: 'Canino', owner: 'Maria Torres', date: '2026-09-15', diagnosis: 'Paciente saludable', treatment: 'Vacuna anual', veterinarian: 'Dra. Rojas' },
    { id: 2, patient: 'Max', species: 'Felino', owner: 'Carlos Ruiz', date: '2026-09-12', diagnosis: 'Dermatitis leve', treatment: 'Shampoo medicado por 10 dias', veterinarian: 'Dr. Salazar' },
    { id: 3, patient: 'Milo', species: 'Canino', owner: 'Elena Diaz', date: '2026-09-08', diagnosis: 'Control postoperatorio', treatment: 'Alta medica', veterinarian: 'Dra. Rojas' },
  ]);
  readonly notifications = signal<AdminNotification[]>([
    { id: 1, title: 'Stock critico', message: 'Shampoo dermatologico tiene 3 unidades.', time: 'Hace 12 min', kind: 'stock', read: false },
    { id: 2, title: 'Cita confirmada', message: 'Maria confirmo la cita de Luna.', time: 'Hace 35 min', kind: 'cita', read: false },
    { id: 3, title: 'Respaldo completado', message: 'Los datos se respaldaron correctamente.', time: 'Ayer', kind: 'sistema', read: true },
  ]);
  readonly users = signal<AdminUser[]>([
    { id: 1, name: 'Ana Rojas', email: 'ana@clinicasmp.pe', role: 'Veterinario', active: true },
    { id: 2, name: 'Luis Salazar', email: 'luis@clinicasmp.pe', role: 'Administrador', active: true },
    { id: 3, name: 'Sofia Reyes', email: 'sofia@clinicasmp.pe', role: 'Recepcionista', active: true },
  ]);
  readonly activities = signal<Activity[]>([
    { id: 1, action: 'Venta registrada', detail: 'V-1048 por S/ 61.40', time: 'Hace 8 min', kind: 'venta' },
    { id: 2, action: 'Cita completada', detail: 'Control de Milo', time: 'Hace 42 min', kind: 'cita' },
    { id: 3, action: 'Producto actualizado', detail: 'Stock de Antipulgas', time: 'Hace 1 h', kind: 'producto' },
  ]);
  readonly summary = signal<DashboardSummary>({ sales: 12480, appointments: 28, products: 63, clients: 186, salesChange: 12.4, appointmentsChange: 8.1 });
  readonly salesChart = signal<ChartPoint[]>([{ label: 'Lun', value: 48 }, { label: 'Mar', value: 62 }, { label: 'Mie', value: 45 }, { label: 'Jue', value: 78 }, { label: 'Vie', value: 68 }, { label: 'Sab', value: 92 }, { label: 'Dom', value: 58 }]);
  readonly settings = signal<AdminSettings>({ clinicName: 'Clinica Veterinaria SMP', email: 'contacto@clinicasmp.pe', phone: '+51 987 654 321', address: 'San Martin de Porres, Lima', lowStockThreshold: 8, appointmentReminders: true, stockAlerts: true });

  inventory(): InventoryItem[] { return this.products().map((p) => ({ id: p.id, product: p.name, sku: p.sku, stock: p.stock, minimum: 8, location: `A-${p.id + 2}`, updatedAt: 'Hoy, 09:24' })); }
  addProduct(value: ProductDraft): void { this.products.update((items) => [...items, { ...value, id: this.nextId(items), status: value.stock <= 8 ? 'Bajo stock' : 'Activo' }]); }
  updateProduct(id: number, value: ProductDraft): void { this.products.update((items) => items.map((item) => item.id === id ? { ...value, id, status: value.stock <= 8 ? 'Bajo stock' : 'Activo' } : item)); }
  deleteProduct(id: number): void { this.products.update((items) => items.filter((item) => item.id !== id)); }
  updateStock(id: number, stock: number): void { this.products.update((items) => items.map((item) => item.id === id ? { ...item, stock, status: stock <= 8 ? 'Bajo stock' : 'Activo' } : item)); }
  addCategory(value: CategoryDraft): void { this.categories.update((items) => [...items, { ...value, id: this.nextId(items), products: 0, active: true }]); }
  addAppointment(value: AppointmentDraft): void { this.appointments.update((items) => [...items, { ...value, id: this.nextId(items), status: 'Pendiente' }]); }
  setAppointmentStatus(id: number, status: Appointment['status']): void { this.appointments.update((items) => items.map((item) => item.id === id ? { ...item, status } : item)); }
  addSale(value: SaleDraft): void { this.sales.update((items) => [...items, { ...value, id: this.nextId(items), code: `V-${1048 + items.length}`, date: new Date().toISOString().slice(0, 10), status: 'Pagada' }]); }
  addRecord(value: ClinicalRecordDraft): void { this.records.update((items) => [...items, { ...value, id: this.nextId(items), date: new Date().toISOString().slice(0, 10) }]); }
  markNotification(id: number): void { this.notifications.update((items) => items.map((item) => item.id === id ? { ...item, read: true } : item)); }
  markAllNotifications(): void { this.notifications.update((items) => items.map((item) => ({ ...item, read: true }))); }
  addUser(value: AdminUserDraft): void { this.users.update((items) => [...items, { ...value, id: this.nextId(items), active: true }]); }
  toggleUser(id: number): void { this.users.update((items) => items.map((item) => item.id === id ? { ...item, active: !item.active } : item)); }
  saveSettings(value: AdminSettings): void { this.settings.set(value); }
  private nextId(items: ReadonlyArray<{ id: number }>): number { return Math.max(0, ...items.map(({ id }) => id)) + 1; }
}
