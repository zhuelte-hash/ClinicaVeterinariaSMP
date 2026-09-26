import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Appointment, AvailabilitySlot, ClinicalRecord, ClinicService, Pet } from './appointments.models';

@Injectable({ providedIn: 'root' })
export class AppointmentsApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/portal`;

  getPets(): Observable<Pet[]> {
    return this.http.get<Pet[]>(`${this.baseUrl}/mascotas`);
  }

  createPet(data: { nombre: string; especie: string; raza?: string; sexo?: string; fecha_nacimiento?: string; peso_actual?: string; caracteristicas?: string }): Observable<Pet> {
    return this.http.post<Pet>(`${this.baseUrl}/mascotas`, data);
  }

  getServices(): Observable<ClinicService[]> {
    return this.http.get<ClinicService[]>(`${this.baseUrl}/servicios`);
  }

  getAvailability(serviceId: number, date: string): Observable<AvailabilitySlot[]> {
    return this.http.get<AvailabilitySlot[]>(`${this.baseUrl}/disponibilidad`, {
      params: { servicio_id: serviceId, fecha: date },
    });
  }

  getAppointments(): Observable<Appointment[]> {
    return this.http.get<Appointment[]>(`${this.baseUrl}/citas`);
  }

  createAppointment(data: {
    mascota_id: number;
    servicio_id: number;
    veterinario_id: number;
    fecha_hora_programada: string;
    motivo?: string;
    es_urgente: boolean;
    telefono_contacto?: string;
    preferencia_contacto?: string;
  }): Observable<Appointment> {
    return this.http.post<Appointment>(`${this.baseUrl}/citas`, data);
  }

  cancelAppointment(id: number): Observable<Appointment> {
    return this.http.patch<Appointment>(`${this.baseUrl}/citas/${id}/cancelar`, {});
  }

  acceptProposedTime(id: number): Observable<Appointment> {
    return this.http.patch<Appointment>(`${this.baseUrl}/citas/${id}/aceptar-horario`, {});
  }

  getPetHistory(petId: number): Observable<ClinicalRecord[]> {
    return this.http.get<ClinicalRecord[]>(`${this.baseUrl}/mascotas/${petId}/historial`);
  }
}
