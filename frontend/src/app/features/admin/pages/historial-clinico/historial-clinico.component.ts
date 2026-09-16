import { Component, computed, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ClinicalRecordDraft } from '../../models/admin.models';
import { AdminDataService } from '../../services/admin-data.service';
import { PageHeaderComponent } from '../../shared/page-header.component';

@Component({ selector: 'app-admin-historial-clinico', standalone: true, imports: [FormsModule, PageHeaderComponent], templateUrl: './historial-clinico.component.html', styleUrl: '../../shared/admin-ui.css' })
export class HistorialClinicoComponent {
  readonly open = signal(false); readonly query = signal(''); readonly expanded = signal<number | null>(null);
  form: ClinicalRecordDraft = { patient: '', species: 'Canino', owner: '', diagnosis: '', treatment: '', veterinarian: 'Dra. Rojas' };
  readonly records = computed(() => { const q = this.query().toLowerCase(); return this.data.records().filter((r) => `${r.patient} ${r.owner}`.toLowerCase().includes(q)); });
  constructor(readonly data: AdminDataService) {}
  save(): void { this.data.addRecord(this.form); this.open.set(false); this.form = { patient: '', species: 'Canino', owner: '', diagnosis: '', treatment: '', veterinarian: 'Dra. Rojas' }; }
}
