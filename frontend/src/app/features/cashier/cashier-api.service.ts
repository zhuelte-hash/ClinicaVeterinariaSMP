import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  CashierCategory,
  CashierAttention,
  CashierOrder,
  CashierPendingPayment,
  CashierClient,
  CashierProduct,
  CashierService,
  CashierSummary,
  CashRegister,
  Receipt,
} from './cashier.models';

@Injectable({ providedIn: 'root' })
export class CashierApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/caja`;

  getSummary(): Observable<CashierSummary> {
    return this.http.get<CashierSummary>(`${this.baseUrl}/resumen`);
  }

  openRegister(fondoInicial: number): Observable<CashRegister> {
    return this.http.post<CashRegister>(`${this.baseUrl}/abrir`, {
      fondo_inicial: fondoInicial,
    });
  }

  closeRegister(efectivoContado: number): Observable<CashRegister> {
    return this.http.post<CashRegister>(`${this.baseUrl}/cerrar`, { efectivo_contado: efectivoContado });
  }

  getCategories(): Observable<CashierCategory[]> {
    return this.http.get<CashierCategory[]>(`${this.baseUrl}/categorias`);
  }

  getProducts(): Observable<CashierProduct[]> {
    return this.http.get<CashierProduct[]>(`${this.baseUrl}/productos`);
  }

  getClients(q?: string): Observable<CashierClient[]> {
    return this.http.get<CashierClient[]>(`${this.baseUrl}/clientes`, { params: q ? { q } : {} });
  }

  getClosedRegisters(): Observable<CashRegister[]> {
    return this.http.get<CashRegister[]>(`${this.baseUrl}/cierres`);
  }

  getAttentions(clientId: number): Observable<CashierAttention[]> {
    return this.http.get<CashierAttention[]>(`${this.baseUrl}/atenciones`, { params: { cliente_id: clientId } });
  }

  getSales(): Observable<CashierOrder[]> {
    return this.http.get<CashierOrder[]>(`${this.baseUrl}/ventas`);
  }

  getPendingPayments(): Observable<CashierPendingPayment[]> {
    return this.http.get<CashierPendingPayment[]>(`${this.baseUrl}/pagos-pendientes`);
  }

  validatePayment(id: number): Observable<void> {
    return this.http.post<void>(`${this.baseUrl}/ventas/${id}/validar`, {});
  }

  rejectPayment(id: number, reason: string): Observable<void> {
    return this.http.post<void>(`${this.baseUrl}/ventas/${id}/rechazar`, { motivo: reason });
  }

  getServices(): Observable<CashierService[]> {
    return this.http.get<CashierService[]>(`${this.baseUrl}/servicios`);
  }

  createSale(data: {
    cliente_id: number | null;
    medio_pago: 'efectivo' | 'yape' | 'plin' | 'tarjeta';
    items: { producto_id?: number; servicio_id?: number; cantidad: number }[];
    clave_idempotencia: string;
    descuento?: number;
    pagos?: { medio: 'efectivo' | 'yape' | 'plin' | 'tarjeta'; monto: number }[];
    efectivo_recibido?: number;
    proceso_atencion_id?: number | null;
  }): Observable<Receipt> {
    return this.http.post<Receipt>(`${environment.apiUrl}/api/ventas`, data);
  }

  getReceipt(orderId: number): Observable<Receipt> {
    return this.http.get<Receipt>(`${this.baseUrl}/ventas/${orderId}/boleta`);
  }
}
