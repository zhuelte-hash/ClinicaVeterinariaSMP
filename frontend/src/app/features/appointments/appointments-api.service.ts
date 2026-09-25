import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Appointment, ClinicService, Pet } from './appointments.models';

@Injectable({ providedIn: 'root' })
export class AppointmentsApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/portal`;

  getPets(): Observable<Pet[]> {
    return this.http.get<Pet[]>(`${this.baseUrl}/mascotas`);
  }

  createPet(data: { nombre: string; especie: string; raza?: string }): Observable<Pet> {
    return this.http.post<Pet>(`${this.baseUrl}/mascotas`, data);
  }

  getServices(): Observable<ClinicService[]> {
    return this.http.get<ClinicService[]>(`${this.baseUrl}/servicios`);
  }

  getAppointments(): Observable<Appointment[]> {
    return this.http.get<Appointment[]>(`${this.baseUrl}/citas`);
  }

  createAppointment(data: {
    mascota_id: number;
    servicio_id: number;
    fecha_hora_programada: string;
    motivo?: string;
    es_urgente: boolean;
  }): Observable<Appointment> {
    return this.http.post<Appointment>(`${this.baseUrl}/citas`, data);
  }

  cancelAppointment(id: number): Observable<Appointment> {
    return this.http.patch<Appointment>(`${this.baseUrl}/citas/${id}/cancelar`, {});
  }
}
