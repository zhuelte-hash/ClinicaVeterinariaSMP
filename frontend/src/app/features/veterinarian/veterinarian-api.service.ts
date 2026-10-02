import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AppointmentStatus } from '../appointments/appointments.models';
import { ClinicService, Pet } from '../appointments/appointments.models';
import { AppointmentSummary, AttentionStatus, ClinicalRecord, CoordinationUpdate, Diagnosis, ExamOrder, ExamPriority, ExamStatus, Notification, Prescription, ScheduleBlock, VeterinarianAppointment, VeterinarianClient, VeterinarianClientPayload, VeterinarianSchedule } from './veterinarian.models';

@Injectable({ providedIn: 'root' })
export class VeterinarianApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/portal/veterinario`;

  getRequests(date?: string, status?: AppointmentStatus, search?: string): Observable<VeterinarianAppointment[]> {
    const params: Record<string, string> = {};
    if (date) params['fecha'] = date;
    if (status) params['estado'] = status;
    if (search) params['busqueda'] = search;
    return this.http.get<VeterinarianAppointment[]>(`${this.baseUrl}/solicitudes`, { params });
  }

  updateRequest(id: number, data: CoordinationUpdate): Observable<VeterinarianAppointment> {
    return this.http.patch<VeterinarianAppointment>(`${this.baseUrl}/solicitudes/${id}`, data);
  }

  getClients(): Observable<VeterinarianClient[]> {
    return this.http.get<VeterinarianClient[]>(`${this.baseUrl}/clientes`);
  }
  getPetsForClient(clientId: number): Observable<Pet[]> { return this.http.get<Pet[]>(`${this.baseUrl}/clientes/${clientId}/mascotas`); }

  createClient(data: VeterinarianClientPayload): Observable<VeterinarianClient> {
    return this.http.post<VeterinarianClient>(`${this.baseUrl}/clientes`, data);
  }

  updateClient(id: number, data: VeterinarianClientPayload): Observable<VeterinarianClient> {
    return this.http.patch<VeterinarianClient>(`${this.baseUrl}/clientes/${id}`, data);
  }

  getSummary(): Observable<AppointmentSummary> { return this.http.get<AppointmentSummary>(`${this.baseUrl}/resumen`); }
  getSchedules(): Observable<VeterinarianSchedule[]> { return this.http.get<VeterinarianSchedule[]>(`${this.baseUrl}/horarios`); }
  createSchedule(data: { dia_semana: number; hora_inicio: string; hora_fin: string; activo: boolean }): Observable<VeterinarianSchedule> { return this.http.post<VeterinarianSchedule>(`${this.baseUrl}/horarios`, data); }
  updateSchedule(id: number, data: { dia_semana: number; hora_inicio: string; hora_fin: string; activo: boolean }): Observable<VeterinarianSchedule> { return this.http.patch<VeterinarianSchedule>(`${this.baseUrl}/horarios/${id}`, data); }
  getBlocks(): Observable<ScheduleBlock[]> { return this.http.get<ScheduleBlock[]>(`${this.baseUrl}/bloqueos`); }
  createBlock(data: { fecha_hora_inicio: string; fecha_hora_fin: string; motivo: string }): Observable<ScheduleBlock> { return this.http.post<ScheduleBlock>(`${this.baseUrl}/bloqueos`, data); }
  deleteBlock(id: number): Observable<void> { return this.http.delete<void>(`${this.baseUrl}/bloqueos/${id}`); }
  getPetHistory(id: number): Observable<ClinicalRecord[]> { return this.http.get<ClinicalRecord[]>(`${this.baseUrl}/mascotas/${id}/historial`); }
  createInitialHistory(id: number, data: Partial<ClinicalRecord>): Observable<ClinicalRecord> { return this.http.post<ClinicalRecord>(`${this.baseUrl}/mascotas/${id}/historial`, data); }
  registerAttention(id: number, data: Record<string, unknown>): Observable<ClinicalRecord> { return this.http.patch<ClinicalRecord>(`${this.baseUrl}/solicitudes/${id}/atencion`, data); }
  startAttention(id: number): Observable<ClinicalRecord> { return this.http.post<ClinicalRecord>(`${this.baseUrl}/solicitudes/${id}/atencion/iniciar`, {}); }
  updateAttentionStatus(processId: number, estado: AttentionStatus): Observable<ClinicalRecord> { return this.http.patch<ClinicalRecord>(`${this.baseUrl}/atenciones/${processId}/estado`, { estado }); }
  addDiagnosis(processId: number, data: { descripcion: string; codigo?: string; es_principal?: boolean; observaciones?: string }): Observable<Diagnosis> { return this.http.post<Diagnosis>(`${this.baseUrl}/atenciones/${processId}/diagnosticos`, data); }
  addExamOrder(processId: number, data: { tipo: string; prioridad: ExamPriority }): Observable<ExamOrder> { return this.http.post<ExamOrder>(`${this.baseUrl}/atenciones/${processId}/ordenes-examen`, data); }
  getExamOrders(processId: number): Observable<ExamOrder[]> { return this.http.get<ExamOrder[]>(`${this.baseUrl}/atenciones/${processId}/ordenes-examen`); }
  updateExamOrder(orderId: number, data: { estado: ExamStatus; resultado?: string; interpretacion?: string }): Observable<ExamOrder> { return this.http.patch<ExamOrder>(`${this.baseUrl}/ordenes-examen/${orderId}`, data); }
  savePrescription(processId: number, data: { indicaciones_generales?: string; detalles: Omit<import('./veterinarian.models').PrescriptionDetail, 'id' | 'receta_id'>[] }): Observable<Prescription> { return this.http.put<Prescription>(`${this.baseUrl}/atenciones/${processId}/receta`, data); }
  addProcedure(processId: number, data: { nombre: string; medicamentos_materiales?: { nombre: string; cantidad?: string; unidad?: string }[]; observaciones?: string }): Observable<unknown> { return this.http.post(`${this.baseUrl}/atenciones/${processId}/procedimientos`, data); }
  addPreventive(processId: number, data: { tipo: 'vacuna' | 'desparasitacion'; producto: string; lote?: string; fecha_vencimiento?: string; fecha_aplicacion?: string; proxima_fecha?: string; observaciones?: string }): Observable<unknown> { return this.http.post(`${this.baseUrl}/atenciones/${processId}/preventivos`, data); }
  getServices(): Observable<ClinicService[]> { return this.http.get<ClinicService[]>(`${this.baseUrl}/servicios`); }
  createPet(clientId: number, data: { nombre: string; especie: string; raza?: string; sexo?: string; fecha_nacimiento?: string; peso_actual?: string; caracteristicas?: string }): Observable<Pet> { return this.http.post<Pet>(`${this.baseUrl}/clientes/${clientId}/mascotas`, data); }
  startWalkIn(data: { mascota_id: number; servicio_id: number; motivo?: string; es_urgente: boolean }): Observable<VeterinarianAppointment> { return this.http.post<VeterinarianAppointment>(`${this.baseUrl}/atenciones/iniciar`, data); }
  getNotifications(): Observable<Notification[]> { return this.http.get<Notification[]>(`${environment.apiUrl}/portal/notificaciones`); }
  markNotificationRead(id: number): Observable<Notification> { return this.http.patch<Notification>(`${environment.apiUrl}/portal/notificaciones/${id}/leer`, {}); }
}
