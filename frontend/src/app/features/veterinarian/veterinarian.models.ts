import { Appointment, AppointmentStatus } from '../appointments/appointments.models';

export interface VeterinarianAppointment extends Appointment {
  cliente_id: number;
  cliente_nombre: string;
  cliente_correo: string;
}

export interface CoordinationUpdate {
  estado: AppointmentStatus;
  fecha_hora_propuesta?: string;
  nota_coordinacion?: string;
}

export interface AppointmentSummary { pendientes: number; confirmadas: number; atendidas: number; proximas: number; }
export interface VeterinarianSchedule { id: number; dia_semana: number; hora_inicio: string; hora_fin: string; activo: boolean; }
export interface ScheduleBlock { id: number; fecha_hora_inicio: string; fecha_hora_fin: string; motivo: string; }
export interface Notification { id: number; cita_id: number | null; tipo: string; titulo: string; mensaje: string; leida: boolean; fecha_creacion: string; }
export interface ClinicalRecord {
  id: number; cita_id: number | null; mascota_id: number; tipo: string; fecha_inicio: string; fecha_fin: string | null;
  observaciones: string | null; motivo_consulta: string | null; anamnesis: string | null; diagnostico: string | null; tratamiento: string | null;
  peso: string | null; temperatura: string | null; historial_alergias: string | null;
  vacunas: string | null; desparasitaciones: string | null; medicamentos: string | null;
  procedimientos: string | null; examenes_resultados: string | null;
  proxima_fecha_control: string | null;
  veterinario_id: number; veterinario_nombre: string; servicio_nombre: string;
}
