import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';
import { VeterinarianApiService } from './veterinarian-api.service';
import { VeterinarianClient, VeterinarianClientPayload } from './veterinarian.models';

@Component({
  selector: 'app-veterinarian-clients',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './veterinarian-clients.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class VeterinarianClientsComponent {
  private readonly api = inject(VeterinarianApiService);
  private readonly formBuilder = inject(FormBuilder);

  readonly clients = signal<VeterinarianClient[]>([]);
  readonly query = signal('');
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly formOpen = signal(false);
  readonly editingClient = signal<VeterinarianClient | null>(null);
  readonly errorMessage = signal('');
  readonly successMessage = signal('');
  readonly filteredClients = computed(() => {
    const query = this.query().trim().toLocaleLowerCase('es');
    return this.clients().filter((client) =>
      !query || `${client.nombre} ${client.correo} ${client.telefono || ''} ${client.direccion || ''}`.toLocaleLowerCase('es').includes(query),
    );
  });
  readonly clientsWithPhone = computed(() => this.clients().filter((client) => !!client.telefono).length);
  readonly clientsWithAddress = computed(() => this.clients().filter((client) => !!client.direccion).length);

  readonly form = this.formBuilder.nonNullable.group({
    nombre: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(150)]],
    correo: ['', [Validators.required, Validators.email, Validators.maxLength(254)]],
    telefono: ['', Validators.maxLength(30)],
    direccion: ['', Validators.maxLength(255)],
    contrasena: ['', Validators.maxLength(72)],
  });

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api.getClients().pipe(finalize(() => this.loading.set(false))).subscribe({
      next: (clients) => {
        this.clients.set(clients);
        this.errorMessage.set('');
      },
      error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
  }

  setQuery(value: string): void {
    this.query.set(value);
  }

  openCreate(): void {
    this.editingClient.set(null);
    this.form.reset();
    this.errorMessage.set('');
    this.successMessage.set('');
    this.formOpen.set(true);
  }

  openEdit(client: VeterinarianClient): void {
    this.editingClient.set(client);
    this.form.reset({
      nombre: client.nombre,
      correo: client.correo,
      telefono: client.telefono || '',
      direccion: client.direccion || '',
      contrasena: '',
    });
    this.errorMessage.set('');
    this.successMessage.set('');
    this.formOpen.set(true);
  }

  closeForm(): void {
    if (this.saving()) return;
    this.formOpen.set(false);
    this.editingClient.set(null);
    this.form.reset();
  }

  save(): void {
    const editing = this.editingClient();
    const password = this.form.controls.contrasena.value;
    if (this.form.invalid || (!editing && password.length < 8) || (password.length > 0 && password.length < 8)) {
      this.form.markAllAsTouched();
      this.errorMessage.set('Revisa los campos. La contraseña debe tener entre 8 y 72 caracteres.');
      return;
    }

    const values = this.form.getRawValue();
    const payload: VeterinarianClientPayload = {
      nombre: values.nombre.trim(),
      correo: values.correo.trim().toLowerCase(),
      telefono: values.telefono.trim(),
      direccion: values.direccion.trim(),
    };
    if (password) payload.contrasena = password;

    this.saving.set(true);
    this.errorMessage.set('');
    const request = editing
      ? this.api.updateClient(editing.id, payload)
      : this.api.createClient({ ...payload, contrasena: password });
    request.pipe(finalize(() => this.saving.set(false))).subscribe({
      next: (client) => {
        if (editing) {
          this.clients.update((clients) => clients.map((item) => item.id === client.id ? client : item));
        } else {
          this.clients.update((clients) => [...clients, client].sort((a, b) => a.nombre.localeCompare(b.nombre, 'es')));
        }
        this.formOpen.set(false);
        this.editingClient.set(null);
        this.form.reset();
        this.successMessage.set(editing ? 'Cliente actualizado correctamente.' : 'Cliente registrado correctamente.');
      },
      error: (error: unknown) => this.errorMessage.set(this.errorText(error)),
    });
  }

  initials(name: string): string {
    return name.split(/\s+/).slice(0, 2).map((part) => part.charAt(0)).join('').toUpperCase();
  }

  private errorText(error: unknown): string {
    if (error instanceof HttpErrorResponse && typeof error.error?.detail === 'string') return error.error.detail;
    if (error instanceof HttpErrorResponse && Array.isArray(error.error?.detail)) {
      return error.error.detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join(' ') || 'Los datos ingresados no son válidos.';
    }
    return 'No se pudo completar la operación.';
  }
}
