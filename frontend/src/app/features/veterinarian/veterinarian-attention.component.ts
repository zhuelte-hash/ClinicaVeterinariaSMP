import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { finalize, switchMap } from 'rxjs/operators';
import { NoticeService } from '../../core/services/notice.service';
import { VeterinarianApiService } from './veterinarian-api.service';
import { ClinicalRecord, ExamOrder, PrescriptionDetail, VeterinarianAppointment } from './veterinarian.models';

@Component({
  selector: 'app-veterinarian-attention',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './veterinarian-attention.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class VeterinarianAttentionComponent {
  private readonly api = inject(VeterinarianApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly formBuilder = inject(FormBuilder);
  private readonly notice = inject(NoticeService);
  readonly appointment = signal<VeterinarianAppointment | null>(null);
  readonly record = signal<ClinicalRecord | null>(null);
  readonly history = signal<ClinicalRecord[]>([]);
  readonly exams = signal<ExamOrder[]>([]);
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly error = signal('');
  readonly examForm = this.formBuilder.nonNullable.group({ tipo: ['Hemograma'], prioridad: ['rutina' as 'rutina' | 'urgente' | 'emergencia'] });
  readonly prescriptionForm = this.formBuilder.nonNullable.group({ medicamento: [''], presentacion: [''], dosis: [''], unidad: ['mg'], via: ['Oral'], frecuencia: [''], duracion: [''], cantidad: [''], indicaciones: [''], indicaciones_generales: [''] });
  readonly procedureForm = this.formBuilder.nonNullable.group({ nombre: [''], observaciones: [''] });
  readonly preventiveForm = this.formBuilder.nonNullable.group({ tipo: ['vacuna' as 'vacuna' | 'desparasitacion'], producto: [''], lote: [''], fecha_vencimiento: [''], fecha_aplicacion: [new Date().toISOString().slice(0, 10)], proxima_fecha: [''], observaciones: [''] });
  readonly attentionForm = this.formBuilder.nonNullable.group({ motivo_consulta: [''], anamnesis: [''], observaciones: [''], diagnostico: [''], tratamiento: [''], peso: [''], temperatura: [''], historial_alergias: [''], medicamentos: [''], procedimientos: [''], examenes_resultados: [''], proxima_fecha_control: [''] });

  constructor() {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.api.getRequests().pipe(switchMap((requests) => {
      const appointment = requests.find((item) => item.id === id) || null;
      this.appointment.set(appointment);
      return appointment ? forkJoin({ history: this.api.getPetHistory(appointment.mascota.id), attention: this.api.startAttention(appointment.id) }) : of({ history: [], attention: null });
    }), finalize(() => this.loading.set(false))).subscribe({
      next: ({ history, attention }) => { this.history.set(history); if (attention) { this.record.set(attention); this.attentionForm.patchValue({ motivo_consulta: attention.motivo_consulta || this.appointment()?.motivo || '' }); this.api.getExamOrders(attention.id).subscribe({ next: (exams) => this.exams.set(exams) }); } },
      error: (error: { error?: { detail?: string } }) => this.error.set(error.error?.detail || 'No se pudo abrir la atención.'),
    });
  }

  save(status: 'en_atencion' | 'cerrada'): void {
    const appointment = this.appointment();
    if (!appointment || !this.record()) return;
    this.saving.set(true);
    const values = this.attentionForm.getRawValue();
    const payload = { ...values, estado: status, peso: values.peso || null, temperatura: values.temperatura || null, proxima_fecha_control: values.proxima_fecha_control || null };
    this.api.registerAttention(appointment.id, payload).pipe(
      switchMap((record) => {
        this.record.set(record);
        const diagnosis = values.diagnostico.trim() ? this.api.addDiagnosis(record.id, { descripcion: values.diagnostico, es_principal: true }) : of(null);
        const procedure = values.procedimientos.trim() ? this.api.addProcedure(record.id, { nombre: values.procedimientos, observaciones: values.observaciones || undefined }) : of(null);
        return forkJoin({ record: of(record), diagnosis, procedure });
      }),
      finalize(() => this.saving.set(false)),
    ).subscribe({ next: ({ record }) => { this.record.set(record); this.notice.show(status === 'cerrada' ? 'Atención cerrada y guardada' : 'Borrador guardado'); }, error: (error: { error?: { detail?: string } }) => this.error.set(error.error?.detail || 'No se pudo guardar la atención.') });
  }

  requestExam(): void {
    const record = this.record();
    if (!record || !this.examForm.value.tipo) return;
    this.api.addExamOrder(record.id, this.examForm.getRawValue()).subscribe({ next: (exam) => { this.exams.update((items) => [...items, exam]); this.notice.show('Orden de examen registrada'); }, error: (error: { error?: { detail?: string } }) => this.error.set(error.error?.detail || 'No se pudo solicitar el examen.') });
  }

  savePrescription(): void {
    const record = this.record();
    const value = this.prescriptionForm.getRawValue();
    if (!record || !value.medicamento || !value.dosis || !value.frecuencia || !value.duracion) { this.error.set('Completa medicamento, dosis, frecuencia y duración.'); return; }
    const detail: Omit<PrescriptionDetail, 'id' | 'receta_id'> = { medicamento: value.medicamento, presentacion: value.presentacion, dosis: value.dosis, unidad: value.unidad, via: value.via, frecuencia: value.frecuencia, duracion: value.duracion, cantidad: value.cantidad, indicaciones: value.indicaciones };
    this.api.savePrescription(record.id, { indicaciones_generales: value.indicaciones_generales, detalles: [detail] }).subscribe({ next: () => this.notice.show('Receta emitida; no se descontó inventario'), error: (error: { error?: { detail?: string } }) => this.error.set(error.error?.detail || 'No se pudo emitir la receta.') });
  }

  savePreventive(): void {
    const record = this.record();
    const value = this.preventiveForm.getRawValue();
    if (!record || !value.producto) { this.error.set('Indica el producto aplicado.'); return; }
    this.api.addPreventive(record.id, { ...value, fecha_vencimiento: value.fecha_vencimiento || undefined, proxima_fecha: value.proxima_fecha || undefined }).subscribe({ next: () => this.notice.show('Aplicación preventiva registrada'), error: (error: { error?: { detail?: string } }) => this.error.set(error.error?.detail || 'No se pudo registrar la aplicación.') });
  }

  formatDate(value: string): string { return new Intl.DateTimeFormat('es-PE', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Lima' }).format(new Date(value)); }
}
