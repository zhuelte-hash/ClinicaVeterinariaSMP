import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { AdminApiService, Supplier } from '../../services/admin-api.service';
import { PageHeaderComponent } from '../../shared/page-header.component';
import { NoticeService } from '../../../../core/services/notice.service';

@Component({
  selector: 'app-suppliers', standalone: true, imports: [FormsModule, RouterLink, PageHeaderComponent],
  styleUrl: '../../shared/admin-ui.css', changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<admin-page-header title="Proveedores" description="Registra proveedores y asócialos desde la edición de productos." action="Nuevo proveedor" (actionClick)="create()" />
    @if (error()) { <p class="mb-4 rounded-xl bg-rose-50 p-4 text-rose-700" role="alert">{{ error() }}</p> }
    <div class="admin-card mb-4 flex flex-wrap gap-3 p-4"><label class="flex-1"><span class="sr-only">Buscar proveedor</span><input class="admin-input" type="search" placeholder="Buscar razón social" [ngModel]="search()" (ngModelChange)="search.set($event)"></label><button class="admin-secondary" (click)="load()">Actualizar</button><a routerLink="/admin/productos" class="admin-secondary">Asociar productos</a></div>
    <div class="admin-card overflow-x-auto"><table class="admin-table"><thead><tr><th>Razón social</th><th>Productos asociados</th><th>Acción</th></tr></thead><tbody>@if (loading()) { <tr><td colspan="3" role="status">Cargando proveedores…</td></tr> } @else { @for (item of filtered(); track item.id) { <tr><td>{{ item.razon_social }}</td><td>{{ item.productos }}</td><td><button type="button" class="admin-secondary" (click)="edit(item)">Editar</button></td></tr> } @empty { <tr><td colspan="3">No hay proveedores para la búsqueda.</td></tr> } }</tbody></table></div>
    @if (modal()) { <div class="admin-modal"><form class="admin-modal-panel" #supplierForm="ngForm" (ngSubmit)="save()" role="dialog" aria-modal="true" aria-labelledby="supplier-title"><h2 id="supplier-title" class="text-xl font-bold">{{ editing() ? 'Editar proveedor' : 'Nuevo proveedor' }}</h2><label class="mt-5 block"><span class="admin-label">Razón social</span><input class="admin-input" name="razon-social" [(ngModel)]="name" required minlength="2" maxlength="180"></label>@if (error()) { <p class="mt-2 text-rose-700" role="alert">{{ error() }}</p> }<div class="mt-5 flex justify-end gap-3"><button type="button" class="admin-secondary" [disabled]="saving()" (click)="modal.set(false)">Cancelar</button><button class="admin-primary" [disabled]="saving() || supplierForm.invalid || name.trim().length < 2">{{ saving() ? 'Guardando…' : 'Guardar proveedor' }}</button></div></form></div> }`,
})
export class ProveedoresComponent {
  private readonly api = inject(AdminApiService); private readonly notice = inject(NoticeService);
  readonly suppliers = signal<Supplier[]>([]); readonly loading = signal(true); readonly saving = signal(false); readonly error = signal(''); readonly modal = signal(false); readonly editing = signal<Supplier | null>(null); readonly search = signal('');
  readonly filtered = computed(() => this.suppliers().filter(item => item.razon_social.toLocaleLowerCase('es').includes(this.search().trim().toLocaleLowerCase('es'))));
  name = '';
  constructor() { this.load(); }
  load(): void { this.loading.set(true); this.api.getSuppliers().pipe(finalize(() => this.loading.set(false))).subscribe({ next: items => { this.suppliers.set(items); this.error.set(''); }, error: error => this.fail(error) }); }
  create(): void { this.editing.set(null); this.name = ''; this.error.set(''); this.modal.set(true); }
  edit(item: Supplier): void { this.editing.set(item); this.name = item.razon_social; this.error.set(''); this.modal.set(true); }
  save(): void { if (this.saving()) return; const item = this.editing(); this.saving.set(true); (item ? this.api.updateSupplier(item.id, this.name.trim()) : this.api.createSupplier(this.name.trim())).pipe(finalize(() => this.saving.set(false))).subscribe({ next: () => { this.modal.set(false); this.notice.show('Proveedor guardado'); this.load(); }, error: error => this.fail(error) }); }
  private fail(error: HttpErrorResponse): void { this.error.set(typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudo completar la operación de proveedores.'); }
}
