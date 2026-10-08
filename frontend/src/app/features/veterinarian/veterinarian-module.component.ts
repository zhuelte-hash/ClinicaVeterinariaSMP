import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import jsPDF from 'jspdf';
import { NoticeService } from '../../core/services/notice.service';
import { VeterinarianApiService } from './veterinarian-api.service';
import { AppointmentSummary, ClinicalRecord, VeterinarianAppointment } from './veterinarian.models';

type ModuleKey = 'agenda' | 'clientes' | 'mascotas' | 'consultas' | 'hospitalizacion' | 'hospedaje' | 'vacunacion' | 'desparasitacion' | 'estetica' | 'domicilio' | 'imagenes' | 'laboratorio' | 'farmacia' | 'reportes';

interface ModuleDefinition {
  eyebrow: string;
  title: string;
  description: string;
  action: string;
  empty: string;
  keywords: string[];
  metrics: string[];
  features: string[];
  categories: string[];
}

const MODULES: Record<ModuleKey, ModuleDefinition> = {
  agenda: { eyebrow: 'Agenda central', title: 'Todas las citas, un solo calendario', description: 'Consulta la programación clínica y filtra rápidamente por paciente, propietario o servicio.', action: 'Gestionar solicitudes', empty: 'No hay citas que coincidan con la búsqueda.', keywords: [], metrics: ['Citas visibles', 'Confirmadas', 'Pendientes'], features: ['Vista día, semana y mes', 'Control de cruces de horario', 'Disponibilidad de veterinario y box'], categories: ['Consulta', 'Cirugía', 'Vacuna', 'Estética', 'Laboratorio', 'Hospedaje'] },
  clientes: { eyebrow: 'Directorio clínico', title: 'Clientes y propietarios', description: 'Directorio de propietarios vinculado con sus mascotas y el historial de atención.', action: 'Nueva atención', empty: 'No hay propietarios registrados en las solicitudes disponibles.', keywords: [], metrics: ['Propietarios', 'Con teléfono', 'Pacientes vinculados'], features: ['DNI o RUC y datos de contacto', 'Dirección por ubigeo', 'Notas y valoración del cliente'], categories: ['Datos personales', 'Contacto', 'Ubicación', 'Mascotas'] },
  mascotas: { eyebrow: 'Pacientes', title: 'Historial', description: 'Consulta al propietario, sus mascotas y toda la historia clínica unificada.', action: 'Abrir historial', empty: 'No hay pacientes registrados en las solicitudes disponibles.', keywords: [], metrics: ['Pacientes', 'Caninos', 'Otras especies'], features: ['Propietario y mascotas vinculados', 'Datos de identificación del paciente', 'Línea de tiempo clínica unificada'], categories: ['Consultas', 'Cirugías', 'Vacunas', 'Estética', 'Internamientos'] },
  consultas: { eyebrow: 'Atención clínica', title: 'Mis citas y pacientes', description: 'Prioriza la jornada, abre la ficha clínica y registra atenciones sin mezclar cobros ni administración.', action: 'Iniciar atención', empty: 'No hay atenciones clínicas activas para mostrar.', keywords: ['consulta', 'cirugía', 'cirugia', 'traumatología', 'traumatologia', 'urgencia'], metrics: ['Citas de hoy', 'En espera', 'En atención', 'Resultados', 'Seguimientos'], features: ['Agenda filtrada por veterinario', 'Diagnóstico, exámenes y receta', 'Cierre clínico trazable'], categories: ['Agenda', 'Historia clínica', 'Órdenes', 'Recetas'] },
  hospitalizacion: { eyebrow: 'Cuidado continuo', title: 'Internamientos y hospitalización', description: 'Controla ocupación de boxes, evolución diaria, medicación y alta de cada paciente.', action: 'Nueva atención', empty: 'No hay internamientos vinculados con las citas actuales.', keywords: ['hospital', 'internamiento', 'internado'], metrics: ['Ingresos', 'Confirmados', 'Pendientes'], features: ['Ingreso y box asignado', 'Signos vitales y evolución diaria', 'Costo acumulado y alta médica'], categories: ['Boxes ocupados', 'Boxes disponibles', 'Altas del día'] },
  hospedaje: { eyebrow: 'Estadías', title: 'Reservas de hospedaje', description: 'Supervisa check-in, check-out, tarifa e indicaciones especiales durante la estadía.', action: 'Nueva atención', empty: 'No hay reservas de hospedaje en las citas actuales.', keywords: ['hospedaje', 'guardería', 'guarderia'], metrics: ['Reservas', 'Confirmadas', 'Por coordinar'], features: ['Reserva por rango de fechas', 'Tarifa y costo acumulado', 'Alimentación y medicación'], categories: ['Próximos ingresos', 'Hospedados', 'Check-out próximo'] },
  vacunacion: { eyebrow: 'Medicina preventiva', title: 'Vacunación y próximos refuerzos', description: 'Consulta aplicaciones registradas y próximas citas de vacunación por paciente.', action: 'Registrar desde atención', empty: 'No hay citas de vacunación en las solicitudes disponibles.', keywords: ['vacuna', 'vacunación', 'vacunacion'], metrics: ['Registros', 'Confirmadas', 'Pendientes'], features: ['Producto, lote, peso y precio', 'Programación del próximo refuerzo', 'Delivery y cartilla imprimible'], categories: ['Aplicadas', 'Programadas', 'Vencidas', 'Delivery'] },
  desparasitacion: { eyebrow: 'Medicina preventiva', title: 'Desparasitación interna y externa', description: 'Mantén visible el historial preventivo y programa la siguiente aplicación.', action: 'Registrar desde atención', empty: 'No hay desparasitaciones en las solicitudes disponibles.', keywords: ['desparasitación', 'desparasitacion', 'antiparasitario'], metrics: ['Registros', 'Confirmadas', 'Pendientes'], features: ['Producto, dosis, peso y precio', 'Historial por paciente', 'Programación, delivery e impresión'], categories: ['Interna', 'Externa', 'Programadas', 'Delivery'] },
  estetica: { eyebrow: 'Bienestar', title: 'Baño, peluquería y estética', description: 'Organiza servicios combinables y revisa las atenciones efectuadas o programadas.', action: 'Gestionar solicitudes', empty: 'No hay servicios estéticos en las solicitudes disponibles.', keywords: ['baño', 'bano', 'peluquería', 'peluqueria', 'estética', 'estetica', 'uñas'], metrics: ['Servicios', 'Confirmados', 'Pendientes'], features: ['Servicios combinables', 'Catálogo con precios', 'Efectuados y programados'], categories: ['Baño estético', 'Baño medicado', 'Corte', 'Uñas y oídos', 'Antipulgas'] },
  domicilio: { eyebrow: 'Atención móvil', title: 'Servicios a domicilio', description: 'Identifica atenciones fuera de clínica, dirección, traslado y personal asignado.', action: 'Gestionar solicitudes', empty: 'No hay atenciones a domicilio en las solicitudes actuales.', keywords: ['domicilio', 'delivery'], metrics: ['Servicios', 'Confirmados', 'Por coordinar'], features: ['Disponible en cualquier atención', 'Dirección y costo de traslado', 'Personal y horario asignados'], categories: ['Programadas', 'En ruta', 'Completadas'] },
  imagenes: { eyebrow: 'Diagnóstico por imágenes', title: 'Ecografías y rayos X', description: 'Centraliza estudios médicos asociados al historial clínico de cada mascota.', action: 'Abrir atención', empty: 'No hay estudios de imágenes en las solicitudes disponibles.', keywords: ['ecografía', 'ecografia', 'rayos', 'radiografía', 'radiografia'], metrics: ['Estudios', 'Confirmados', 'Pendientes'], features: ['Galería y subida múltiple', 'Estudio, hallazgos y diagnóstico', 'Visor con zoom por tipo'], categories: ['Ecografía', 'Rayos X', 'Otros estudios'] },
  laboratorio: { eyebrow: 'Diagnóstico clínico', title: 'Laboratorio y resultados', description: 'Organiza solicitudes y resultados de laboratorio asociados al paciente.', action: 'Abrir atención', empty: 'No hay análisis de laboratorio en las solicitudes disponibles.', keywords: ['laboratorio', 'hematología', 'hematologia', 'urianálisis', 'bioquímica', 'citología', 'parasitología', 'hisopado', 'raspado'], metrics: ['Análisis', 'Confirmados', 'Pendientes'], features: ['Resultados, unidades y referencia', 'Alertas automáticas de valores anormales', 'Informe PDF con identidad de la clínica'], categories: ['Hematología', 'Urianálisis', 'Bioquímica', 'Citología', 'Parasitología', 'Hisopado', 'Raspado'] },
  farmacia: { eyebrow: 'Control interno', title: 'Farmacia e inventario clínico', description: 'Consulta el alcance del control interno asociado a tratamientos y atenciones.', action: 'Abrir atención', empty: 'No hay salidas de farmacia vinculadas con las solicitudes actuales.', keywords: ['farmacia', 'medicamento', 'alimento', 'insumo'], metrics: ['Movimientos', 'Atenciones', 'Alertas'], features: ['Medicamentos, alimentos e insumos', 'Stock mínimo y vencimiento', 'Salida automática al recetar'], categories: ['Stock crítico', 'Próximos a vencer', 'Salidas clínicas'] },
  reportes: { eyebrow: 'Análisis interno', title: 'Indicadores clínicos', description: 'Resumen operativo calculado a partir de las solicitudes visibles del veterinario.', action: 'Ver agenda', empty: 'Aún no hay datos suficientes para generar indicadores.', keywords: [], metrics: ['Atenciones', 'Servicios distintos', 'Pacientes'], features: ['Atenciones por veterinario', 'Servicios más solicitados', 'Preventivos vencidos y stock crítico'], categories: ['Actividad clínica', 'Estética', 'Farmacia', 'Prevención'] },
};

