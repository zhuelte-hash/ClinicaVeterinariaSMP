import { Component, computed, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Product, ProductDraft } from '../../models/admin.models';
import { AdminDataService } from '../../services/admin-data.service';
import { PageHeaderComponent } from '../../shared/page-header.component';
import { StatusBadgeComponent } from '../../shared/status-badge.component';

@Component({ selector: 'app-admin-productos', standalone: true, imports: [FormsModule, PageHeaderComponent, StatusBadgeComponent], templateUrl: './productos.component.html', styleUrl: '../../shared/admin-ui.css' })
export class ProductosComponent {
  readonly query = signal(''); readonly category = signal('Todas'); readonly modalOpen = signal(false);
  readonly editingId = signal<number | null>(null);
  readonly selected = signal<Product | null>(null);
  form: ProductDraft = this.emptyForm();
  readonly filtered = computed(() => { const q = this.query().toLowerCase(); return this.data.products().filter((p) => (!q || `${p.name} ${p.sku}`.toLowerCase().includes(q)) && (this.category() === 'Todas' || p.category === this.category())); });
  constructor(readonly data: AdminDataService) {}
  create(): void { this.editingId.set(null); this.form = this.emptyForm(); this.modalOpen.set(true); }
  edit(product: Product): void { this.editingId.set(product.id); this.form = { name: product.name, sku: product.sku, category: product.category, price: product.price, stock: product.stock, imageUrl: product.imageUrl }; this.modalOpen.set(true); }
  save(): void { const id = this.editingId(); if (id === null) this.data.addProduct(this.form); else this.data.updateProduct(id, this.form); this.modalOpen.set(false); this.form = this.emptyForm(); }
  delete(product: Product): void { if (confirm(`¿Eliminar ${product.name}? Esta acción no se puede deshacer.`)) this.data.deleteProduct(product.id); }
  onImageSelected(event: Event): void { const input = event.target as HTMLInputElement; const file = input.files?.[0]; if (!file) return; const reader = new FileReader(); reader.addEventListener('load', () => { if (typeof reader.result === 'string') this.form = { ...this.form, imageUrl: reader.result }; }); reader.readAsDataURL(file); }
  private emptyForm(): ProductDraft { return { name: '', sku: '', category: 'Alimentos', price: 0, stock: 0, imageUrl: '/logo.png' }; }
}
