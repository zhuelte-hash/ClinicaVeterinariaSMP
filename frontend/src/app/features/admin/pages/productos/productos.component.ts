import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize, forkJoin } from 'rxjs';
import { NoticeService } from '../../../../core/services/notice.service';
import { AdminApiService, AdminProduct, CatalogOption, ProductCreate } from '../../services/admin-api.service';
import { PageHeaderComponent } from '../../shared/page-header.component';
import { StatusBadgeComponent } from '../../shared/status-badge.component';
import { OperationsApiService, Unit } from '../../services/operations-api.service';
import { publicImageUrl } from '../../../../core/utils/public-image-url';

@Component({ selector: 'app-admin-productos', standalone: true, imports: [FormsModule, PageHeaderComponent, StatusBadgeComponent], templateUrl: './productos.component.html', styleUrl: '../../shared/admin-ui.css', changeDetection: ChangeDetectionStrategy.OnPush })
export class ProductosComponent {
  private readonly api = inject(AdminApiService);
  private readonly notice = inject(NoticeService);
  private readonly operations = inject(OperationsApiService);
  readonly units = signal<Unit[]>([]);
  readonly query = signal(''); readonly category = signal(''); readonly products = signal<AdminProduct[]>([]); readonly categories = signal<CatalogOption[]>([]); readonly providers = signal<CatalogOption[]>([]); readonly loading = signal(true); readonly saving = signal(false); readonly imageUploading = signal(false); readonly deletingId = signal<number | null>(null); readonly pendingDelete = signal<AdminProduct | null>(null); readonly selected = signal<AdminProduct | null>(null); readonly modalOpen = signal(false); readonly editingId = signal<number | null>(null); readonly error = signal('');
  form: ProductCreate = this.emptyForm();
  speciesText = '';
  readonly onlyMissingPhotos = signal(false);
  readonly failedImages = signal<ReadonlySet<string>>(new Set());
  readonly imageUrl = publicImageUrl;
  readonly imageDrafts = signal<Record<number, string>>({});
  readonly savingImages = signal<ReadonlySet<number>>(new Set());
  imageDraft(product: AdminProduct): string { return this.imageDrafts()[product.id] ?? (this.needsPhoto(product) ? '' : product.imagen_url); }
  setImageDraft(id: number, url: string): void { this.imageDrafts.update(drafts => ({ ...drafts, [id]: url })); }
  saveImageUrl(product: AdminProduct): void {
    if (this.savingImages().has(product.id)) return;
    const url = this.imageDraft(product).trim();
    try {
      if (!['http:', 'https:'].includes(new URL(url).protocol)) throw new Error();
    } catch { this.error.set('Ingresa una URL directa de imagen que comience con https:// o http://.'); return; }
    if (url.length > 500) { this.error.set('La URL de la imagen debe tener como máximo 500 caracteres.'); return; }
    this.error.set('');
    this.savingImages.update(ids => new Set([...ids, product.id]));
    this.api.updateProduct(product.id, { imagen_url: url }).pipe(finalize(() => this.savingImages.update(ids => { const next = new Set(ids); next.delete(product.id); return next; }))).subscribe({
      next: updated => {
        this.failedImages.update(urls => { const next = new Set(urls); next.delete(updated.imagen_url); return next; });
        this.products.update(items => items.map(item => item.id === updated.id ? updated : item));
        this.notice.show(`Imagen de ${updated.nombre} guardada correctamente`);
      },
      error: (error: unknown) => this.error.set(this.errorText(error)),
    });
  }
  readonly missingPhotoCount = computed(() => this.products().filter(item => this.needsPhoto(item)).length);
  needsPhoto(product: AdminProduct): boolean { return !product.imagen_url || ['/logo.png', '/catalogo/producto-sin-foto.svg'].includes(product.imagen_url) || this.failedImages().has(product.imagen_url); }
  readonly filtered = computed(() => { const q = this.query().trim().toLowerCase(); return this.products().filter((item) => (!q || `${item.nombre} ${item.sku} ${item.categoria_nombre}`.toLowerCase().includes(q)) && (!this.category() || item.categoria_id === Number(this.category())) && (!this.onlyMissingPhotos() || this.needsPhoto(item))); });
  constructor() { this.load(); this.operations.productUnits().subscribe({ next: rows => this.units.set(rows), error: error => this.error.set(this.errorText(error)) }); }
  load(): void { this.loading.set(true); forkJoin({ products: this.api.getProducts(), catalog: this.api.getProductCatalog() }).pipe(finalize(() => this.loading.set(false))).subscribe({ next: ({ products, catalog }) => { this.products.set(products); this.categories.set(catalog.categorias); this.providers.set(catalog.proveedores); if (!this.form.categoria_id && catalog.categorias[0]) this.form.categoria_id = catalog.categorias[0].id; if (!this.form.proveedor_id && catalog.proveedores[0]) this.form.proveedor_id = catalog.proveedores[0].id; this.error.set(''); }, error: (error: unknown) => this.error.set(this.errorText(error)) }); }
  create(): void { this.editingId.set(null); this.form = this.emptyForm(); this.speciesText = ''; this.modalOpen.set(true); }
  edit(product: AdminProduct): void { this.error.set(''); this.editingId.set(product.id); this.form = { categoria_id: product.categoria_id, proveedor_id: product.proveedor_id, sku: product.sku, nombre: product.nombre, precio_venta: product.precio_venta, stock_actual: product.stock_actual, stock_minimo: product.stock_minimo, imagen_url: product.imagen_url, descripcion: product.descripcion, especies: product.especies, unidad_medida: product.unidad_medida, fraccionable: product.fraccionable, requiere_vencimiento: product.requiere_vencimiento, costo_unitario: product.costo_unitario, marca: product.marca, presentacion: product.presentacion, subcategoria: product.subcategoria }; this.speciesText = product.especies.join(', '); this.modalOpen.set(true); }
  closeForm(): void { if (!this.saving()) this.modalOpen.set(false); }
  save(): void { if (this.saving() || this.imageUploading()) return; const id = this.editingId(); if (!this.form.categoria_id) { this.error.set('Selecciona una categoría.'); return; } this.form.especies = this.speciesText.split(',').map(value => value.trim()).filter(Boolean); this.saving.set(true); const { stock_actual, ...changes } = this.form; const request = id === null ? this.api.createProduct(this.form) : this.api.updateProduct(id, changes); request.pipe(finalize(() => this.saving.set(false))).subscribe({ next: (product) => { this.products.update((items) => id === null ? [...items, product] : items.map((item) => item.id === product.id ? product : item)); this.modalOpen.set(false); this.error.set(''); this.notice.show(id === null ? 'Producto creado correctamente' : 'Producto actualizado correctamente'); }, error: (error: unknown) => this.error.set(this.errorText(error)) }); }
  confirmDelete(product: AdminProduct): void { this.pendingDelete.set(product); this.error.set(''); }
  cancelDelete(): void { if (this.deletingId() === null) this.pendingDelete.set(null); }
  deleteConfirmed(): void { const product = this.pendingDelete(); if (!product || this.deletingId() !== null) return; this.deletingId.set(product.id); this.api.deactivateProduct(product.id).pipe(finalize(() => this.deletingId.set(null))).subscribe({ next: () => { this.products.update((items) => items.filter((item) => item.id !== product.id)); this.pendingDelete.set(null); this.notice.show('Producto desactivado correctamente'); }, error: (error: unknown) => this.error.set(this.errorText(error)) }); }
  onImageSelected(event: Event): void { const file = (event.target as HTMLInputElement).files?.[0]; if (!file) return; this.imageUploading.set(true); this.api.uploadProductImage(file).pipe(finalize(() => this.imageUploading.set(false))).subscribe({ next: ({ url }) => { this.form.imagen_url = url; this.notice.show('Imagen cargada correctamente'); }, error: (error: unknown) => this.error.set(this.errorText(error)) }); }
  unitChanged(): void { this.form.fraccionable = this.units().find(unit => unit.codigo === this.form.unidad_medida)?.fraccionable ?? false; }
  priceLabel(product: AdminProduct): string { return product.precio_venta === null ? 'Precio por confirmar' : 'S/ ' + product.precio_venta.toFixed(2); }
  imageError(event: Event, product?: AdminProduct): void { const image = event.target as HTMLImageElement; if (!image.src.endsWith('/catalogo/producto-sin-foto.svg')) { if (product) this.failedImages.update(urls => new Set([...urls, product.imagen_url])); image.src = '/catalogo/producto-sin-foto.svg'; } }
  private emptyForm(): ProductCreate { return { categoria_id: this.categories()[0]?.id ?? 0, proveedor_id: null, sku: '', nombre: '', precio_venta: null, stock_actual: 0, stock_minimo: 0, imagen_url: '/catalogo/producto-sin-foto.svg', unidad_medida: 'unidad', fraccionable: false, requiere_vencimiento: false, costo_unitario: 0 }; }
  private errorText(error: unknown): string { return error instanceof HttpErrorResponse && typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudo actualizar el producto.'; }
}
