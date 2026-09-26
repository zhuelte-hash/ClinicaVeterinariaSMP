export interface Pet {
  id: number;
  nombre: string;
  especie: string;
  raza: string | null;
  sexo?: string | null;
  fecha_nacimiento?: string | null;
  peso_actual?: string | null;
  caracteristicas?: string | null;
}

export interface ClinicService {
  id: number;
  codigo: string;
  nombre: string;
  descripcion: string | null;
  precio_referencial: string;
  duracion_estimada_min: number;
}

export type AppointmentStatus =
  | 'pendiente' | 'pendiente_contacto' | 'contactando_cliente'
  | 'esperando_respuesta' | 'requiere_otro_horario' | 'confirmada'
  | 'reprogramada' | 'atendida' | 'cancelada' | 'cliente_no_respondio' | 'no_asistio';

export interface Appointment {
  id: number;
  fecha_hora_programada: string;
  estado: AppointmentStatus;
  es_urgente: boolean;
  motivo: string | null;
  fecha_creacion: string;
  fecha_actualizacion: string;
  fecha_hora_propuesta: string | null;
  telefono_contacto: string | null;
  preferencia_contacto: string | null;
  nota_coordinacion: string | null;
  veterinario_id: number | null;
  mascota: Pet;
  servicio: ClinicService;
}

export interface ClinicalRecord {
  id: number;
  cita_id: number | null;
  mascota_id: number;
  tipo: string;
  fecha_inicio: string;
  fecha_fin: string | null;
  observaciones: string | null;
  motivo_consulta: string | null;
  anamnesis: string | null;
  diagnostico: string | null;
  tratamiento: string | null;
  peso: string | null;
  temperatura: string | null;
  historial_alergias: string | null;
  vacunas: string | null;
  desparasitaciones: string | null;
  medicamentos: string | null;
  procedimientos: string | null;
  examenes_resultados: string | null;
  proxima_fecha_control: string | null;
  veterinario_id: number;
  veterinario_nombre: string;
  servicio_nombre: string;
}

export interface AvailabilitySlot {
  fecha_hora: string;
  veterinario_id: number;
  veterinario_nombre: string;
}
