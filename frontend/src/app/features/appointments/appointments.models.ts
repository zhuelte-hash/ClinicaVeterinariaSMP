export interface Pet {
  id: number;
  nombre: string;
  especie: string;
  raza: string | null;
}

export interface ClinicService {
  id: number;
  codigo: string;
  nombre: string;
  descripcion: string | null;
  precio_referencial: string;
  duracion_estimada_min: number;
}

export type AppointmentStatus = 'pendiente' | 'confirmada' | 'reprogramada' | 'atendida' | 'cancelada' | 'no_asistio';

export interface Appointment {
  id: number;
  fecha_hora_programada: string;
  estado: AppointmentStatus;
  es_urgente: boolean;
  motivo: string | null;
  fecha_creacion: string;
  mascota: Pet;
  servicio: ClinicService;
}
