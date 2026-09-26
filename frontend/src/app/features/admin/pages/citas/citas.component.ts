import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { AdminApiService, AdminAppointment } from '../../services/admin-api.service';
import { PageHeaderComponent } from '../../shared/page-header.component';

@Component({ selector: 'app-admin-citas', standalone: true, imports: [FormsModule, PageHeaderComponent], templateUrl: './citas.component.html', styleUrl: '../../shared/admin-ui.css', changeDetection: ChangeDetectionStrategy.OnPush })
export class CitasComponent {
  private readonly api = inject(AdminApiService);
  readonly date = signal(new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima' }).format(new Date())); readonly status = signal(''); readonly appointments = signal<AdminAppointment[]>([]); readonly loading = signal(true); readonly error = signal('');
  constructor() { this.load(); }
  load(): void { this.loading.set(true); this.api.getAppointments(this.date() || undefined, this.status() || undefined).pipe(finalize(() => this.loading.set(false))).subscribe({ next: (items) => { this.appointments.set(items); this.error.set(''); }, error: (error: unknown) => this.error.set(this.errorText(error)) }); }
  formatDate(value: string): string { return new Intl.DateTimeFormat('es-PE', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Lima' }).format(new Date(value)); }
  private errorText(error: unknown): string { return error instanceof HttpErrorResponse && typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudieron consultar las citas.'; }
}
