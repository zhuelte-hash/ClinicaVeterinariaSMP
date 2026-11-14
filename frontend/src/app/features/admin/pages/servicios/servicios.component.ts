import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { AuthService } from '../../../../core/auth/auth.service';
import { ManagedService, MedicalKind, OperationsApiService, operationError, ServiceWrite } from '../../services/operations-api.service';
import { PageHeaderComponent } from '../../shared/page-header.component';

@Component({ standalone: true, imports: [FormsModule, PageHeaderComponent], styleUrl: '../../shared/admin-ui.css', template: `
  <admin-page-header title="Tarifas y servicios" description="Catálogo único para el portal, reservas, atenciones y caja. Las órdenes ya emitidas conservan sus importes." />
  @if (error()) { <p class="mb-4 rounded-xl bg-rose-50 p-4 text-rose-700" role="alert">{{ error() }}</p> }
  @if (message()) { <p class="mb-4 rounded-xl bg-teal-50 p-4 text-teal-800" role="status">{{ message() }}</p> }
  <div class="admin-card mb-5 flex flex-wrap items-center gap-3 p-4">
    <input class="admin-input max-w-sm" aria-label="Buscar servicios" placeholder="Nombre o código" [ngModel]="query()" (ngModelChange)="query.set($event)">
    <label><input type="checkbox" [ngModel]="includeInactive()" (ngModelChange)="includeInactive.set($event)"> Mostrar inactivos</label>
    <button class="admin-secondary" [disabled]="busy() || loading()" (click)="load()">Actualizar</button>
    @if (auth.can('citas', 'crear')) { <button class="admin-primary" [disabled]="busy()" (click)="create()">Nuevo servicio</button> }
  </div>
  @if (loading()) { <p role="status">Consultando servicios…</p> }
  <section class="admin-card overflow-x-auto"><table class="admin-table"><thead><tr><th>Servicio</th><th>Tipo</th><th>Tarifa</th><th>Duración</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>
    @for (item of filtered(); track item.id) { <tr><td><b>{{ item.nombre }}</b><small class="block">{{ item.codigo }}</small></td><td>{{ item.tipo === 'medica' ? 'Médico' : 'Estético' }}</td><td>S/ {{ money(item.precio_referencial) }}</td><td>{{ item.duracion_estimada_min }} min</td><td>{{ item.activo ? 'Activo' : 'Inactivo' }}</td><td>@if (auth.can('citas', 'editar')) { <div class="flex gap-3"><button class="admin-secondary" [disabled]="busy()" (click)="edit(item)">Editar</button><button class="admin-secondary" [disabled]="busy()" (click)="toggle(item)">{{ item.activo ? 'Desactivar' : 'Activar' }}</button></div> } @else { <span>Solo consulta</span> }</td></tr> }
    @empty { <tr><td colspan="6">Sin servicios para estos filtros.</td></tr> }
  </tbody></table></section>
  @if (form; as data) {
    <div class="admin-modal"><form class="admin-modal-panel grid gap-4 sm:grid-cols-2" #serviceForm="ngForm" (ngSubmit)="save()" role="dialog" aria-modal="true" aria-labelledby="service-form-title">
      <h2 id="service-form-title" class="text-xl font-bold sm:col-span-2">{{ editingId === undefined ? 'Nuevo servicio' : 'Editar servicio' }}</h2>
      <label>Nombre<input required minlength="2" maxlength="150" class="admin-input" name="nombre" [(ngModel)]="data.nombre"></label>
      <label>Código<input required minlength="2" maxlength="50" pattern="[a-z0-9-]+" class="admin-input" name="codigo" [(ngModel)]="data.codigo"><small>Minúsculas, números y guiones.</small></label>
      <label class="sm:col-span-2">Descripción<textarea required minlength="3" maxlength="5000" class="admin-input" name="descripcion" [(ngModel)]="data.descripcion" rows="3"></textarea></label>
      <label>Tarifa referencial (S/)<input required type="number" min="0" step="0.01" class="admin-input" name="precio" [(ngModel)]="data.precio_referencial"></label>
      <label>Duración (minutos)<input required type="number" min="5" max="1440" step="1" class="admin-input" name="duracion" [(ngModel)]="data.duracion_estimada_min"></label>
      <label>Tipo<select class="admin-input" name="tipo" [(ngModel)]="data.tipo" [disabled]="editingId !== undefined"><option value="medica">Médico</option><option value="estetica">Estético</option></select></label>
      @if (data.tipo === 'medica') { <label>Atención médica<select class="admin-input" name="tipoMedico" [(ngModel)]="data.tipo_medico">@for (kind of medicalKinds; track kind.value) { <option [value]="kind.value">{{ kind.label }}</option> }</select></label> }
      <label class="sm:col-span-2"><input type="checkbox" name="activo" [(ngModel)]="data.activo"> Activo para nuevas reservas y cobros</label>
      <p class="text-sm text-slate-500 sm:col-span-2">Cambiar la duración no modifica citas ya programadas. Desactivar conserva el historial y retira el servicio del catálogo activo.</p>
      @if (error()) { <p class="text-rose-700 sm:col-span-2" role="alert">{{ error() }}</p> }
      <div class="flex justify-end gap-3 sm:col-span-2"><button type="button" class="admin-secondary" [disabled]="busy()" (click)="form = null">Cancelar</button><button class="admin-primary" [disabled]="busy() || serviceForm.invalid">{{ busy() ? 'Guardando…' : 'Guardar servicio' }}</button></div>
    </form></div>
  }
` })
export class ServiciosComponent {
  readonly auth = inject(AuthService);
  private readonly api = inject(OperationsApiService);
  readonly services = signal<ManagedService[]>([]);
  readonly loading = signal(false); readonly busy = signal(false); readonly error = signal(''); readonly message = signal('');
  readonly query = signal(''); readonly includeInactive = signal(false);
  readonly filtered = computed(() => this.services().filter(item => (item.activo || this.includeInactive()) && `${item.nombre} ${item.codigo}`.toLocaleLowerCase('es').includes(this.query().trim().toLocaleLowerCase('es'))));
  readonly medicalKinds: { value: MedicalKind; label: string }[] = [
    { value: 'consulta_general', label: 'Consulta general' }, { value: 'cirugia', label: 'Cirugía' }, { value: 'vacunacion', label: 'Vacunación' }, { value: 'desparasitacion', label: 'Desparasitación' }, { value: 'laboratorio_e_imagen', label: 'Laboratorio e imagen' },
  ];
  editingId: number | undefined;
  form: ServiceWrite | null = null;
  constructor() { this.load(); }
  load(): void { this.loading.set(true); this.api.services().pipe(finalize(() => this.loading.set(false))).subscribe({ next: rows => this.services.set(rows), error: error => this.error.set(operationError(error)) }); }
  create(): void { if (!this.auth.can('citas', 'crear')) return; this.editingId = undefined; this.error.set(''); this.form = { codigo: '', nombre: '', descripcion: '', precio_referencial: 0, duracion_estimada_min: 30, activo: true, tipo: 'medica', tipo_medico: 'consulta_general' }; }
  private payload(item: ManagedService): ServiceWrite { const { id, ...data } = item; return { ...data, tipo_medico: item.tipo_medico ?? 'consulta_general' }; }
  edit(item: ManagedService): void { if (!this.auth.can('citas', 'editar')) return; this.editingId = item.id; this.error.set(''); this.form = this.payload(item); }
  save(): void { if (!this.form || this.busy() || !this.auth.can('citas', this.editingId === undefined ? 'crear' : 'editar')) return; this.persist(this.form, this.editingId, 'Servicio guardado. Portal, agenda y caja usan el catálogo actualizado.'); }
  toggle(item: ManagedService): void { if (this.busy() || !this.auth.can('citas', 'editar')) return; this.persist({ ...this.payload(item), activo: !item.activo }, item.id, item.activo ? 'Servicio desactivado; historial conservado.' : 'Servicio activado.'); }
  private persist(data: ServiceWrite, id: number | undefined, message: string): void { this.busy.set(true); this.error.set(''); this.message.set(''); this.api.saveService(data, id).pipe(finalize(() => this.busy.set(false))).subscribe({ next: () => { this.form = null; this.message.set(message); this.load(); }, error: error => this.error.set(operationError(error)) }); }
  money(value: string | number): string { return Number(value).toFixed(2); }
}
