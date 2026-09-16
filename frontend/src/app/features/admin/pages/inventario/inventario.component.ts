import { Component, computed, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { InventoryItem } from '../../models/admin.models';
import { AdminDataService } from '../../services/admin-data.service';
import { PageHeaderComponent } from '../../shared/page-header.component';

@Component({ selector: 'app-admin-inventario', standalone: true, imports: [FormsModule, PageHeaderComponent], templateUrl: './inventario.component.html', styleUrl: '../../shared/admin-ui.css' })
export class InventarioComponent {
  readonly query = signal(''); readonly onlyLow = signal(false); readonly editing = signal<InventoryItem | null>(null); stock = 0;
  readonly items = computed(() => { const q = this.query().toLowerCase(); return this.data.inventory().filter((i) => (!q || `${i.product} ${i.sku}`.toLowerCase().includes(q)) && (!this.onlyLow() || i.stock <= i.minimum)); });
  readonly lowCount = computed(() => this.data.inventory().filter((i) => i.stock <= i.minimum).length);
  constructor(readonly data: AdminDataService) {}
  edit(item: InventoryItem): void { this.editing.set(item); this.stock = item.stock; }
  save(): void { const item = this.editing(); if (item) this.data.updateStock(item.id, this.stock); this.editing.set(null); }
}
