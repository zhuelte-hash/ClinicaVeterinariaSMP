import { Component, computed, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AdminUserDraft } from '../../models/admin.models';
import { AdminDataService } from '../../services/admin-data.service';
import { PageHeaderComponent } from '../../shared/page-header.component';
import { StatusBadgeComponent } from '../../shared/status-badge.component';

@Component({ selector: 'app-admin-usuarios', standalone: true, imports: [FormsModule, PageHeaderComponent, StatusBadgeComponent], templateUrl: './usuarios.component.html', styleUrl: '../../shared/admin-ui.css' })
export class UsuariosComponent {
  readonly open = signal(false); readonly query = signal('');
  form: AdminUserDraft = { name: '', email: '', role: 'Recepcionista' };
  readonly users = computed(() => { const q = this.query().toLowerCase(); return this.data.users().filter((u) => `${u.name} ${u.email} ${u.role}`.toLowerCase().includes(q)); });
  constructor(readonly data: AdminDataService) {}
  save(): void { this.data.addUser(this.form); this.form = { name: '', email: '', role: 'Recepcionista' }; this.open.set(false); }
}
