import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';

export type PaymentMethod = 'efectivo' | 'yape' | 'plin' | 'tarjeta' | 'transferencia';
export interface OrderLine { producto_id?: number | null; servicio_id?: number | null; cantidad: string | number; nombre?: string; precio_unitario?: string | number; subtotal?: string | number; }
export interface OrderPayment { id: number; monto: number; medio: PaymentMethod; canal: string; estado: string; fecha: string; codigo_operacion: string | null; tiene_comprobante: boolean; motivo: string | null; registrado_por_nombre: string; validado_por_nombre: string | null; }
export interface BillingOrder { id: number; codigo: string; cliente_id: number; cliente_nombre: string; creador_nombre: string; proceso_id: number | null; fecha: string; estado: string; total: number; descuento: number; abonado: number; saldo: number; venta_id: number | null; motivo_anulacion: string | null; sin_comprobante: boolean; detalles: OrderLine[]; abonos: OrderPayment[]; historial?: { id: number; fecha: string; autor: string; accion: string; cambios: Record<string, { antes: unknown; despues: unknown }> }[]; }
export interface DiscountAuthorization { id: number; cliente_id: number | null; monto: number; motivo: string; estado: string; usada: boolean; solicitante_id: number; solicitante_nombre: string; cliente_nombre: string; aprobador_nombre: string | null; }
export interface BillingCatalog { clientes: { id: number; nombre: string }[]; productos: { id: number; nombre: string; precio: number; stock: number; unidad: string; fraccionable: boolean }[]; servicios: { id: number; nombre: string; precio: number }[]; }
export interface BillingAttention { id: number; mascota: string; servicio: string; detalles: OrderLine[]; }
export interface StaffSale { id: number; codigo_orden: string; monto_total: number; estado_pago: string; motivo_anulacion: string | null; anulado_por_nombre: string | null; }
export interface OwnPayments { ordenes: BillingOrder[]; ventas: { id: number; codigo: string; total: number; estado: string; fecha: string; origen: string; boleta: string | null }[]; pedidos_web: { id: number; codigo: string; total: number; estado: string; estado_pago: string; fecha: string; motivo_rechazo: string | null; comprobante: string }[]; }

export function apiError(error: unknown): string {
  if (error instanceof HttpErrorResponse) {
    const detail = error.error?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map(item => item.msg).join('. ');
  }
  return 'No se pudo completar la operación. Revisa la conexión e intenta nuevamente.';
}

@Injectable({ providedIn: 'root' })
export class BillingApiService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/operaciones`;
  orders(filters: Record<string, string | boolean> = {}) { let params = new HttpParams(); for (const [key, value] of Object.entries(filters)) if (value !== '' && value !== false) params = params.set(key, value); return this.http.get<BillingOrder[]>(`${this.base}/ordenes`, { params }); }
  order(id: number) { return this.http.get<BillingOrder>(`${this.base}/ordenes/${id}`); }
  catalog() { return this.http.get<BillingCatalog>(`${this.base}/catalogo`); }
  attentions(client: number) { return this.http.get<BillingAttention[]>(`${this.base}/atenciones`, { params: { cliente_id: client } }); }
  createOrder(data: { cliente_id: number; detalles: OrderLine[]; proceso_id: number | null; autorizacion_id: number | null; clave_idempotencia: string }) { return this.http.post<BillingOrder>(`${this.base}/ordenes`, data); }
  payment(id: number, data: { monto: string; medio: PaymentMethod; canal: string; codigo_operacion: string | null; clave_idempotencia: string }, file: File | null) {
    if (file) { const form = new FormData(); form.append('datos', JSON.stringify(data)); form.append('archivo', file); return this.http.post<BillingOrder>(`${this.base}/ordenes/${id}/comprobantes`, form); }
    return this.http.post<BillingOrder>(`${this.base}/ordenes/${id}/abonos`, data);
  }
  validatePayment(id: number) { return this.http.post<BillingOrder>(`${this.base}/pagos/${id}/validar`, {}); }
  reason(action: 'ordenes' | 'ventas' | 'pagos', id: number, reason: string) { return this.http.post<unknown>(`${this.base}/${action}/${id}/${action === 'pagos' ? 'rechazar' : 'anular'}`, { motivo: reason }); }
  sales() { return this.http.get<StaffSale[]>(`${this.base}/ventas`); }
  ownPayments() { return this.http.get<OwnPayments>(`${this.base}/mis-pagos`); }
  discounts() { return this.http.get<DiscountAuthorization[]>(`${this.base}/descuentos`); }
  requestDiscount(cliente_id: number | null, monto: number, motivo: string) { return this.http.post<DiscountAuthorization>(`${this.base}/descuentos`, { cliente_id, monto, motivo }); }
  reviewDiscount(id: number, approve: boolean) { return this.http.post(`${this.base}/descuentos/${id}/${approve ? 'aprobar' : 'rechazar'}`, {}); }
  file(path: string) { return this.http.get(`${environment.apiUrl}${path}`, { responseType: 'blob' }); }
  download(blob: Blob, filename: string): void { const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = filename; link.click(); setTimeout(() => URL.revokeObjectURL(url), 30_000); }
}
