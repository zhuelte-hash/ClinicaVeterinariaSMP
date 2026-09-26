import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { AuthService } from '../../../../core/auth/auth.service';
import { PageHeaderComponent } from '../../shared/page-header.component';
import { StatusBadgeComponent } from '../../shared/status-badge.component';
import {
  AdminUser,
  AdminUsersApiService,
  BackendRole,
  CreateAdminUser,
  UpdateAdminUser,
} from '../../services/admin-users-api.service';
import { AdminApiService, Role, RolePermission } from '../../services/admin-api.service';

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
  private readonly auth = inject(AuthService);
  private readonly permissionsApi = inject(AdminApiService);
  readonly open = signal(false);
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly deletingId = signal<number | null>(null);
  readonly error = signal('');
  readonly query = signal('');
  readonly users = signal<AdminUser[]>([]);
  readonly editingUser = signal<AdminUser | null>(null);
  readonly permissions = signal<RolePermission[]>([]);
  readonly permissionsLoading = signal(true);
  readonly permissionSaving = signal('');
  readonly selectedPermissionRole = signal<Role>('administrador');
  readonly permissionModules = [
    { key: 'productos', label: 'Productos e inventario' }, { key: 'ventas', label: 'Ventas' },
    { key: 'usuarios', label: 'Usuarios' }, { key: 'citas', label: 'Citas' },
    { key: 'mascotas', label: 'Mascotas' }, { key: 'historias_clinicas', label: 'Historias clínicas' },
  ];
  readonly permissionRoles: { key: Role; label: string }[] = [
    { key: 'administrador', label: 'Administrador' }, { key: 'cajero', label: 'Cajero' },
    { key: 'veterinario', label: 'Veterinario' }, { key: 'cliente', label: 'Cliente' },
  ];
  readonly filteredUsers = computed(() => {
    const query = this.query().trim().toLowerCase();
    return this.users().filter((user) => !query || `${user.nombre} ${user.correo} ${user.tipo}`.toLowerCase().includes(query));
  });
  form: CreateAdminUser = { nombre: '', correo: '', contrasena: '', tipo: 'veterinario' };

  constructor() { this.load(); this.loadPermissions(); }

  load(): void {
    this.loading.set(true);
    this.api.getUsers().pipe(finalize(() => this.loading.set(false))).subscribe({
      next: (users) => { this.users.set(users); this.error.set(''); },
      error: (error: unknown) => this.error.set(this.errorText(error)),
    });
  }

  save(): void {
    const editing = this.editingUser();
    if (!this.form.nombre.trim() || !this.form.correo.trim()) {
      this.error.set('Completa el nombre y el correo.');
      return;
    }
    if ((!editing && this.form.contrasena.length < 8) || (editing && this.form.contrasena.length > 0 && this.form.contrasena.length < 8)) {
      this.error.set('La contraseña debe tener al menos 8 caracteres.');
      return;
    }
    if (this.form.tipo === 'veterinario' && !this.form.colegiatura) {
      this.error.set('La colegiatura es obligatoria para un veterinario.');
      return;
    }
    this.saving.set(true);
    const request = editing
      ? this.api.updateUser(editing.id, this.updatePayload(editing))
      : this.api.createUser({ ...this.form });
    request.pipe(finalize(() => this.saving.set(false))).subscribe({
      next: () => { this.closeForm(); this.load(); },
      error: (error: unknown) => this.error.set(this.errorText(error)),
    });
  }

  openCreate(): void {
    this.editingUser.set(null);
    this.resetForm();
    this.error.set('');
    this.open.set(true);
  }

  openEdit(user: AdminUser): void {
    this.editingUser.set(user);
    this.form = {
      nombre: user.nombre,
      correo: user.correo,
      contrasena: '',
      tipo: user.tipo,
      telefono: user.telefono ?? '',
      colegiatura: user.colegiatura ?? '',
      especialidad: user.especialidad ?? '',
    };
    this.error.set('');
    this.open.set(true);
  }

  closeForm(): void {
    this.open.set(false);
    this.editingUser.set(null);
    this.resetForm();
  }

  deleteUser(user: AdminUser): void {
    if (this.isCurrentUser(user) || !confirm(`¿Eliminar a ${user.nombre}? Esta acción no se puede deshacer.`)) return;
    this.deletingId.set(user.id);
    this.error.set('');
    this.api.deleteUser(user.id).pipe(finalize(() => this.deletingId.set(null))).subscribe({
      next: () => this.users.update((users) => users.filter((item) => item.id !== user.id)),
      error: (error: unknown) => this.error.set(this.errorText(error)),
    });
  }

  isCurrentUser(user: AdminUser): boolean {
    return this.auth.currentUser()?.id === user.id;
  }

  loadPermissions(): void {
    this.permissionsLoading.set(true);
    this.permissionsApi.getPermissions().pipe(finalize(() => this.permissionsLoading.set(false))).subscribe({
      next: (permissions) => this.permissions.set(permissions),
      error: (error: unknown) => this.error.set(this.errorText(error)),
    });
  }

  permission(role: Role, module: string): RolePermission | undefined { return this.permissions().find((item) => item.rol === role && item.modulo === module); }

  updatePermission(role: Role, module: string, field: keyof Pick<RolePermission, 'puede_ver' | 'puede_crear' | 'puede_editar' | 'puede_eliminar' | 'puede_aprobar'>, checked: boolean): void {
    const current = this.permission(role, module);
    if (!current || this.permissionSaving()) return;
    const next = { puede_ver: current.puede_ver, puede_crear: current.puede_crear, puede_editar: current.puede_editar, puede_eliminar: current.puede_eliminar, puede_aprobar: current.puede_aprobar, [field]: checked };
    if (checked && field !== 'puede_ver') next.puede_ver = true;
    if (!next.puede_ver) { next.puede_crear = false; next.puede_editar = false; next.puede_eliminar = false; next.puede_aprobar = false; }
    const key = `${role}:${module}`;
    this.permissionSaving.set(key);
    this.permissionsApi.updatePermission(role, module, next).pipe(finalize(() => this.permissionSaving.set(''))).subscribe({
      next: (updated) => this.permissions.update((items) => items.map((item) => item.rol === role && item.modulo === module ? updated : item)),
      error: (error: unknown) => this.error.set(this.errorText(error)),
    });
  }

  roleLabel(role: BackendRole): string {
    return { cliente: 'Cliente', veterinario: 'Veterinario', cajero: 'Cajero', administrador: 'Administrador' }[role];
  }

  resetForm(): void {
    this.form = { nombre: '', correo: '', contrasena: '', tipo: 'veterinario' };
  }

  private updatePayload(user: AdminUser): UpdateAdminUser {
    const data: UpdateAdminUser = {
      nombre: this.form.nombre.trim(),
      correo: this.form.correo.trim(),
    };
    if (this.form.contrasena) data.contrasena = this.form.contrasena;
    if (user.tipo === 'cliente') data.telefono = this.form.telefono?.trim() ?? '';
    if (user.tipo === 'veterinario') {
      data.colegiatura = this.form.colegiatura?.trim() ?? '';
      data.especialidad = this.form.especialidad?.trim() ?? '';
    }
    return data;
  }

  private errorText(error: unknown): string {
    if (error instanceof HttpErrorResponse && typeof error.error?.detail === 'string') return error.error.detail;
    if (error instanceof HttpErrorResponse && Array.isArray(error.error?.detail)) {
      return error.error.detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join(' ') || 'Los datos ingresados no son válidos.';
    }
    return 'No se pudo completar la operación.';
  }
}
