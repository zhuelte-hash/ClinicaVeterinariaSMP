import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  CashierCategory,
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

  closeRegister(): Observable<CashRegister> {
    return this.http.post<CashRegister>(`${this.baseUrl}/cerrar`, {});
  }

  getCategories(): Observable<CashierCategory[]> {
    return this.http.get<CashierCategory[]>(`${this.baseUrl}/categorias`);
  }

  getProducts(): Observable<CashierProduct[]> {
    return this.http.get<CashierProduct[]>(`${this.baseUrl}/productos`);
  }

  getClients(): Observable<CashierClient[]> {
    return this.http.get<CashierClient[]>(`${this.baseUrl}/clientes`);
  }

  getServices(): Observable<CashierService[]> {
    return this.http.get<CashierService[]>(`${this.baseUrl}/servicios`);
  }

  createSale(data: {
    cliente_id: number;
    medio_pago: 'efectivo' | 'yape' | 'plin' | 'tarjeta';
    items: { producto_id?: number; servicio_id?: number; cantidad: number }[];
  }): Observable<Receipt> {
    return this.http.post<Receipt>(`${this.baseUrl}/ventas`, data);
  }

  getReceipt(orderId: number): Observable<Receipt> {
    return this.http.get<Receipt>(`${this.baseUrl}/ventas/${orderId}/boleta`);
  }
}
