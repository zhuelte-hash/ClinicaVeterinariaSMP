import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { environment } from '../../../../environments/environment';

export type Numeric = number | string;
export interface Ranking { id: number; nombre: string; cantidad: Numeric; }
export interface OperationsDashboard {
  desde: string; hasta: string; ventas: Numeric; cantidad_ventas: number; citas_por_estado: Record<string, number>;
  ordenes_pendientes: number; saldo_pendiente: Numeric; pagos_web_por_validar: number; pagos_por_validar: number;
  stock_bajo: { id: number; nombre: string; stock: Numeric; minimo: Numeric }[];
  productos_mas_vendidos: Ranking[]; servicios_mas_solicitados: Ranking[]; servicios_mas_atendidos: Ranking[];
  finanzas: { cobros: Numeric; egresos: Numeric; resultado: Numeric; criterio: string };
}
export interface Unit { codigo: string; nombre: string; dimension: 'conteo' | 'masa' | 'volumen'; factor_base: Numeric; fraccionable: boolean; }
export interface Lot { id: number; producto_id: number; producto_nombre: string; codigo: string; cantidad: Numeric; costo_unitario: Numeric; vencimiento: string | null; }
export interface PurchaseLine { producto_id: number; cantidad: number; costo_unitario: number; lote: string; vencimiento: string | null; unidad: string | null; }
export interface PurchaseReceipt { id: number; documento: string; proveedor_id: number; proveedor_nombre: string; usuario_nombre: string; fecha: string; total: Numeric; detalles: PurchaseLine[]; }
export interface Expense { id: number; categoria: string; concepto: string; monto: Numeric; fecha: string; }
export interface AuditEvent { id: number; autor: string; usuario_id: number | null; entidad: string; registro_id: string; accion: string; fecha: string; cambios: Record<string, { antes: unknown; despues: unknown }>; }
export interface Schedule { id: number; veterinario_id: number; dia_semana: number; hora_inicio: string; hora_fin: string; activo: boolean; }
export type MedicalKind = 'consulta_general' | 'cirugia' | 'vacunacion' | 'desparasitacion' | 'laboratorio_e_imagen';
export interface ManagedService { id: number; codigo: string; nombre: string; descripcion: string; precio_referencial: Numeric; duracion_estimada_min: number; activo: boolean; tipo: 'medica' | 'estetica'; tipo_medico: MedicalKind | null; }
export type ServiceWrite = Omit<ManagedService, 'id' | 'tipo_medico'> & { tipo_medico: MedicalKind };
export interface Reschedule { id: number; cita_id: number; cliente_id: number; fecha_propuesta: string; motivo: string; canal: string; estado: string; }
export function operationError(error: unknown): string {
  const detail = (error as { error?: { detail?: unknown } })?.error?.detail;
  if (Array.isArray(detail)) return detail.map(item => typeof item?.msg === 'string' ? item.msg.replace(/^Value error, /, '') : '').filter(Boolean).join(' · ') || 'Revisa los datos del formulario.';
  return typeof detail === 'string' ? detail : 'No se pudo completar la operación. Revisa los datos e intenta nuevamente.';
}
@Injectable({ providedIn: 'root' })
export class OperationsApiService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/admin/operaciones`;
  dashboard(desde: string, hasta: string) { return this.http.get<OperationsDashboard>(`${this.base}/dashboard`, { params: { desde, hasta } }); }
  units() { return this.http.get<Unit[]>(`${this.base}/unidades`); }
  productUnits() { return this.http.get<Unit[]>(`${environment.apiUrl}/admin/productos/unidades`); }
  suppliers() { return this.http.get<{ id: number; razon_social: string }[]>(`${this.base}/proveedores`); }
  services() { return this.http.get<ManagedService[]>(`${this.base}/servicios`); }
  saveService(data: ServiceWrite, id?: number) { return id ? this.http.put(`${this.base}/servicios/${id}`, data) : this.http.post(`${this.base}/servicios`, data); }
  createUnit(data: Unit) { return this.http.post<Unit>(`${this.base}/unidades`, data); }
  lots(expiring = false) { return this.http.get<Lot[]>(`${this.base}/lotes`, { params: { por_vencer: expiring } }); }
  receipts() { return this.http.get<PurchaseReceipt[]>(`${this.base}/compras`); }
  receive(data: { proveedor_id: number; documento: string; detalles: PurchaseLine[] }) { return this.http.post<PurchaseReceipt>(`${this.base}/compras`, data); }
  expenses(desde: string, hasta: string) { return this.http.get<Expense[]>(`${this.base}/egresos`, { params: { desde, hasta } }); }
  recordExpense(data: Omit<Expense, 'id'>) { return this.http.post<Expense>(`${this.base}/egresos`, data); }
  audit(params: Record<string, string>) { return this.http.get<AuditEvent[]>(`${this.base}/auditoria`, { params }); }
  schedules(vet: number) { return this.http.get<Schedule[]>(`${this.base}/horarios/${vet}`); }
  saveSchedule(vet: number, data: Omit<Schedule, 'id' | 'veterinario_id'>, id?: number) {
    return id ? this.http.put<Schedule>(`${this.base}/horarios/${vet}/${id}`, data) : this.http.post<Schedule>(`${this.base}/horarios/${vet}`, data);
  }
  requests() { return this.http.get<Reschedule[]>(`${this.base}/reprogramaciones`); }
  resolve(id: number, aceptar: boolean, motivo: string) { return this.http.post<Reschedule>(`${this.base}/reprogramaciones/${id}/resolver`, { aceptar, motivo }); }
}
