import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { AdminApiService, AdminSettings } from '../../services/admin-api.service';
import { PageHeaderComponent } from '../../shared/page-header.component';

@Component({ selector: 'app-admin-configuracion', standalone: true, imports: [FormsModule, PageHeaderComponent], templateUrl: './configuracion.component.html', styleUrl: '../../shared/admin-ui.css' })
export class ConfiguracionComponent {
  private readonly api = inject(AdminApiService); readonly saved = signal(false); readonly loading = signal(true); readonly saving = signal(false); readonly error = signal('');
  form: AdminSettings = { nombre: '', correo: '', telefono: '', direccion: '', umbral_stock_bajo: 8, recordatorios_citas: true, alertas_stock: true };
  readonly loaded = signal(false);
  constructor() { this.load(); }
  load(): void { this.loading.set(true); this.api.getSettings().pipe(finalize(() => this.loading.set(false))).subscribe({ next: (settings) => { this.form = settings; this.loaded.set(true); this.error.set(''); }, error: (error: unknown) => this.error.set(this.errorText(error)) }); }
  save(): void { if (this.saving() || this.loading() || !this.loaded()) return; this.saving.set(true); this.saved.set(false); this.error.set(''); this.api.updateSettings(this.form).pipe(finalize(() => this.saving.set(false))).subscribe({ next: (settings) => { this.form = settings; this.saved.set(true); window.setTimeout(() => this.saved.set(false), 2500); }, error: (error: unknown) => this.error.set(this.errorText(error)) }); }
  private errorText(error: unknown): string { if (error instanceof HttpErrorResponse && typeof error.error?.detail === 'string') return error.error.detail; if (error instanceof HttpErrorResponse && Array.isArray(error.error?.detail)) return error.error.detail.map((item: { msg: string }) => item.msg).join(' · '); return 'No se pudo cargar o guardar la configuración.'; }
}
