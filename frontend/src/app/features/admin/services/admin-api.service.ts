import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable, Subject, map, tap } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { VeterinarianClinicalRecord } from '../../veterinarian/veterinarian.models';

export interface AdminProduct { id: number; sku: string; nombre: string; precio_venta: number; stock_actual: number; stock_minimo: number; activo: boolean; imagen_url: string; categoria_id: number; categoria_nombre: string; }
export interface AdminClient { id: number; nombre: string; correo: string; telefono: string | null; direccion: string | null; mascotas: number; citas: number; ultima_cita: string | null; }
export interface CatalogOption { id: number; nombre: string; }
export interface ProductCatalog { categorias: CatalogOption[]; proveedores: CatalogOption[]; }
export interface AdminCategory { id: number; nombre: string; productos: number; }
export interface ProductCreate { categoria_id: number; proveedor_id: number; sku: string; nombre: string; precio_venta: number; stock_actual: number; stock_minimo: number; imagen_url: string; }
export interface AdminAppointment { id: number; fecha_hora_programada: string; fecha_hora_fin_programada: string; estado: string; cliente_nombre: string; mascota_nombre: string; servicio_nombre: string; veterinario_id: number | null; veterinario_nombre: string | null; nota_coordinacion: string | null; }
export interface AdminNotification { id: number; cita_id: number | null; tipo: string; titulo: string; mensaje: string; leida: boolean; fecha_creacion: string; }
export interface AdminSale { id: number; codigo_orden: string; fecha_emision: string; cajero_nombre: string; cliente_nombre: string | null; total: number; medio_pago: string | null; }
export interface SalesDay { fecha: string; total: number; ventas: AdminSale[]; }
export interface Sale { id: number; codigo_orden: string; fecha_emision: string; cajero_id: number; cajero_nombre: string; cliente_nombre: string | null; medio_pago: string; subtotal: string; descuento: string; impuesto: string; total: string; estado: 'PAGADA' | 'ANULADA' | 'PENDIENTE'; }
export interface SaleDetail extends Sale { detalles: { producto_id: number | null; servicio_id: number | null; nombre: string; cantidad: number; precio_unitario: string; subtotal: string }[]; }
export interface SalesPage { total: number; pagina: number; tamano_pagina: number; ventas: Sale[]; }
export interface SalesSummary { total_ventas: string; cantidad_ventas: number; ticket_promedio: string; productos_vendidos: number; }
export interface SalesFilters { fecha_inicial?: string; fecha_final?: string; numero_venta?: string; estado?: string; metodo_pago?: string; cajero_id?: number; producto_id?: number; pagina?: number; tamano_pagina?: number; }
export type Role = 'administrador' | 'veterinario' | 'cajero' | 'cliente';
export interface RolePermission { rol: Role; modulo: string; puede_ver: boolean; puede_crear: boolean; puede_editar: boolean; puede_eliminar: boolean; puede_aprobar: boolean; }
export interface AdminUserNotification { id: number; usuario_id: number; usuario_nombre: string; tipo: string; titulo: string; mensaje: string; leida: boolean; fecha_creacion: string; }
export type AdminClinicalRecord = VeterinarianClinicalRecord;
export interface AdminSettings { nombre: string; correo: string; telefono: string; direccion: string; umbral_stock_bajo: number; recordatorios_citas: boolean; alertas_stock: boolean; }

