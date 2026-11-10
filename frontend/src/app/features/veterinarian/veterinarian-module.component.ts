import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize, forkJoin } from 'rxjs';
import { NoticeService } from '../../core/services/notice.service';
import { VeterinarianApiService } from './veterinarian-api.service';
import { AppointmentSummary, ClinicalRecord, VeterinarianAppointment, VeterinarianClinicalRecord } from './veterinarian.models';
import { clinicalDate, clinicalSearch, VeterinarianIconComponent, VeterinarianPaginationComponent, VeterinarianStatusComponent, VeterinarianTableState } from './veterinarian-table';

type HistorySubject = Pick<VeterinarianAppointment, 'mascota' | 'cliente_nombre' | 'cliente_correo' | 'telefono_contacto'>;

type ModuleKey = 'agenda' | 'clientes' | 'mascotas' | 'consultas' | 'hospitalizacion' | 'cirugia' | 'hospedaje' | 'vacunacion' | 'desparasitacion' | 'estetica' | 'domicilio' | 'imagenes' | 'laboratorio' | 'farmacia' | 'reportes';

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
  consultas: { eyebrow: 'Atención clínica', title: 'Consultas y pacientes', description: 'Prioriza la jornada, abre la ficha clínica y registra atenciones sin mezclar cobros ni administración.', action: 'Iniciar atención', empty: 'No hay atenciones clínicas activas para mostrar.', keywords: ['consulta', 'cirugía', 'cirugia', 'traumatología', 'traumatologia', 'urgencia'], metrics: ['Citas de hoy', 'En espera', 'En atención', 'Resultados', 'Seguimientos'], features: ['Agenda filtrada por veterinario', 'Diagnóstico, exámenes y receta', 'Cierre clínico trazable'], categories: ['Agenda', 'Historia clínica', 'Órdenes', 'Recetas'] },
  hospitalizacion: { eyebrow: 'Cuidado continuo', title: 'Internamientos y hospitalización', description: 'Consulta citas y registros de internamiento, evolución clínica, medicación e indicaciones guardadas.', action: 'Nueva atención', empty: 'No hay internamientos vinculados con las citas actuales.', keywords: ['hospital', 'internamiento', 'internado'], metrics: ['Ingresos', 'Confirmados', 'Pendientes'], features: ['Ingreso y box asignado', 'Signos vitales y evolución diaria', 'Costo acumulado y alta médica'], categories: ['Boxes ocupados', 'Boxes disponibles', 'Altas del día'] },
  cirugia: { eyebrow: 'Procedimientos', title: 'Cirugía y procedimientos', description: 'Consulta las cirugías programadas y abre la atención para registrar el procedimiento y sus indicaciones.', action: 'Abrir atención', empty: 'No hay cirugías en las solicitudes actuales.', keywords: ['cirug', 'esteriliz', 'castr', 'operac'], metrics: ['Cirugías', 'Confirmadas', 'Pendientes'], features: ['Procedimiento y equipo responsable', 'Anestesia y evolución', 'Indicaciones postoperatorias'], categories: ['Programadas', 'En atención', 'Finalizadas'] },
  hospedaje: { eyebrow: 'Estadías', title: 'Reservas de hospedaje', description: 'Revisa las reservas y atenciones de hospedaje con los datos del paciente y las indicaciones registradas.', action: 'Nueva atención', empty: 'No hay reservas de hospedaje en las citas actuales.', keywords: ['hospedaje', 'guardería', 'guarderia'], metrics: ['Reservas', 'Confirmadas', 'Por coordinar'], features: ['Reserva por rango de fechas', 'Tarifa y costo acumulado', 'Alimentación y medicación'], categories: ['Próximos ingresos', 'Hospedados', 'Check-out próximo'] },
  vacunacion: { eyebrow: 'Medicina preventiva', title: 'Vacunas y desparasitación', description: 'Consulta aplicaciones preventivas, lotes y próximos controles junto a las citas registradas del paciente.', action: 'Registrar desde atención', empty: 'No hay citas de vacunación en las solicitudes disponibles.', keywords: ['vacuna', 'vacunación', 'vacunacion', 'desparasit', 'antipulga'], metrics: ['Registros', 'Confirmadas', 'Pendientes'], features: ['Producto, lote, peso y precio', 'Programación del próximo refuerzo', 'Delivery y cartilla imprimible'], categories: ['Aplicadas', 'Programadas', 'Vencidas', 'Delivery'] },
  desparasitacion: { eyebrow: 'Medicina preventiva', title: 'Desparasitación interna y externa', description: 'Mantén visible el historial preventivo y programa la siguiente aplicación.', action: 'Registrar desde atención', empty: 'No hay desparasitaciones en las solicitudes disponibles.', keywords: ['desparasitación', 'desparasitacion', 'antiparasitario'], metrics: ['Registros', 'Confirmadas', 'Pendientes'], features: ['Producto, dosis, peso y precio', 'Historial por paciente', 'Programación, delivery e impresión'], categories: ['Interna', 'Externa', 'Programadas', 'Delivery'] },
  estetica: { eyebrow: 'Bienestar', title: 'Baño, peluquería y estética', description: 'Organiza servicios combinables y revisa las atenciones efectuadas o programadas.', action: 'Gestionar solicitudes', empty: 'No hay servicios estéticos en las solicitudes disponibles.', keywords: ['baño', 'bano', 'peluquería', 'peluqueria', 'estética', 'estetica', 'uñas'], metrics: ['Servicios', 'Confirmados', 'Pendientes'], features: ['Servicios combinables', 'Catálogo con precios', 'Efectuados y programados'], categories: ['Baño estético', 'Baño medicado', 'Corte', 'Uñas y oídos', 'Antipulgas'] },
  domicilio: { eyebrow: 'Atención móvil', title: 'Servicios a domicilio', description: 'Identifica atenciones fuera de clínica, dirección, traslado y personal asignado.', action: 'Gestionar solicitudes', empty: 'No hay atenciones a domicilio en las solicitudes actuales.', keywords: ['domicilio', 'delivery'], metrics: ['Servicios', 'Confirmados', 'Por coordinar'], features: ['Disponible en cualquier atención', 'Dirección y costo de traslado', 'Personal y horario asignados'], categories: ['Programadas', 'En ruta', 'Completadas'] },
  imagenes: { eyebrow: 'Diagnóstico por imágenes', title: 'Ecografías y rayos X', description: 'Centraliza estudios médicos asociados al historial clínico de cada mascota.', action: 'Abrir atención', empty: 'No hay estudios de imágenes en las solicitudes disponibles.', keywords: ['ecografía', 'ecografia', 'rayos', 'radiografía', 'radiografia'], metrics: ['Estudios', 'Confirmados', 'Pendientes'], features: ['Galería y subida múltiple', 'Estudio, hallazgos y diagnóstico', 'Visor con zoom por tipo'], categories: ['Ecografía', 'Rayos X', 'Otros estudios'] },
  laboratorio: { eyebrow: 'Diagnóstico clínico', title: 'Laboratorio y resultados', description: 'Organiza solicitudes y resultados de laboratorio asociados al paciente.', action: 'Abrir atención', empty: 'No hay análisis de laboratorio en las solicitudes disponibles.', keywords: ['laboratorio', 'hematología', 'hematologia', 'urianálisis', 'bioquímica', 'citología', 'parasitología', 'hisopado', 'raspado'], metrics: ['Análisis', 'Confirmados', 'Pendientes'], features: ['Resultados, unidades y referencia', 'Alertas automáticas de valores anormales', 'Informe PDF con identidad de la clínica'], categories: ['Hematología', 'Urianálisis', 'Bioquímica', 'Citología', 'Parasitología', 'Hisopado', 'Raspado'] },
  farmacia: { eyebrow: 'Control interno', title: 'Farmacia e inventario clínico', description: 'Consulta el alcance del control interno asociado a tratamientos y atenciones.', action: 'Abrir atención', empty: 'No hay salidas de farmacia vinculadas con las solicitudes actuales.', keywords: ['farmacia', 'medicamento', 'alimento', 'insumo'], metrics: ['Movimientos', 'Atenciones', 'Alertas'], features: ['Medicamentos, alimentos e insumos', 'Stock mínimo y vencimiento', 'Salida automática al recetar'], categories: ['Stock crítico', 'Próximos a vencer', 'Salidas clínicas'] },
  reportes: { eyebrow: 'Documentación clínica', title: 'Documentos y registros clínicos', description: 'Consulta tus atenciones, fichas iniciales y documentos del paciente. Abre el detalle o descarga su historial en PDF.', action: 'Ver agenda', empty: 'No hay citas para los filtros seleccionados.', keywords: [], metrics: ['Atenciones', 'Servicios distintos', 'Pacientes'], features: ['Atenciones por veterinario', 'Servicios más solicitados', 'Preventivos vencidos y stock crítico'], categories: ['Actividad clínica', 'Estética', 'Farmacia', 'Prevención'] },
};

