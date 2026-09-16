export type AdminStatus = 'Activo' | 'Inactivo' | 'Pendiente' | 'Confirmada' | 'Completada' | 'Cancelada' | 'Pagada' | 'Bajo stock';

export interface Product { id: number; name: string; sku: string; category: string; price: number; stock: number; status: AdminStatus; imageUrl: string; }
export interface InventoryItem { id: number; product: string; sku: string; stock: number; minimum: number; location: string; updatedAt: string; }
export interface Category { id: number; name: string; description: string; products: number; active: boolean; }
export interface Appointment { id: number; time: string; date: string; patient: string; owner: string; service: string; veterinarian: string; status: AdminStatus; }
export interface Sale { id: number; code: string; client: string; date: string; total: number; method: string; status: AdminStatus; }
export interface ClinicalRecord { id: number; patient: string; species: string; owner: string; date: string; diagnosis: string; treatment: string; veterinarian: string; }
export interface AdminNotification { id: number; title: string; message: string; time: string; kind: 'cita' | 'stock' | 'sistema'; read: boolean; }
export interface AdminUser { id: number; name: string; email: string; role: 'Administrador' | 'Veterinario' | 'Recepcionista'; active: boolean; }
export interface Activity { id: number; action: string; detail: string; time: string; kind: 'venta' | 'cita' | 'producto'; }
export interface DashboardSummary { sales: number; appointments: number; products: number; clients: number; salesChange: number; appointmentsChange: number; }
export interface ChartPoint { label: string; value: number; }
export interface AdminSettings { clinicName: string; email: string; phone: string; address: string; lowStockThreshold: number; appointmentReminders: boolean; stockAlerts: boolean; }

export type ProductDraft = Omit<Product, 'id' | 'status'>;
export type AppointmentDraft = Omit<Appointment, 'id' | 'status'>;
export type CategoryDraft = Pick<Category, 'name' | 'description'>;
export type SaleDraft = Pick<Sale, 'client' | 'total' | 'method'>;
export type ClinicalRecordDraft = Omit<ClinicalRecord, 'id' | 'date'>;
export type AdminUserDraft = Omit<AdminUser, 'id' | 'active'>;
