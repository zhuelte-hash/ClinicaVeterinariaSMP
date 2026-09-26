import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize, forkJoin } from 'rxjs';
import { NoticeService } from '../../../../core/services/notice.service';
import { AdminApiService, AdminProduct, CatalogOption, ProductCreate } from '../../services/admin-api.service';
import { PageHeaderComponent } from '../../shared/page-header.component';
import { StatusBadgeComponent } from '../../shared/status-badge.component';

@Component({ selector: 'app-admin-productos', standalone: true, imports: [FormsModule, PageHeaderComponent, StatusBadgeComponent], templateUrl: './productos.component.html', styleUrl: '../../shared/admin-ui.css', changeDetection: ChangeDetectionStrategy.OnPush })
export class ProductosComponent {
  private readonly api = inject(AdminApiService);
  private readonly notice = inject(NoticeService);
  readonly query = signal(''); readonly category = signal(''); readonly products = signal<AdminProduct[]>([]); readonly categories = signal<CatalogOption[]>([]); readonly providers = signal<CatalogOption[]>([]); readonly loading = signal(true); readonly saving = signal(false); readonly imageUploading = signal(false); readonly deletingId = signal<number | null>(null); readonly pendingDelete = signal<AdminProduct | null>(null); readonly selected = signal<AdminProduct | null>(null); readonly modalOpen = signal(false); readonly editingId = signal<number | null>(null); readonly error = signal('');
  form: ProductCreate = this.emptyForm();
  readonly filtered = computed(() => { const q = this.query().trim().toLowerCase(); return this.products().filter((item) => (!q || `${item.nombre} ${item.sku} ${item.categoria_nombre}`.toLowerCase().includes(q)) && (!this.category() || item.categoria_id === Number(this.category()))); });
  constructor() { this.load(); }
  load(): void { this.loading.set(true); forkJoin({ products: this.api.getProducts(), catalog: this.api.getProductCatalog() }).pipe(finalize(() => this.loading.set(false))).subscribe({ next: ({ products, catalog }) => { this.products.set(products); this.categories.set(catalog.categorias); this.providers.set(catalog.proveedores); if (!this.form.categoria_id && catalog.categorias[0]) this.form.categoria_id = catalog.categorias[0].id; if (!this.form.proveedor_id && catalog.proveedores[0]) this.form.proveedor_id = catalog.proveedores[0].id; this.error.set(''); }, error: (error: unknown) => this.error.set(this.errorText(error)) }); }
  create(): void { this.editingId.set(null); this.form = this.emptyForm(); this.modalOpen.set(true); }
  edit(product: AdminProduct): void { this.editingId.set(product.id); this.form = { categoria_id: product.categoria_id, proveedor_id: 0, sku: product.sku, nombre: product.nombre, precio_venta: product.precio_venta, stock_actual: product.stock_actual, stock_minimo: product.stock_minimo, imagen_url: product.imagen_url }; this.modalOpen.set(true); }
  closeForm(): void { if (!this.saving()) this.modalOpen.set(false); }
  save(): void { if (this.saving() || this.imageUploading()) return; const id = this.editingId(); if (id === null && (!this.form.categoria_id || !this.form.proveedor_id)) { this.error.set('Selecciona una categoría y un proveedor.'); return; } this.saving.set(true); const request = id === null ? this.api.createProduct(this.form) : this.api.updateProduct(id, { sku: this.form.sku, nombre: this.form.nombre, precio_venta: this.form.precio_venta, stock_minimo: this.form.stock_minimo, imagen_url: this.form.imagen_url }); request.pipe(finalize(() => this.saving.set(false))).subscribe({ next: (product) => { this.products.update((items) => id === null ? [...items, product] : items.map((item) => item.id === product.id ? product : item)); this.modalOpen.set(false); this.notice.show(id === null ? 'Producto creado correctamente' : 'Producto actualizado correctamente'); }, error: (error: unknown) => this.error.set(this.errorText(error)) }); }
  confirmDelete(product: AdminProduct): void { this.pendingDelete.set(product); this.error.set(''); }
  cancelDelete(): void { if (this.deletingId() === null) this.pendingDelete.set(null); }
  deleteConfirmed(): void { const product = this.pendingDelete(); if (!product || this.deletingId() !== null) return; this.deletingId.set(product.id); this.api.deactivateProduct(product.id).pipe(finalize(() => this.deletingId.set(null))).subscribe({ next: () => { this.products.update((items) => items.filter((item) => item.id !== product.id)); this.pendingDelete.set(null); this.notice.show('Producto desactivado correctamente'); }, error: (error: unknown) => this.error.set(this.errorText(error)) }); }
  onImageSelected(event: Event): void { const file = (event.target as HTMLInputElement).files?.[0]; if (!file) return; this.imageUploading.set(true); this.api.uploadProductImage(file).pipe(finalize(() => this.imageUploading.set(false))).subscribe({ next: ({ url }) => { this.form.imagen_url = url; this.notice.show('Imagen cargada correctamente'); }, error: (error: unknown) => this.error.set(this.errorText(error)) }); }
  private emptyForm(): ProductCreate { return { categoria_id: this.categories()[0]?.id ?? 0, proveedor_id: this.providers()[0]?.id ?? 0, sku: '', nombre: '', precio_venta: 0, stock_actual: 0, stock_minimo: 0, imagen_url: '/logo.png' }; }
  private errorText(error: unknown): string { return error instanceof HttpErrorResponse && typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudo actualizar el producto.'; }
}
