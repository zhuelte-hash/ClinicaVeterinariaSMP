import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { NoticeService } from '../../../../core/services/notice.service';
import { AdminApiService, AdminClient } from '../../services/admin-api.service';
import { AdminUsersApiService, CreateAdminUser, UpdateAdminUser } from '../../services/admin-users-api.service';
import { PageHeaderComponent } from '../../shared/page-header.component';

@Component({
  selector: 'app-admin-clientes',
  standalone: true,
  imports: [FormsModule, RouterLink, PageHeaderComponent],
  templateUrl: './clientes.component.html',
  styleUrl: '../../shared/admin-ui.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientesComponent {
  private readonly api = inject(AdminApiService);
  private readonly usersApi = inject(AdminUsersApiService);
  private readonly notice = inject(NoticeService);
  readonly clients = signal<AdminClient[]>([]);
  readonly query = signal('');
  readonly onlyWithAppointments = signal(false);
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly deletingId = signal<number | null>(null);
  readonly editing = signal<AdminClient | null>(null);
  readonly formOpen = signal(false);
  readonly error = signal('');
  readonly filtered = computed(() => {
    const query = this.query().trim().toLocaleLowerCase('es');
    return this.clients().filter((client) =>
      (!this.onlyWithAppointments() || client.citas > 0)
      && (!query || `${client.nombre} ${client.correo} ${client.telefono ?? ''}`.toLocaleLowerCase('es').includes(query)));
  });
  readonly withAppointments = computed(() => this.clients().filter((client) => client.citas > 0).length);
  readonly totalAppointments = computed(() => this.clients().reduce((total, client) => total + client.citas, 0));
  form = this.emptyForm();

  constructor() { this.load(); }

  load(): void {
    this.loading.set(true);
    this.api.getClients().pipe(finalize(() => this.loading.set(false))).subscribe({
      next: (clients) => { this.clients.set(clients); this.error.set(''); },
      error: (error: unknown) => this.error.set(this.errorText(error)),
    });
  }

  create(): void { this.editing.set(null); this.form = this.emptyForm(); this.error.set(''); this.formOpen.set(true); }
  edit(client: AdminClient): void {
    this.editing.set(client);
    this.form = { nombre: client.nombre, correo: client.correo, telefono: client.telefono ?? '', direccion: client.direccion ?? '', contrasena: '' };
    this.error.set('');
    this.formOpen.set(true);
  }
  close(): void { if (!this.saving()) this.formOpen.set(false); }

  save(): void {
    if (this.saving()) return;
    if (!this.form.nombre.trim() || !this.form.correo.trim() || (!this.editing() && this.form.contrasena.length < 8)
      || (this.editing() && this.form.contrasena && this.form.contrasena.length < 8)) {
      this.error.set('Completa nombre, correo y contraseña de al menos 8 caracteres para cuentas nuevas.');
      return;
    }
    const editing = this.editing();
    const data = {
      nombre: this.form.nombre.trim(), correo: this.form.correo.trim(),
      telefono: this.form.telefono.trim(), direccion: this.form.direccion.trim(),
    };
    const request = editing
      ? this.usersApi.updateUser(editing.id, { ...data, ...(this.form.contrasena ? { contrasena: this.form.contrasena } : {}) } satisfies UpdateAdminUser)
      : this.usersApi.createUser({ ...data, contrasena: this.form.contrasena, tipo: 'cliente' } satisfies CreateAdminUser);
    this.saving.set(true);
    this.error.set('');
    request.pipe(finalize(() => this.saving.set(false))).subscribe({
      next: () => { this.formOpen.set(false); this.load(); this.notice.show(editing ? 'Cliente actualizado' : 'Cliente registrado'); },
      error: (error: unknown) => this.error.set(this.errorText(error)),
    });
  }

  deleteClient(client: AdminClient): void {
    if (client.mascotas > 0 || client.citas > 0 || this.deletingId() !== null
      || !window.confirm(`¿Eliminar la cuenta de ${client.nombre}?`)) return;
    this.deletingId.set(client.id);
    this.error.set('');
    this.usersApi.deleteUser(client.id).pipe(finalize(() => this.deletingId.set(null))).subscribe({
      next: () => { this.clients.update((items) => items.filter((item) => item.id !== client.id)); this.notice.show('Cliente eliminado'); },
      error: (error: unknown) => this.error.set(this.errorText(error)),
    });
  }

  formatDate(value: string): string {
    return new Intl.DateTimeFormat('es-PE', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Lima' }).format(new Date(value));
  }

  private emptyForm() { return { nombre: '', correo: '', telefono: '', direccion: '', contrasena: '' }; }

  private errorText(error: unknown): string {
    if (error instanceof HttpErrorResponse && typeof error.error?.detail === 'string') return error.error.detail;
    if (error instanceof HttpErrorResponse && Array.isArray(error.error?.detail)) {
      return error.error.detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join(' ') || 'Revisa los datos ingresados.';
    }
    return 'No se pudo completar la operación. Intenta nuevamente.';
  }
}
