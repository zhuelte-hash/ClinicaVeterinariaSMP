import { Component, computed, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Appointment, AppointmentDraft } from '../../models/admin.models';
import { AdminDataService } from '../../services/admin-data.service';
import { PageHeaderComponent } from '../../shared/page-header.component';
import { StatusBadgeComponent } from '../../shared/status-badge.component';

@Component({ selector: 'app-admin-citas', standalone: true, imports: [FormsModule, PageHeaderComponent, StatusBadgeComponent], templateUrl: './citas.component.html', styleUrl: '../../shared/admin-ui.css' })
export class CitasComponent {
  readonly open = signal(false); readonly status = signal('Todas');
  form: AppointmentDraft = { date: '2026-09-15', time: '09:00', patient: '', owner: '', service: 'Consulta general', veterinarian: 'Dra. Rojas' };
  readonly appointments = computed(() => this.data.appointments().filter((a) => this.status() === 'Todas' || a.status === this.status()).sort((a, b) => `${a.date}${a.time}`.localeCompare(`${b.date}${b.time}`)));
  constructor(readonly data: AdminDataService) {}
  save(): void { this.data.addAppointment(this.form); this.open.set(false); this.form = { date: '2026-09-15', time: '09:00', patient: '', owner: '', service: 'Consulta general', veterinarian: 'Dra. Rojas' }; }
  complete(item: Appointment): void { this.data.setAppointmentStatus(item.id, 'Completada'); }
}
