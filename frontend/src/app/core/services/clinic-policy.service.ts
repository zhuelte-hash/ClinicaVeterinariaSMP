import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';

export interface DayHours { dia: number; cerrado: boolean; inicio: string; fin: string; descanso_inicio: string | null; descanso_fin: string | null; }
export interface ExceptionHours extends DayHours { fecha: string; motivo: string; }
export interface ClinicPolicy { horarios: DayHours[]; excepciones: ExceptionHours[]; galeria: { url: string; titulo: string }[]; horas_cancelacion: number; horas_reprogramacion: number; dias_alerta_vencimiento: number; dias_recordatorio_vacuna: number; }
export const WEEKDAYS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
export function hoursLabel(day: DayHours): string {
  if (day.cerrado) return 'Cerrado';
  const time = (value: string) => value.slice(0, 5);
  return day.descanso_inicio && day.descanso_fin
    ? `${time(day.inicio)}–${time(day.descanso_inicio)} y ${time(day.descanso_fin)}–${time(day.fin)}`
    : `${time(day.inicio)}–${time(day.fin)}`;
}
@Injectable({ providedIn: 'root' })
export class ClinicPolicyService {
  private readonly http = inject(HttpClient);
  get() { return this.http.get<ClinicPolicy>(`${environment.apiUrl}/publico/institucional`); }
  save(policy: ClinicPolicy) { return this.http.put<ClinicPolicy>(`${environment.apiUrl}/admin/operaciones/configuracion`, policy); }
  saveHours(hours: Pick<ClinicPolicy, 'horarios' | 'excepciones'>) { return this.http.put<ClinicPolicy>(`${environment.apiUrl}/admin/operaciones/horario-clinica`, hours); }
}