@Injectable({ providedIn: 'root' })
export class AdminApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/admin`;
  readonly notificationChanges = new Subject<void>();
  private normalizeProduct(product: AdminProduct): AdminProduct { return { ...product, precio_venta: Number(product.precio_venta) }; }
  getProducts(): Observable<AdminProduct[]> { return this.http.get<AdminProduct[]>(`${this.baseUrl}/productos`).pipe(map((items) => items.map((item) => this.normalizeProduct(item)))); }
  getProductCatalog(): Observable<ProductCatalog> { return this.http.get<ProductCatalog>(`${this.baseUrl}/productos/catalogo`); }
  getCategories(): Observable<AdminCategory[]> { return this.http.get<AdminCategory[]>(`${this.baseUrl}/categorias`); }
  createCategory(nombre: string): Observable<AdminCategory> { return this.http.post<AdminCategory>(`${this.baseUrl}/categorias`, { nombre }); }
  updateCategory(id: number, nombre: string): Observable<AdminCategory> { return this.http.patch<AdminCategory>(`${this.baseUrl}/categorias/${id}`, { nombre }); }
  deleteCategory(id: number): Observable<void> { return this.http.delete<void>(`${this.baseUrl}/categorias/${id}`); }
  createProduct(data: ProductCreate): Observable<AdminProduct> { return this.http.post<AdminProduct>(`${this.baseUrl}/productos`, data).pipe(map((item) => this.normalizeProduct(item))); }
  updateProduct(id: number, data: Partial<Pick<ProductCreate, 'categoria_id' | 'sku' | 'nombre' | 'precio_venta' | 'stock_minimo' | 'imagen_url'>>): Observable<AdminProduct> { return this.http.patch<AdminProduct>(`${this.baseUrl}/productos/${id}`, data).pipe(map((item) => this.normalizeProduct(item))); }
  getInventory(): Observable<AdminProduct[]> { return this.http.get<AdminProduct[]>(`${this.baseUrl}/inventario`).pipe(map((items) => items.map((item) => this.normalizeProduct(item)))); }
  getClients(): Observable<AdminClient[]> { return this.http.get<AdminClient[]>(`${this.baseUrl}/clientes`); }
  updateStock(id: number, stock: number): Observable<AdminProduct> { return this.http.patch<AdminProduct>(`${this.baseUrl}/inventario/${id}`, { stock_actual: stock }).pipe(map((item) => this.normalizeProduct(item))); }
  uploadProductImage(image: File): Observable<{ url: string }> { const form = new FormData(); form.append('image', image); return this.http.post<{ url: string }>(`${this.baseUrl}/productos/imagen`, form); }
  deactivateProduct(id: number): Observable<void> { return this.http.delete<void>(`${this.baseUrl}/productos/${id}`); }
  getAppointments(date?: string, status?: string): Observable<AdminAppointment[]> { const params: Record<string, string> = {}; if (date) params['fecha'] = date; if (status) params['estado'] = status; return this.http.get<AdminAppointment[]>(`${this.baseUrl}/citas`, { params }); }
  getNotifications(): Observable<AdminNotification[]> { return this.http.get<AdminNotification[]>(`${environment.apiUrl}/portal/notificaciones`); }
  getAppointmentVeterinarians(): Observable<CatalogOption[]> { return this.http.get<CatalogOption[]>(`${this.baseUrl}/citas/veterinarios`); }
  updateAppointment(id: number, data: { estado?: string; fecha_hora_programada?: string; veterinario_id?: number | null; nota_coordinacion?: string }): Observable<AdminAppointment> { return this.http.patch<AdminAppointment>(`${this.baseUrl}/citas/${id}`, data); }
  getClinicalRecords(): Observable<AdminClinicalRecord[]> { return this.http.get<AdminClinicalRecord[]>(`${this.baseUrl}/historial-clinico`); }
  getAdminNotifications(unread = false): Observable<AdminUserNotification[]> { return this.http.get<AdminUserNotification[]>(`${this.baseUrl}/notificaciones`, { params: unread ? { no_leidas: 'true' } : {} }); }
  createNotification(data: { usuario_id: number; tipo: string; titulo: string; mensaje: string }): Observable<AdminUserNotification> { return this.http.post<AdminUserNotification>(`${this.baseUrl}/notificaciones`, data); }
  markAllNotifications(): Observable<void> { return this.http.post<void>(`${this.baseUrl}/notificaciones/marcar-leidas`, {}).pipe(tap(() => this.notificationChanges.next())); }
  markNotificationRead(id: number): Observable<AdminNotification> { return this.http.patch<AdminNotification>(`${environment.apiUrl}/portal/notificaciones/${id}/leer`, {}).pipe(tap(() => this.notificationChanges.next())); }
  getSettings(): Observable<AdminSettings> { return this.http.get<AdminSettings>(`${this.baseUrl}/configuracion`); }
  updateSettings(data: AdminSettings): Observable<AdminSettings> { return this.http.patch<AdminSettings>(`${this.baseUrl}/configuracion`, data); }
  getSalesDay(date?: string): Observable<SalesDay> { const params: Record<string, string> = {}; if (date) params['fecha'] = date; return this.http.get<SalesDay>(`${this.baseUrl}/ventas/dia`, { params }).pipe(map(report => ({ ...report, total: Number(report.total), ventas: report.ventas.map(sale => ({ ...sale, total: Number(sale.total) })) }))); }
  private salesParams(filters: SalesFilters): Record<string, string> { return Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== undefined && value !== '').map(([key, value]) => [key, String(value)])); }
  getSales(filters: SalesFilters): Observable<SalesPage> { return this.http.get<SalesPage>(`${environment.apiUrl}/api/admin/ventas`, { params: this.salesParams(filters) }); }
  getSalesSummary(filters: SalesFilters): Observable<SalesSummary> { return this.http.get<SalesSummary>(`${environment.apiUrl}/api/admin/ventas/resumen`, { params: this.salesParams(filters) }); }
  getSale(id: number): Observable<SaleDetail> { return this.http.get<SaleDetail>(`${environment.apiUrl}/api/admin/ventas/${id}`); }
  voidSale(id: number): Observable<SaleDetail> { return this.http.post<SaleDetail>(`${environment.apiUrl}/api/admin/ventas/${id}/anular`, {}); }
  getPermissions(): Observable<RolePermission[]> { return this.http.get<RolePermission[]>(`${this.baseUrl}/permisos`); }
  applyRecommendedPermissions(role?: Role): Observable<RolePermission[]> { return this.http.post<RolePermission[]>(`${this.baseUrl}/permisos${role ? `/${role}` : ''}/recomendados`, {}); }
  updatePermission(role: Role, module: string, data: Omit<RolePermission, 'rol' | 'modulo'>): Observable<RolePermission> { return this.http.put<RolePermission>(`${this.baseUrl}/permisos/${role}/${module}`, data); }
}
