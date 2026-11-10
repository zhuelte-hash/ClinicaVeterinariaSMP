import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { environment } from '../../../environments/environment';
import { DatosCliente } from '../models/purchase.model';
import { PurchaseConfig } from '../config/purchase.config';

export interface WebOrder {
  id: number;
  codigo_pedido: string;
  fecha_pedido: string;
  cliente_id: number;
  datos_cliente: DatosCliente;
  subtotal: string;
  descuento: string;
  costo_delivery: string;
  total: string;
  metodo_pago: string;
  estado_pedido: 'PENDIENTE' | 'APROBADO' | 'RECHAZADO' | 'CANCELADO';
  estado_pago: string;
  numero_operacion: string;
  observaciones: string;
  comprobante_pago: string;
  comprobante_tipo: string;
  motivo_rechazo: string | null;
  usuario_revisor_id: number | null;
  fecha_revision: string | null;
  venta_id: number | null;
  detalles: { producto_id: number; nombre_producto: string; imagen_url: string; cantidad: number; precio_unitario: string; subtotal: string }[];
}

export interface CreateWebOrder {
  clave_idempotencia: string;
  cliente: DatosCliente;
  items: { producto_id: number; cantidad: number }[];
  metodo_pago: string;
  numero_operacion: string;
  observaciones: string;
  total_esperado: string;
}

/** Conserva el nombre para los consumidores existentes; la fuente de verdad es la API. */
@Injectable({ providedIn: 'root' })
export class LocalPurchaseService {
  private readonly http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/pedidos-web`;

  configuration() { return this.http.get<PurchaseConfig>(`${this.url}/configuracion`); }
  create(data: CreateWebOrder, proof: File) {
    const body = new FormData();
    body.append('datos', JSON.stringify(data));
    body.append('comprobante', proof);
    return this.http.post<WebOrder>(this.url, body);
  }
  list(filters: Record<string, string | number> = {}) {
    let params = new HttpParams();
    for (const [key, value] of Object.entries(filters)) if (value !== '') params = params.set(key, value);
    return this.http.get<WebOrder[]>(this.url, { params });
  }
  get(id: number) { return this.http.get<WebOrder>(`${this.url}/${id}`); }
  proof(id: number) { return this.http.get(`${this.url}/${id}/comprobante`, { responseType: 'blob' }); }
  review(id: number, accion: 'APROBAR' | 'RECHAZAR', motivo = '') {
    return this.http.post<WebOrder>(`${this.url}/${id}/revision`, { accion, motivo });
  }
}
