import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';

export interface AdminProduct { id: number; sku: string; nombre: string; precio_venta: number; stock_actual: number; stock_minimo: number; activo: boolean; imagen_url: string; categoria_id: number; categoria_nombre: string; }
export interface CatalogOption { id: number; nombre: string; }
export interface ProductCatalog { categorias: CatalogOption[]; proveedores: CatalogOption[]; }
export interface ProductCreate { categoria_id: number; proveedor_id: number; sku: string; nombre: string; precio_venta: number; stock_actual: number; stock_minimo: number; imagen_url: string; }
export interface AdminAppointment { id: number; fecha_hora_programada: string; estado: string; cliente_nombre: string; mascota_nombre: string; servicio_nombre: string; veterinario_nombre: string | null; }
export interface AdminSale { id: number; codigo_orden: string; fecha_emision: string; cajero_nombre: string; cliente_nombre: string | null; total: number; medio_pago: string | null; }
export interface SalesDay { fecha: string; total: number; ventas: AdminSale[]; }
export interface Sale { id: number; codigo_orden: string; fecha_emision: string; cajero_id: number; cajero_nombre: string; cliente_nombre: string | null; medio_pago: string; subtotal: string; descuento: string; impuesto: string; total: string; estado: 'PAGADA' | 'ANULADA' | 'PENDIENTE'; }
export interface SaleDetail extends Sale { detalles: { producto_id: number | null; servicio_id: number | null; nombre: string; cantidad: number; precio_unitario: string; subtotal: string }[]; }
export interface SalesPage { total: number; pagina: number; tamano_pagina: number; ventas: Sale[]; }
export interface SalesSummary { total_ventas: string; cantidad_ventas: number; ticket_promedio: string; productos_vendidos: number; }
export interface SalesFilters { fecha_inicial?: string; fecha_final?: string; numero_venta?: string; estado?: string; metodo_pago?: string; cajero_id?: number; producto_id?: number; pagina?: number; tamano_pagina?: number; }
export type Role = 'administrador' | 'veterinario' | 'cajero' | 'cliente';
export interface RolePermission { rol: Role; modulo: string; puede_ver: boolean; puede_crear: boolean; puede_editar: boolean; puede_eliminar: boolean; puede_aprobar: boolean; }

@Injectable({ providedIn: 'root' })
export class AdminApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/admin`;
  getProducts(): Observable<AdminProduct[]> { return this.http.get<AdminProduct[]>(`${this.baseUrl}/productos`); }
  getProductCatalog(): Observable<ProductCatalog> { return this.http.get<ProductCatalog>(`${this.baseUrl}/productos/catalogo`); }
  createProduct(data: ProductCreate): Observable<AdminProduct> { return this.http.post<AdminProduct>(`${this.baseUrl}/productos`, data); }
  updateProduct(id: number, data: Partial<Pick<ProductCreate, 'sku' | 'nombre' | 'precio_venta' | 'stock_minimo' | 'imagen_url'>>): Observable<AdminProduct> { return this.http.patch<AdminProduct>(`${this.baseUrl}/productos/${id}`, data); }
  uploadProductImage(image: File): Observable<{ url: string }> { const form = new FormData(); form.append('image', image); return this.http.post<{ url: string }>(`${this.baseUrl}/productos/imagen`, form); }
  deactivateProduct(id: number): Observable<void> { return this.http.delete<void>(`${this.baseUrl}/productos/${id}`); }
  getAppointments(date?: string, status?: string): Observable<AdminAppointment[]> { const params: Record<string, string> = {}; if (date) params['fecha'] = date; if (status) params['estado'] = status; return this.http.get<AdminAppointment[]>(`${this.baseUrl}/citas`, { params }); }
  getSalesDay(date?: string): Observable<SalesDay> { const params: Record<string, string> = {}; if (date) params['fecha'] = date; return this.http.get<SalesDay>(`${this.baseUrl}/ventas/dia`, { params }); }
  private salesParams(filters: SalesFilters): Record<string, string> { return Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== undefined && value !== '').map(([key, value]) => [key, String(value)])); }
  getSales(filters: SalesFilters): Observable<SalesPage> { return this.http.get<SalesPage>(`${environment.apiUrl}/api/admin/ventas`, { params: this.salesParams(filters) }); }
  getSalesSummary(filters: SalesFilters): Observable<SalesSummary> { return this.http.get<SalesSummary>(`${environment.apiUrl}/api/admin/ventas/resumen`, { params: this.salesParams(filters) }); }
  getSale(id: number): Observable<SaleDetail> { return this.http.get<SaleDetail>(`${environment.apiUrl}/api/admin/ventas/${id}`); }
  voidSale(id: number): Observable<SaleDetail> { return this.http.post<SaleDetail>(`${environment.apiUrl}/api/admin/ventas/${id}/anular`, {}); }
  getPermissions(): Observable<RolePermission[]> { return this.http.get<RolePermission[]>(`${this.baseUrl}/permisos`); }
  updatePermission(role: Role, module: string, data: Omit<RolePermission, 'rol' | 'modulo'>): Observable<RolePermission> { return this.http.put<RolePermission>(`${this.baseUrl}/permisos/${role}/${module}`, data); }
}
