import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AppointmentStatus } from '../appointments/appointments.models';
import { ClinicService, Pet } from '../appointments/appointments.models';
import { AppointmentSummary, ClinicalRecord, CoordinationUpdate, Notification, ScheduleBlock, VeterinarianAppointment, VeterinarianClient, VeterinarianClientPayload, VeterinarianSchedule } from './veterinarian.models';

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
  registerAttention(id: number, data: Partial<ClinicalRecord>): Observable<ClinicalRecord> { return this.http.patch<ClinicalRecord>(`${this.baseUrl}/solicitudes/${id}/atencion`, data); }
  getServices(): Observable<ClinicService[]> { return this.http.get<ClinicService[]>(`${this.baseUrl}/servicios`); }
  createPet(clientId: number, data: { nombre: string; especie: string; raza?: string; sexo?: string; fecha_nacimiento?: string; peso_actual?: string; caracteristicas?: string }): Observable<Pet> { return this.http.post<Pet>(`${this.baseUrl}/clientes/${clientId}/mascotas`, data); }
  startWalkIn(data: { mascota_id: number; servicio_id: number; motivo?: string; es_urgente: boolean }): Observable<VeterinarianAppointment> { return this.http.post<VeterinarianAppointment>(`${this.baseUrl}/atenciones/iniciar`, data); }
  getNotifications(): Observable<Notification[]> { return this.http.get<Notification[]>(`${environment.apiUrl}/portal/notificaciones`); }
  markNotificationRead(id: number): Observable<Notification> { return this.http.patch<Notification>(`${environment.apiUrl}/portal/notificaciones/${id}/leer`, {}); }
}
