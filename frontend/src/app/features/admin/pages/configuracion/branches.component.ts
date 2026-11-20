import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../../../core/auth/auth.service';
import { Branch, BranchService } from '../../../../core/services/branch.service';
import { operationError } from '../../services/operations-api.service';

@Component({
  standalone: true, imports: [FormsModule], styleUrl: '../../shared/admin-ui.css',
  template: `<h1 class="mb-4 text-2xl font-bold">Sucursales</h1>
    <p class="mb-4">La sede seleccionada en la cabecera determina la agenda, caja, inventario y reportes. Asigna colaboradores desde Usuarios; los permisos por rol y el catálogo de servicios son compartidos.</p>
    @if (error()) { <p role="alert" class="mb-4 text-rose-700">{{ error() }}</p> }
    @if (message()) { <p role="status">{{ message() }}</p> }
    <button type="button" class="admin-secondary mb-4" (click)="load()">Actualizar sucursales</button>
    @if (loading()) { <p role="status">Cargando sucursales…</p> }
    <div class="admin-card overflow-x-auto"><table class="admin-table"><thead><tr><th>Sede</th><th>Dirección</th><th>Teléfono</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>
    @for (item of items(); track item.id) { <tr><td>{{ item.nombre }}</td><td>{{ item.direccion }}</td><td>{{ item.telefono }}</td><td>{{ item.activa ? 'Activa' : 'Inactiva' }}</td><td>
      @if (item.activa) { <button class="admin-secondary" (click)="api.select(item.id)">Trabajar en {{ item.nombre }}</button> }
      @if (auth.can('usuarios', 'editar')) { <button class="admin-secondary" (click)="edit(item)">Editar {{ item.nombre }}</button> }
    </td></tr> } @empty { @if (!loading()) { <tr><td colspan="5">No hay sucursales.</td></tr> } }
    </tbody></table></div>
    @if (auth.can('usuarios', 'crear') || editing) {
      <form class="admin-card mt-5 space-y-3 p-4" (ngSubmit)="save()"><h2 class="text-xl font-bold">{{ editing ? 'Editar sucursal' : 'Nueva sucursal' }}</h2>
        <label class="block">Nombre de sucursal<input class="admin-input" name="nombre" required minlength="2" maxlength="150" [(ngModel)]="form.nombre"></label>
        <label class="block">Dirección de sucursal<input class="admin-input" name="direccion" maxlength="250" [(ngModel)]="form.direccion"></label>
        <label class="block">Teléfono de sucursal<input class="admin-input" name="telefono" maxlength="30" [(ngModel)]="form.telefono"></label>
        <label class="block"><input type="checkbox" name="activa" [(ngModel)]="form.activa"> Sucursal activa</label>
        <button class="admin-primary" [disabled]="saving()">{{ saving() ? 'Guardando…' : 'Guardar sucursal' }}</button>
        @if (editing) { <button type="button" class="admin-secondary" (click)="reset()">Cancelar edición</button> }
      </form>
    }`,
})
export class BranchesComponent {
  readonly api = inject(BranchService); readonly auth = inject(AuthService);
  readonly items = signal<Branch[]>([]); readonly error = signal(''); readonly message = signal('');
  readonly loading = signal(false); readonly saving = signal(false); editing: number | undefined;
  form = { nombre: '', direccion: '', telefono: '', activa: true };
  constructor() { this.load(); }
  load(): void { this.loading.set(true); this.error.set(''); this.api.all().subscribe({ next: data => { this.items.set(data); this.loading.set(false); }, error: e => { this.error.set(operationError(e)); this.loading.set(false); } }); }
  edit(item: Branch): void { this.editing = item.id; this.form = { nombre: item.nombre, direccion: item.direccion, telefono: item.telefono, activa: item.activa }; this.message.set(''); }
  reset(): void { this.editing = undefined; this.form = { nombre: '', direccion: '', telefono: '', activa: true }; }
  save(): void { if (this.saving()) return; this.saving.set(true); this.error.set(''); this.api.save(this.form, this.editing).subscribe({ next: () => { this.saving.set(false); this.reset(); this.message.set('Sucursal guardada.'); this.load(); }, error: e => { this.saving.set(false); this.error.set(operationError(e)); } }); }
}