@Component({
  selector: 'app-veterinarian-module',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './veterinarian-module.component.html',
  styleUrl: './veterinarian-module.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class VeterinarianModuleComponent {
  private readonly api = inject(VeterinarianApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly notice = inject(NoticeService);
  private readonly routeData = toSignal(this.route.data, { initialValue: this.route.snapshot.data });

  readonly loading = signal(true);
  readonly errorMessage = signal('');
  readonly search = signal('');
  readonly appointments = signal<VeterinarianAppointment[]>([]);
  readonly summary = signal<AppointmentSummary>({ pendientes: 0, confirmadas: 0, atendidas: 0, proximas: 0 });
  readonly selectedAppointment = signal<number | null>(null);
  readonly historyPetId = signal<number | null>(null);
  readonly history = signal<ClinicalRecord[]>([]);
  readonly savingId = signal<number | null>(null);
  readonly attentionForm = { motivo_consulta: '', anamnesis: '', observaciones: '', diagnostico: '', tratamiento: '', peso: '', temperatura: '', historial_alergias: '', vacunas: '', desparasitaciones: '', medicamentos: '', procedimientos: '', examenes_resultados: '', proxima_fecha_control: '' };
  readonly moduleKey = computed(() => (this.routeData()['module'] || 'agenda') as ModuleKey);
  readonly definition = computed(() => MODULES[this.moduleKey()]);
  readonly filteredAppointments = computed(() => {
    const definition = this.definition();
    const query = this.search().trim().toLocaleLowerCase('es');
    return this.appointments().filter((appointment) => {
      const service = appointment.servicio.nombre.toLocaleLowerCase('es');
      const moduleMatch = definition.keywords.length === 0 || definition.keywords.some((keyword) => service.includes(keyword));
      const text = `${appointment.mascota.nombre} ${appointment.cliente_nombre} ${appointment.servicio.nombre}`.toLocaleLowerCase('es');
      return moduleMatch && (!query || text.includes(query));
    });
  });
  readonly firstAvailableAppointment = computed(() => this.filteredAppointments().find((item) => item.estado === 'confirmada' || item.estado === 'reprogramada'));
  readonly uniqueClients = computed(() => new Set(this.filteredAppointments().map((item) => item.cliente_id)).size);
  readonly uniquePets = computed(() => new Set(this.filteredAppointments().map((item) => item.mascota.id)).size);
  readonly uniqueServices = computed(() => new Set(this.filteredAppointments().map((item) => item.servicio.id)).size);
  readonly metricValues = computed(() => {
    const items = this.filteredAppointments();
    if (this.moduleKey() === 'consultas') {
      const summary = this.summary();
      return [summary.citas_hoy ?? items.length, summary.pacientes_espera ?? 0, summary.atenciones_en_curso ?? 0, summary.resultados_pendientes ?? 0, summary.seguimientos_pendientes ?? 0];
    }
    if (this.moduleKey() === 'clientes') return [this.uniqueClients(), items.filter((item) => !!item.telefono_contacto).length, this.uniquePets()];
    if (this.moduleKey() === 'mascotas') return [this.uniquePets(), new Set(items.filter((item) => item.mascota.especie.toLowerCase().includes('can')).map((item) => item.mascota.id)).size, new Set(items.filter((item) => !item.mascota.especie.toLowerCase().includes('can')).map((item) => item.mascota.id)).size];
    if (this.moduleKey() === 'reportes') return [items.filter((item) => item.estado === 'atendida').length, this.uniqueServices(), this.uniquePets()];
    return [items.length, items.filter((item) => item.estado === 'confirmada' || item.estado === 'atendida').length, items.filter((item) => item.estado !== 'confirmada' && item.estado !== 'atendida' && item.estado !== 'cancelada').length];
  });

  constructor() {
    this.api.getRequests().pipe(finalize(() => this.loading.set(false))).subscribe({
      next: (appointments) => this.appointments.set(appointments),
      error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
    this.api.getSummary().subscribe({ next: (summary) => this.summary.set(summary), error: (error: unknown) => this.errorMessage.set(this.errorText(error)) });
  }

  setSearch(value: string): void { this.search.set(value); }

  startAttention(appointment: VeterinarianAppointment): void {
    void this.router.navigate(['/veterinario/atencion', appointment.id]);
  }

  registerArrival(appointment: VeterinarianAppointment): void {
    this.api.registerArrival(appointment.id).subscribe({
      next: (updated) => {
        this.appointments.update((items) => items.map((item) => item.id === updated.id ? updated : item));
        this.notice.show('Llegada registrada');
      },
      error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
  }

  confirmAppointment(appointment: VeterinarianAppointment): void {
    this.api.updateRequest(appointment.id, { estado: 'confirmada' }).subscribe({
      next: (updated) => {
        this.appointments.update((items) => items.map((item) => item.id === updated.id ? updated : item));
        this.notice.show('Cita confirmada');
      },
      error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
  }

  cancelAttention(): void { this.selectedAppointment.set(null); this.resetAttention(); }

  registerAttention(appointment: VeterinarianAppointment): void {
    this.savingId.set(appointment.id);
    const payload = Object.fromEntries(Object.entries(this.attentionForm).map(([key, value]) => [key, value || null]));
    this.api.registerAttention(appointment.id, payload).pipe(finalize(() => this.savingId.set(null))).subscribe({
      next: () => { this.selectedAppointment.set(null); this.resetAttention(); this.notice.show('Atención registrada en el historial clínico'); this.reload(); },
      error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
  }

  showHistory(appointment: VeterinarianAppointment): void {
    void this.router.navigate(['/veterinario/mascota', appointment.mascota.id]);
  }

  sendHistory(appointment: VeterinarianAppointment, channel: 'whatsapp' | 'correo'): void {
    if (channel === 'whatsapp') {
      void this.downloadHistoryPdf(appointment);
      return;
    }
    this.api.getPetHistory(appointment.mascota.id).subscribe({
      next: (records) => {
        const summary = records.map((record) => `${record.servicio_nombre}: ${record.diagnostico || 'Atención registrada'}`).join(' | ');
        const message = `Historial clínico de ${appointment.mascota.nombre}. ${summary || 'Sin atenciones registradas.'}`;
        if (channel === 'correo') {
          window.location.href = `mailto:${appointment.cliente_correo}?subject=${encodeURIComponent(`Historial de ${appointment.mascota.nombre}`)}&body=${encodeURIComponent(message)}`;
        }
      },
      error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
  }

  async downloadHistoryPdf(appointment: VeterinarianAppointment): Promise<void> {
    this.api.getPetHistory(appointment.mascota.id).subscribe({
      next: async (records) => {
        const pdf = new jsPDF();
        const logo = await this.loadImage('/logo.png');
        const pageWidth = pdf.internal.pageSize.getWidth();
        let y = 18;

        if (logo) pdf.addImage(logo, 'PNG', 16, 12, 28, 28);
        pdf.setTextColor(16, 43, 53);
        pdf.setFontSize(18);
        pdf.setFont('helvetica', 'bold');
        pdf.text('CLINICA VETERINARIA SAN MARTIN DE PORRES', 50, 23);
        pdf.setFontSize(10);
        pdf.setFont('helvetica', 'normal');
        pdf.text('Historial clinico veterinario', 50, 30);
        pdf.setDrawColor(22, 139, 131);
        pdf.line(16, 46, pageWidth - 16, 46);
        y = 58;

        pdf.setFontSize(12);
        pdf.setFont('helvetica', 'bold');
        pdf.text('Datos del paciente', 16, y);
        y += 8;
        pdf.setFontSize(10);
        pdf.setFont('helvetica', 'normal');
        pdf.text(`Mascota: ${appointment.mascota.nombre}`, 16, y);
        pdf.text(`Especie: ${appointment.mascota.especie}`, 105, y);
        y += 6;
        pdf.text(`Raza: ${appointment.mascota.raza || 'No registrada'}`, 16, y);
        pdf.text(`Propietario: ${appointment.cliente_nombre}`, 105, y);
        y += 6;
        pdf.text(`Correo: ${appointment.cliente_correo}`, 16, y);
        pdf.text(`Telefono: ${appointment.telefono_contacto || 'No registrado'}`, 105, y);
        y += 14;

        pdf.setFontSize(12);
        pdf.setFont('helvetica', 'bold');
        pdf.text(`Atenciones registradas (${records.length})`, 16, y);
        y += 9;

        const fields: Array<[string, keyof ClinicalRecord]> = [
          ['Motivo de consulta', 'motivo_consulta'], ['Anamnesis', 'anamnesis'],
          ['Observaciones', 'observaciones'], ['Diagnostico', 'diagnostico'],
          ['Tratamiento', 'tratamiento'], ['Peso (kg)', 'peso'],
          ['Temperatura (C)', 'temperatura'], ['Alergias', 'historial_alergias'],
          ['Vacunas', 'vacunas'], ['Desparasitaciones', 'desparasitaciones'],
          ['Medicamentos', 'medicamentos'], ['Procedimientos', 'procedimientos'],
          ['Examenes y resultados', 'examenes_resultados'], ['Proximo control', 'proxima_fecha_control'],
        ];

        records.forEach((record, index) => {
          if (y > 260) { pdf.addPage(); y = 18; }
          pdf.setFillColor(234, 249, 246);
          pdf.rect(16, y - 5, pageWidth - 32, 10, 'F');
          pdf.setTextColor(16, 43, 53);
          pdf.setFontSize(11);
          pdf.setFont('helvetica', 'bold');
          pdf.text(`${index + 1}. ${record.servicio_nombre} · ${this.formatDate(record.fecha_inicio)}`, 20, y + 2);
          y += 12;
          pdf.setFontSize(9);
          pdf.setFont('helvetica', 'normal');
          pdf.setTextColor(60, 70, 75);
          for (const [label, key] of fields) {
            const value = record[key];
            if (value === null || value === undefined || value === '') continue;
            const lines = pdf.splitTextToSize(`${label}: ${String(value)}`, pageWidth - 40);
            if (y + lines.length * 5 > 280) { pdf.addPage(); y = 18; }
            pdf.text(lines, 20, y);
            y += lines.length * 5 + 2;
          }
          pdf.text(`Veterinario: ${record.veterinario_nombre || 'Sin asignar'}`, 20, y);
          y += 10;
        });

        pdf.setFontSize(8);
        pdf.setTextColor(110, 110, 110);
        pdf.text('Documento generado por la Clinica Veterinaria San Martin de Porres', 16, 290);
        pdf.save(`historial-${appointment.mascota.nombre.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.pdf`);
      },
      error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
  }

  private async loadImage(url: string): Promise<string | null> {
    try {
      const response = await fetch(url);
      const blob = await response.blob();
      return await new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = () => resolve(typeof reader.result === 'string' ? reader.result : null);
        reader.onerror = () => resolve(null);
        reader.readAsDataURL(blob);
      });
    } catch {
      return null;
    }
  }

  resetAttention(): void { Object.assign(this.attentionForm, { motivo_consulta: '', anamnesis: '', observaciones: '', diagnostico: '', tratamiento: '', peso: '', temperatura: '', historial_alergias: '', vacunas: '', desparasitaciones: '', medicamentos: '', procedimientos: '', examenes_resultados: '', proxima_fecha_control: '' }); }

  private reload(): void { this.api.getRequests().subscribe({ next: (appointments) => this.appointments.set(appointments), error: (error: unknown) => this.errorMessage.set(this.errorText(error)) }); }

  formatDate(value: string): string {
    return new Intl.DateTimeFormat('es-PE', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Lima' }).format(new Date(value));
  }

  statusLabel(status: string): string {
    const labels: Record<string, string> = { pendiente_contacto: 'Pendiente de confirmación', contactando_cliente: 'Contactando', esperando_respuesta: 'Esperando respuesta', requiere_otro_horario: 'Reprogramar', confirmada: 'Confirmada', cancelada: 'Cancelada', cliente_no_respondio: 'Sin respuesta', no_asistio: 'Cancelada por inasistencia', atendida: 'Atendida', reprogramada: 'Reprogramada' };
    return labels[status] || status;
  }

  private errorText(error: unknown): string {
    if (error instanceof HttpErrorResponse && typeof error.error?.detail === 'string') return error.error.detail;
    return 'No se pudo cargar la información clínica.';
  }
}
