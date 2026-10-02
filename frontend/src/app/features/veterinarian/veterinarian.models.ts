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

export interface AppointmentSummary { pendientes: number; confirmadas: number; atendidas: number; proximas: number; citas_hoy?: number; pacientes_espera?: number; atenciones_en_curso?: number; resultados_pendientes?: number; seguimientos_pendientes?: number; hospitalizados?: number; }
export interface VeterinarianSchedule { id: number; dia_semana: number; hora_inicio: string; hora_fin: string; activo: boolean; }
export interface ScheduleBlock { id: number; fecha_hora_inicio: string; fecha_hora_fin: string; motivo: string; }
export interface Notification { id: number; cita_id: number | null; tipo: string; titulo: string; mensaje: string; leida: boolean; fecha_creacion: string; }
export interface ClinicalRecord {
  id: number; cita_id: number | null; mascota_id: number; tipo: string; fecha_inicio: string; fecha_fin: string | null; estado: AttentionStatus; fecha_cierre: string | null;
  observaciones: string | null; motivo_consulta: string | null; anamnesis: string | null; diagnostico: string | null; tratamiento: string | null;
  peso: string | null; temperatura: string | null; historial_alergias: string | null;
  vacunas: string | null; desparasitaciones: string | null; medicamentos: string | null;
  procedimientos: string | null; examenes_resultados: string | null;
  proxima_fecha_control: string | null;
  veterinario_id: number; veterinario_nombre: string; servicio_nombre: string;
}

export type AttentionStatus = 'borrador' | 'en_atencion' | 'cerrada' | 'cancelada';
export type ExamPriority = 'rutina' | 'urgente' | 'emergencia';
export type ExamStatus = 'solicitado' | 'en_proceso' | 'resultado_disponible' | 'revisado' | 'cancelado';

export interface Diagnosis { id: number; proceso_id: number; descripcion: string; codigo?: string | null; es_principal: boolean; observaciones?: string | null; }
export interface ExamOrder { id: number; proceso_id: number; veterinario_id: number; tipo: string; prioridad: ExamPriority; estado: ExamStatus; resultado?: string | null; interpretacion?: string | null; revisado_por?: number | null; revisado_en?: string | null; fecha_solicitud: string; }
export interface PrescriptionDetail { id?: number; receta_id?: number; medicamento: string; presentacion?: string; dosis: string; unidad: string; via: string; frecuencia: string; duracion: string; cantidad?: string; indicaciones?: string; }
export interface Prescription { id: number; proceso_id: number; veterinario_id: number; indicaciones_generales?: string | null; fecha_emision: string; detalles: PrescriptionDetail[]; }

export interface VeterinarianClient {
  id: number;
  nombre: string;
  correo: string;
  tipo: 'cliente';
  telefono: string | null;
  direccion: string | null;
}

export interface VeterinarianClientPayload {
  nombre: string;
  correo: string;
  contrasena?: string;
  telefono: string;
  direccion: string;
}
