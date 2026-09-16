import { Component, computed, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SaleDraft } from '../../models/admin.models';
import { AdminDataService } from '../../services/admin-data.service';
import { PageHeaderComponent } from '../../shared/page-header.component';
import { StatusBadgeComponent } from '../../shared/status-badge.component';

@Component({ selector: 'app-admin-ventas', standalone: true, imports: [FormsModule, PageHeaderComponent, StatusBadgeComponent], templateUrl: './ventas.component.html', styleUrl: '../../shared/admin-ui.css' })
export class VentasComponent {
  readonly open = signal(false); readonly query = signal('');
  form: SaleDraft = { client: '', total: 0, method: 'Efectivo' };
  readonly filtered = computed(() => { const q = this.query().toLowerCase(); return this.data.sales().filter((s) => `${s.code} ${s.client}`.toLowerCase().includes(q)); });
  readonly total = computed(() => this.filtered().reduce((sum, item) => sum + item.total, 0));
  constructor(readonly data: AdminDataService) {}
  save(): void { this.data.addSale(this.form); this.form = { client: '', total: 0, method: 'Efectivo' }; this.open.set(false); }
}