@Component({
  selector: 'app-veterinarian-module',
  standalone: true,
  imports: [RouterLink, VeterinarianIconComponent, VeterinarianPaginationComponent, VeterinarianStatusComponent],
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
  readonly records = signal<VeterinarianClinicalRecord[]>([]);
  readonly view = signal<'appointments' | 'records'>('appointments');
  readonly status = signal('');
  readonly sort = signal('recent');
  readonly expandedRecord = signal<number | null>(null);
  readonly pdfPetId = signal<number | null>(null);
  readonly dateLabel = clinicalDate;
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
    const query = clinicalSearch(this.search());
    return this.appointments().filter((appointment) => {
      const service = clinicalSearch(appointment.servicio.nombre);
      const moduleMatch = definition.keywords.length === 0 || definition.keywords.some((keyword) => service.includes(clinicalSearch(keyword))) || (this.moduleKey() === 'vacunacion' && /desparasit|antipulga/.test(service));
      const text = clinicalSearch(`${appointment.id} ${appointment.mascota.nombre} ${appointment.cliente_nombre} ${appointment.cliente_correo} ${appointment.servicio.nombre} ${appointment.telefono_contacto || ''}`);
      return moduleMatch && (!query || text.includes(query)) && (this.view() !== 'appointments' || !this.status() || appointment.estado === this.status());
    }).sort((a, b) => this.sort() === 'patient' ? a.mascota.nombre.localeCompare(b.mascota.nombre, 'es') : (Date.parse(a.fecha_hora_programada) - Date.parse(b.fecha_hora_programada)) * (this.sort() === 'oldest' ? 1 : -1));
  });
  readonly filteredRecords = computed(() => {
    const query = clinicalSearch(this.search());
    const module = this.moduleKey();
    return this.records().filter(record => {
      const serviceText = clinicalSearch(`${record.servicio_nombre} ${record.archivos.map(file => file.tipo_examen).join(' ')} ${record.ordenes_examen.map(exam => exam.tipo).join(' ')} ${record.procedimientos_realizados.map(procedure => procedure.nombre).join(' ')} ${record.examenes_resultados || ''}`);
      const preventive = module === 'vacunacion' && (!!record.vacunas || !!record.desparasitaciones || record.aplicaciones_preventivas.length > 0);
      const laboratory = module === 'laboratorio' && (
        record.ordenes_examen.some(exam => !/radiograf|rayos|ecograf|imagen/i.test(exam.tipo)) ||
        (!!record.examenes_resultados && !/radiograf|rayos|ecograf|imagen/i.test(`${record.servicio_nombre} ${record.examenes_resultados}`))
      );
      const imaging = module === 'imagenes' && record.archivos.some(file => !/laboratorio|hemograma|bioquim|citolog|urian/i.test(clinicalSearch(file.tipo_examen)));
      const moduleMatch = this.definition().keywords.length === 0 || preventive || laboratory || imaging || this.definition().keywords.some(keyword => serviceText.includes(clinicalSearch(keyword)));
      const text = clinicalSearch(`${record.id} ${record.mascota.nombre} ${record.cliente_nombre} ${record.cliente_correo} ${record.servicio_nombre} ${record.diagnostico || ''} ${record.tratamiento || ''} ${serviceText}`);
      return moduleMatch && (!query || text.includes(query)) && (this.view() !== 'records' || !this.status() || record.estado === this.status());
    }).sort((a, b) => this.sort() === 'patient' ? a.mascota.nombre.localeCompare(b.mascota.nombre, 'es') : (Date.parse(a.fecha_inicio) - Date.parse(b.fecha_inicio)) * (this.sort() === 'oldest' ? 1 : -1));
  });
  readonly appointmentTable = new VeterinarianTableState(this.filteredAppointments);
  readonly recordTable = new VeterinarianTableState(this.filteredRecords);
  readonly table = computed(() => this.view() === 'appointments' ? this.appointmentTable : this.recordTable);
  readonly patientsCount = computed(() => new Set([...this.filteredAppointments().map(item => item.mascota.id), ...this.filteredRecords().map(item => item.mascota_id)]).size);
  readonly historyTab = computed(() => {
    const tabs: Partial<Record<ModuleKey, string>> = { imagenes: 'examenes', laboratorio: 'laboratorio', vacunacion: 'preventivos' };
    return tabs[this.moduleKey()] || 'historia';
  });
  readonly detailFields = [
    { key: 'motivo_consulta', label: 'Motivo de consulta' }, { key: 'anamnesis', label: 'Anamnesis' },
    { key: 'diagnostico', label: 'Diagnóstico' }, { key: 'tratamiento', label: 'Tratamiento e indicaciones' },
    { key: 'observaciones', label: 'Observaciones' }, { key: 'historial_alergias', label: 'Alergias' },
    { key: 'medicamentos', label: 'Medicamentos' }, { key: 'procedimientos', label: 'Procedimientos' },
    { key: 'vacunas', label: 'Vacunas' }, { key: 'desparasitaciones', label: 'Desparasitación' },
    { key: 'examenes_resultados', label: 'Resultados registrados' },
  ] as const;
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
    if (['imagenes', 'laboratorio', 'vacunacion', 'reportes'].includes(this.moduleKey())) this.view.set('records');
    this.load();
  }

  load(): void {
    this.loading.set(true);
    forkJoin({ appointments: this.api.getRequests(undefined, undefined, undefined, true), records: this.api.getClinicalRecords() })
      .pipe(finalize(() => this.loading.set(false))).subscribe({
        next: ({ appointments, records }) => { this.appointments.set(appointments); this.records.set(records); this.errorMessage.set(''); },
        error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
      });
  }

  setSearch(value: string): void { this.search.set(value); this.appointmentTable.reset(); this.recordTable.reset(); }
  setView(value: 'appointments' | 'records'): void { this.view.set(value); this.status.set(''); this.expandedRecord.set(null); }
  setStatus(value: string): void { this.status.set(value); this.table().reset(); }
  setSort(value: string): void { this.sort.set(value); this.table().reset(); }
  clearFilters(): void { this.setSearch(''); this.status.set(''); }
  canConfirm(appointment: VeterinarianAppointment): boolean { return ['pendiente_contacto', 'contactando_cliente', 'esperando_respuesta', 'requiere_otro_horario'].includes(appointment.estado); }
  canAttend(appointment: VeterinarianAppointment): boolean { return appointment.veterinario_id !== null && ['confirmada', 'reprogramada'].includes(appointment.estado); }
  toggleRecord(record: VeterinarianClinicalRecord): void { this.expandedRecord.update(id => id === record.id ? null : record.id); }

  startAttention(appointment: VeterinarianAppointment): void {
    void this.router.navigate(['/veterinario/atencion', appointment.id]);
  }

  registerArrival(appointment: VeterinarianAppointment): void {
    if (this.savingId() !== null) return;
    this.savingId.set(appointment.id);
    this.api.registerArrival(appointment.id).pipe(finalize(() => this.savingId.set(null))).subscribe({
      next: (updated) => {
        this.appointments.update((items) => items.map((item) => item.id === updated.id ? updated : item));
        this.notice.show('Llegada registrada');
      },
      error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
  }

  confirmAppointment(appointment: VeterinarianAppointment): void {
    if (this.savingId() !== null) return;
    this.savingId.set(appointment.id);
    this.api.updateRequest(appointment.id, { estado: 'confirmada' }).pipe(finalize(() => this.savingId.set(null))).subscribe({
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

  showHistory(appointment: HistorySubject): void {
    void this.router.navigate(['/veterinario/mascota', appointment.mascota.id]);
  }

  sendHistory(appointment: HistorySubject, channel: 'whatsapp' | 'correo'): void {
    if (channel === 'whatsapp') {
      if (!appointment.telefono_contacto) {
        this.errorMessage.set('El cliente no tiene un teléfono registrado.');
        return;
      }
      const phone = appointment.telefono_contacto.replace(/\D/g, '');
      const message = `Hola ${appointment.cliente_nombre}, te compartimos el historial clínico de ${appointment.mascota.nombre}. Puedes solicitar el informe PDF a la clínica.`;
      window.open(`https://wa.me/${phone}?text=${encodeURIComponent(message)}`, '_blank', 'noopener,noreferrer');
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

  downloadHistoryPdf(appointment: HistorySubject): void {
    if (this.pdfPetId() !== null) return;
    this.pdfPetId.set(appointment.mascota.id);
    this.api.getPetHistory(appointment.mascota.id).subscribe({
      next: async (records) => {
        try {
        const { default: jsPDF } = await import('jspdf');
        const pdf = new jsPDF();
        const logo = await this.loadImage('/logo.png');
        const pageWidth = pdf.internal.pageSize.getWidth();
        let y = 18;
        const write = (label: string, value: string): void => {
          const lines: string[] = pdf.splitTextToSize(`${label}: ${value}`, pageWidth - 40);
          for (const line of lines) {
            if (y > 276) { pdf.addPage(); y = 18; }
            pdf.text(line, 20, y);
            y += 5;
          }
          y += 2;
        };

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
        write('Mascota', appointment.mascota.nombre);
        write('Especie', appointment.mascota.especie);
        write('Raza', appointment.mascota.raza || 'No registrada');
        write('Sexo', appointment.mascota.sexo || 'No registrado');
        if (appointment.mascota.fecha_nacimiento) write('Nacimiento', clinicalDate(appointment.mascota.fecha_nacimiento));
        if (appointment.mascota.caracteristicas) write('Caracteristicas', appointment.mascota.caracteristicas);
        write('Propietario', appointment.cliente_nombre);
        write('Correo', appointment.cliente_correo);
        write('Telefono', appointment.telefono_contacto || 'No registrado');
        y += 6;

        if (y > 258) { pdf.addPage(); y = 18; }
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
          pdf.setFontSize(11);
          pdf.setFont('helvetica', 'bold');
          const title: string[] = pdf.splitTextToSize(`${index + 1}. ${record.servicio_nombre} · ${this.formatDate(record.fecha_inicio)}`, pageWidth - 40);
          const height = title.length * 5 + 6;
          if (y + height > 276) { pdf.addPage(); y = 18; }
          pdf.setFillColor(234, 249, 246);
          pdf.rect(16, y - 5, pageWidth - 32, height, 'F');
          pdf.setTextColor(16, 43, 53);
          pdf.setFontSize(11);
          pdf.setFont('helvetica', 'bold');
          pdf.text(title, 20, y);
          y += height;
          pdf.setFontSize(9);
          pdf.setFont('helvetica', 'normal');
          pdf.setTextColor(60, 70, 75);
          for (const [label, key] of fields) {
            const value = record[key];
            if (value === null || value === undefined || value === '') continue;
            write(label, String(value));
          }
          record.diagnosticos.forEach(item => write('Diagnostico detallado', `${item.codigo || ''} ${item.descripcion}${item.es_principal ? ' (principal)' : ''}. ${item.observaciones || ''}`));
          record.ordenes_examen.forEach(item => write('Examen', `${item.tipo} · ${item.estado} · ${item.prioridad}. Resultado: ${item.resultado || 'Pendiente'}. Interpretacion: ${item.interpretacion || 'Sin registrar'}`));
          record.aplicaciones_preventivas.forEach(item => write('Preventivo', `${item.tipo}: ${item.producto}. Lote: ${item.lote || 'Sin registrar'}. Aplicacion: ${clinicalDate(item.fecha_aplicacion)}. Proximo control: ${item.proxima_fecha ? clinicalDate(item.proxima_fecha) : 'No programado'}. ${item.observaciones || ''}`));
          record.procedimientos_realizados.forEach(item => write('Procedimiento realizado', `${item.nombre} · ${clinicalDate(item.fecha_realizacion)}. ${item.observaciones || ''}`));
          if (record.receta) {
            write('Indicaciones de la receta', record.receta.indicaciones_generales || 'Sin indicaciones generales');
            record.receta.detalles.forEach(item => write('Medicamento recetado', `${item.medicamento} ${item.presentacion || ''}. Dosis: ${item.dosis} ${item.unidad}. Via: ${item.via}. Frecuencia: ${item.frecuencia}. Duracion: ${item.duracion}. Cantidad: ${item.cantidad || 'Sin registrar'}. ${item.indicaciones || ''}`));
          }
          record.archivos.forEach(item => write('Archivo clinico', `${item.tipo_examen} · ${clinicalDate(item.fecha_estudio)} · ${item.archivo_ruta}`));
          write('Veterinario', record.veterinario_nombre || 'Sin asignar');
          y += 4;
        });

        const pages = pdf.getNumberOfPages();
        for (let page = 1; page <= pages; page++) {
          pdf.setPage(page); pdf.setFontSize(8); pdf.setTextColor(110, 110, 110);
          pdf.text('Clinica Veterinaria San Martin de Porres · Historial clinico', 16, 290);
          pdf.text(`${page} / ${pages}`, pageWidth - 16, 290, { align: 'right' });
        }
        pdf.save(`historial-${clinicalSearch(appointment.mascota.nombre).replace(/[^a-z0-9]+/g, '-')}.pdf`);
        } catch { this.errorMessage.set('No se pudo generar el documento PDF. Intenta nuevamente.'); }
        finally { this.pdfPetId.set(null); }
      },
      error: (error: unknown) => { this.pdfPetId.set(null); this.errorMessage.set(this.errorText(error)); },
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

  private reload(): void { this.load(); }

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
