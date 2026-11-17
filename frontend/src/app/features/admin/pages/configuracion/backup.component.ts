import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { finalize } from 'rxjs';
import { environment } from '../../../../../environments/environment';
import { AuthService } from '../../../../core/auth/auth.service';
import { BillingApiService } from '../../../billing/billing-api.service';
import { operationError } from '../../services/operations-api.service';

interface RestoreCheck { valido: boolean; tablas: number; registros_restaurados: number; archivos: number; verificacion: string; }

@Component({ selector: 'app-backup', standalone: true, styleUrl: '../../shared/admin-ui.css', template: `
  <section class="admin-card mt-6 grid max-w-4xl gap-4 p-5" aria-labelledby="backup-title">
    <h2 id="backup-title" class="text-xl font-bold">Respaldo de información</h2>
    <p class="text-sm text-slate-600">Descarga manual completa de todas las sedes: tablas, documentos binarios y archivos de uploads y clinical_private, con manifiesto SHA-256. Conserva el ZIP en un lugar privado.</p>
    @if (error()) { <p role="alert" class="text-rose-700">{{ error() }}</p> }
    @if (message()) { <p role="status" class="text-teal-800">{{ message() }}</p> }
    @if (auth.can('usuarios', 'editar')) {
      <button type="button" class="admin-primary justify-self-start" (click)="download()" [disabled]="busy()">{{ busy() ? 'Procesando respaldo…' : 'Descargar respaldo ZIP' }}</button>
      <label>Seleccionar respaldo para verificar restauración<input class="admin-input" type="file" accept=".zip,application/zip" (change)="select($event)" [disabled]="busy()"></label>
      <button type="button" class="admin-secondary justify-self-start" (click)="verify()" [disabled]="busy() || !file">Verificar restauración aislada</button>
    } @else { <p>Acceso de consulta. Generar y verificar respaldos requiere edición de Usuarios.</p> }
    <p class="text-sm text-slate-500">La comprobación carga los registros en SQLite temporal y valida claves, relaciones, conteos y archivos. No reemplaza la base operativa ni es una restauración PostgreSQL. Límite de verificación: 50 MB comprimidos y 250 MB descomprimidos.</p>
    @if (result(); as data) { <div role="status" class="rounded-xl bg-teal-50 p-4"><b>Restauración lógica verificada</b><p>{{ data.tablas }} tablas · {{ data.registros_restaurados }} registros · {{ data.archivos }} archivos.</p><p>{{ data.verificacion }}</p></div> }
  </section>
` })
export class BackupComponent {
  readonly auth = inject(AuthService);
  private readonly http = inject(HttpClient); private readonly files = inject(BillingApiService);
  private readonly url = `${environment.apiUrl}/admin/operaciones/respaldo`;
  readonly busy = signal(false); readonly error = signal(''); readonly message = signal(''); readonly result = signal<RestoreCheck | null>(null);
  file: File | null = null;
  select(event: Event) { this.file = (event.target as HTMLInputElement).files?.[0] ?? null; this.result.set(null); this.error.set(''); }
  download() {
    if (this.busy() || !this.auth.can('usuarios', 'editar')) return;
    this.busy.set(true); this.error.set(''); this.message.set('');
    this.http.get(this.url, { responseType: 'blob' }).pipe(finalize(() => this.busy.set(false))).subscribe({ next: blob => { this.files.download(blob, `respaldo-clinica-${new Date().toISOString().slice(0, 10)}.zip`); this.message.set('Respaldo descargado. Puedes seleccionar el ZIP para verificarlo.'); }, error: () => this.error.set('No se pudo generar el respaldo. Revisa los permisos y la conexión e intenta nuevamente.') });
  }
  verify() {
    if (!this.file || this.busy() || !this.auth.can('usuarios', 'editar')) return;
    if (this.file.size > 50 * 1024 * 1024) { this.error.set('El respaldo comprimido supera 50 MB.'); return; }
    const data = new FormData(); data.append('archivo', this.file);
    this.busy.set(true); this.error.set(''); this.result.set(null);
    this.http.post<RestoreCheck>(`${this.url}/verificar`, data).pipe(finalize(() => this.busy.set(false))).subscribe({ next: result => this.result.set(result), error: error => this.error.set(operationError(error)) });
  }
}
