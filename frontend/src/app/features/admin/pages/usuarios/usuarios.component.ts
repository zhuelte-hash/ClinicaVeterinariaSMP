import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { PageHeaderComponent } from '../../shared/page-header.component';
import { StatusBadgeComponent } from '../../shared/status-badge.component';
import { AdminUser, AdminUsersApiService, BackendRole, CreateAdminUser } from '../../services/admin-users-api.service';

@Component({
  selector: 'app-admin-usuarios',
  standalone: true,
  imports: [FormsModule, PageHeaderComponent, StatusBadgeComponent],
  templateUrl: './usuarios.component.html',
  styleUrl: '../../shared/admin-ui.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UsuariosComponent {
  private readonly api = inject(AdminUsersApiService);
  readonly open = signal(false);
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly error = signal('');
  readonly query = signal('');
  readonly users = signal<AdminUser[]>([]);
  readonly filteredUsers = computed(() => {
    const query = this.query().trim().toLowerCase();
    return this.users().filter((user) => !query || `${user.nombre} ${user.correo} ${user.tipo}`.toLowerCase().includes(query));
  });
  form: CreateAdminUser = { nombre: '', correo: '', contrasena: '', tipo: 'veterinario' };

  constructor() { this.load(); }

  load(): void {
    this.loading.set(true);
    this.api.getUsers().pipe(finalize(() => this.loading.set(false))).subscribe({
      next: (users) => { this.users.set(users); this.error.set(''); },
      error: (error: unknown) => this.error.set(this.errorText(error)),
    });
  }

  save(): void {
    if (!this.form.nombre || !this.form.correo || this.form.contrasena || this.form.contrasena.length < 8) {
      this.error.set('Completa nombre, correo y una contraseña de al menos 8 caracteres.');
      return;
    }
    if (this.form.tipo === 'veterinario' && !this.form.colegiatura) {
      this.error.set('La colegiatura es obligatoria para un veterinario.');
      return;
    }
    this.saving.set(true);
    this.api.createUser({ ...this.form }).pipe(finalize(() => this.saving.set(false))).subscribe({
      next: () => { this.open.set(false); this.resetForm(); this.load(); },
      error: (error: unknown) => this.error.set(this.errorText(error)),
    });
  }

  roleLabel(role: BackendRole): string {
    return { cliente: 'Cliente', veterinario: 'Veterinario', cajero: 'Cajero', administrador: 'Administrador' }[role];
  }

  resetForm(): void {
    this.form = { nombre: '', correo: '', contrasena: '', tipo: 'veterinario' };
  }

  private errorText(error: unknown): string {
    if (error instanceof HttpErrorResponse && typeof error.error?.detail === 'string') return error.error.detail;
    return 'No se pudo completar la operación.';
  }
}
