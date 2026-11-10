import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { NoticeService } from '../../../../core/services/notice.service';
import { AdminApiService, AdminCategory } from '../../services/admin-api.service';
import { PageHeaderComponent } from '../../shared/page-header.component';

@Component({ selector: 'app-admin-categorias', standalone: true, imports: [FormsModule, PageHeaderComponent], templateUrl: './categorias.component.html', styleUrl: '../../shared/admin-ui.css' })
export class CategoriasComponent {
  private readonly api = inject(AdminApiService);
  private readonly notice = inject(NoticeService);
  readonly categories = signal<AdminCategory[]>([]); readonly open = signal(false); readonly loading = signal(true); readonly saving = signal(false); readonly error = signal(''); readonly editing = signal<AdminCategory | null>(null);
  name = '';
  readonly removingId = signal<number | null>(null);
  constructor() { this.load(); }
  load(): void { this.loading.set(true); this.api.getCategories().pipe(finalize(() => this.loading.set(false))).subscribe({ next: (items) => { this.categories.set(items); this.error.set(''); }, error: (error: unknown) => this.error.set(this.errorText(error)) }); }
  create(): void { this.editing.set(null); this.name = ''; this.error.set(''); this.open.set(true); }
  edit(category: AdminCategory): void { this.editing.set(category); this.name = category.nombre; this.error.set(''); this.open.set(true); }
  close(): void { if (!this.saving()) this.open.set(false); }
  save(): void { if (this.saving() || this.name.trim().length < 2 || this.name.trim().length > 100) return; this.saving.set(true); this.error.set(''); const editing = this.editing(); const request = editing ? this.api.updateCategory(editing.id, this.name.trim()) : this.api.createCategory(this.name.trim()); request.pipe(finalize(() => this.saving.set(false))).subscribe({ next: (item) => { this.categories.update((items) => (editing ? items.map((current) => current.id === item.id ? item : current) : [...items, item]).sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'))); this.open.set(false); this.notice.show(editing ? 'Categoría actualizada' : 'Categoría creada'); }, error: (error: unknown) => this.error.set(this.errorText(error)) }); }
  remove(category: AdminCategory): void { if (this.removingId() !== null || category.productos || !window.confirm(`¿Eliminar la categoría ${category.nombre}?`)) return; this.removingId.set(category.id); this.api.deleteCategory(category.id).pipe(finalize(() => this.removingId.set(null))).subscribe({ next: () => { this.categories.update((items) => items.filter((item) => item.id !== category.id)); this.error.set(''); this.notice.show('Categoría eliminada'); }, error: (error: unknown) => this.error.set(this.errorText(error)) }); }
  private errorText(error: unknown): string { return error instanceof HttpErrorResponse && typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudo completar la operación.'; }
}
