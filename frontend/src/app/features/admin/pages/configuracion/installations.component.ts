import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { environment } from '../../../../../environments/environment';
import { AuthService } from '../../../../core/auth/auth.service';
import { ClinicPolicy } from '../../../../core/services/clinic-policy.service';
import { operationError } from '../../services/operations-api.service';

@Component({ selector: 'app-installations-settings', standalone: true, imports: [FormsModule], styleUrl: '../../shared/admin-ui.css', template: `
  <section class="admin-card mt-6 grid max-w-4xl gap-4 p-5" aria-labelledby="gallery-title">
    <h2 id="gallery-title" class="text-xl font-bold">Galería de instalaciones y próximas vacunas</h2>
    <p class="text-sm text-slate-600">Publica fotografías reales de la clínica con un título identificable. Los cambios de orden o eliminación se aplican al guardar la galería.</p>
    @if (error()) { <p role="alert" class="text-rose-700">{{ error() }}</p><button type="button" class="admin-secondary" (click)="load()" [disabled]="busy()">Recargar galería</button> }
    @if (message()) { <p role="status" class="text-teal-800">{{ message() }}</p> }
    @if (busy()) { <p role="status">Procesando galería y vacunas…</p> }
    <fieldset class="grid gap-4" [disabled]="busy() || !loaded() || !auth.can('usuarios', 'editar')">
      <label>Título de la nueva fotografía<input class="admin-input" maxlength="150" [(ngModel)]="title" placeholder="Por ejemplo: Consultorio principal"></label>
      <label>Fotografía real JPG o PNG (máximo 5 MB)<input type="file" accept="image/jpeg,image/png" (change)="selectFile($event)"></label>
      <button type="button" class="admin-secondary" (click)="upload()" [disabled]="!file || title.trim().length < 3 || photos().length >= 50">Subir fotografía</button>
    </fieldset>
    <div class="grid gap-4 sm:grid-cols-2">
      @for (photo of photos(); track photo.url; let i = $index) {
        <figure class="rounded-xl border p-3"><img [src]="imageUrl(photo.url)" [alt]="photo.titulo" class="h-40 w-full rounded-lg object-cover">
          <label>Título de fotografía {{ i + 1 }}<input class="admin-input" [(ngModel)]="photo.titulo" maxlength="150" [disabled]="busy() || !auth.can('usuarios', 'editar')"></label>
          @if (auth.can('usuarios', 'editar')) { <div class="mt-2 flex flex-wrap gap-2"><button type="button" class="admin-secondary" (click)="move(i, -1)" [disabled]="busy() || i === 0" [attr.aria-label]="'Subir posición de ' + photo.titulo">↑</button><button type="button" class="admin-secondary" (click)="move(i, 1)" [disabled]="busy() || i === photos().length - 1" [attr.aria-label]="'Bajar posición de ' + photo.titulo">↓</button><button type="button" class="admin-secondary" (click)="remove(i)" [disabled]="busy()" [attr.aria-label]="'Quitar ' + photo.titulo">Quitar</button></div> }
        </figure>
      } @empty { <p>Sin fotografías de instalaciones publicadas.</p> }
    </div>
    @if (auth.can('usuarios', 'editar')) { <button type="button" class="admin-primary" (click)="saveGallery()" [disabled]="busy() || !loaded() || !validPhotos()">Guardar galería pública</button> }
    <form #vaccineForm="ngForm" class="grid gap-3 border-t pt-4" (ngSubmit)="vaccineForm.valid && saveVaccines()">
      <h3 class="font-bold">Recordatorios de próxima vacuna (HU-056 / HU-103)</h3>
      <p class="text-sm text-slate-600">Incluye vacunas registradas con cita y en atención presencial. El worker revisa desde hoy hasta el plazo indicado, sin repetir la misma aplicación y fecha. Cero incluye solo las vacunas de hoy. La entrega WhatsApp requiere proveedor y plantilla vacuna aprobada.</p>
      <label>Días de anticipación de vacuna<input name="vaccineDays" class="admin-input" required type="number" min="0" max="30" step="1" [(ngModel)]="days" [disabled]="busy() || !loaded() || !auth.can('usuarios', 'editar')"></label>
      @if (auth.can('usuarios', 'editar')) { <button class="admin-primary" [disabled]="busy() || !loaded() || vaccineForm.invalid">Guardar plazo de vacunas</button> }
    </form>
  </section>
` })
export class InstallationsComponent {
  readonly auth = inject(AuthService); private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/admin/operaciones`;
  readonly photos = signal<{ url: string; titulo: string }[]>([]);
  readonly busy = signal(false); readonly loaded = signal(false); readonly error = signal(''); readonly message = signal('');
  title = ''; file: File | null = null; days = 3;
  constructor() { this.load(); }
  imageUrl(url: string) { return environment.apiUrl + url; }
  load() {
    if (this.busy()) return;
    this.busy.set(true); this.error.set('');
    this.http.get<ClinicPolicy>(`${this.base}/configuracion`).pipe(finalize(() => this.busy.set(false))).subscribe({ next: data => { this.photos.set(data.galeria); this.days = data.dias_recordatorio_vacuna; this.loaded.set(true); }, error: error => this.error.set(operationError(error)) });
  }
  selectFile(event: Event) { this.file = (event.target as HTMLInputElement).files?.[0] || null; }
  upload() {
    if (!this.file || this.title.trim().length < 3 || this.busy() || !this.loaded() || !this.auth.can('usuarios', 'editar') || this.photos().length >= 50) return;
    if (this.file.size > 5 * 1024 * 1024 || !['image/jpeg', 'image/png'].includes(this.file.type)) { this.error.set('Selecciona una fotografía JPG o PNG de hasta 5 MB.'); return; }
    const payload = new FormData(); payload.append('archivo', this.file);
    const title = this.title.trim(); this.busy.set(true); this.error.set(''); this.message.set('');
    this.http.post<{ url: string }>(`${this.base}/instalaciones`, payload).pipe(finalize(() => this.busy.set(false))).subscribe({ next: data => { this.photos.update(rows => [...rows, { url: data.url, titulo: title }]); this.title = ''; this.file = null; this.message.set('Fotografía subida. Guarda la galería para publicarla.'); }, error: error => this.error.set(operationError(error)) });
  }
  move(index: number, offset: number) {
    const target = index + offset;
    if (this.busy() || !this.auth.can('usuarios', 'editar') || target < 0 || target >= this.photos().length) return;
    this.photos.update(rows => { const next = [...rows]; [next[index], next[target]] = [next[target], next[index]]; return next; });
  }
  remove(index: number) { if (!this.busy() && this.auth.can('usuarios', 'editar')) this.photos.update(rows => rows.filter((_, i) => i !== index)); }
  validPhotos() { return this.photos().every(photo => photo.titulo.trim().length >= 3 && photo.titulo.length <= 150); }
  saveGallery() {
    if (!this.validPhotos() || this.busy() || !this.loaded() || !this.auth.can('usuarios', 'editar')) return;
    this.save('/galeria', { galeria: this.photos() }, 'Galería pública guardada.');
  }
  saveVaccines() {
    if (!Number.isInteger(this.days) || this.days < 0 || this.days > 30 || this.busy() || !this.loaded() || !this.auth.can('usuarios', 'editar')) return;
    this.save('/politicas-vacunas', { dias_recordatorio_vacuna: this.days }, 'Plazo de vacunas guardado. Mantén el worker activo.');
  }
  private save(path: string, payload: unknown, success: string) {
    this.busy.set(true); this.error.set(''); this.message.set('');
    this.http.put<ClinicPolicy>(this.base + path, payload).pipe(finalize(() => this.busy.set(false))).subscribe({ next: () => this.message.set(success), error: error => this.error.set(operationError(error)) });
  }
}
