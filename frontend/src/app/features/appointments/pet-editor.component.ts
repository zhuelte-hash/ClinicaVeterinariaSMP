import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, effect, inject, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { environment } from '../../../environments/environment';
import { NoticeService } from '../../core/services/notice.service';
import { Pet } from './appointments.models';

@Component({
  selector: 'app-pet-editor', standalone: true, imports: [FormsModule], changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="rounded-2xl border border-slate-200 bg-white p-5">
      <div class="flex flex-wrap items-center gap-4">
        <img [src]="photoUrl()" [alt]="'Foto de ' + pet().nombre" class="h-24 w-24 rounded-2xl bg-slate-50 object-cover">
        <div><h2 class="text-lg font-bold">Ficha maestra de {{ pet().nombre }}</h2><p class="mt-1 text-sm text-slate-500">Identificación, peso actual y antecedentes consolidados.</p><button type="button" (click)="open.update(value => !value)" [attr.aria-expanded]="open()" class="mt-2 font-bold text-teal-700">{{ open() ? 'Ocultar edición' : 'Editar datos y foto' }}</button></div>
      </div>
      @if (error()) { <p class="mt-3 text-sm text-rose-700" role="alert">{{ error() }}</p> }
      @if (open()) {
        <form #petForm="ngForm" (ngSubmit)="save()" class="mt-5 grid gap-4 sm:grid-cols-2">
          @for (field of textFields; track field.key) { <label class="grid gap-1 text-sm font-semibold">{{ field.label }}<input class="site-input" [name]="field.key" [(ngModel)]="form[field.key]" [required]="field.key === 'nombre' || field.key === 'especie'" [maxlength]="field.max"></label> }
          <label class="grid gap-1 text-sm font-semibold">Fecha de nacimiento<input class="site-input" type="date" name="nacimiento" [(ngModel)]="form.fecha_nacimiento" [max]="today"></label>
          <label class="grid gap-1 text-sm font-semibold">Peso actual (kg)<input class="site-input" type="number" min="0" max="99999.99" step="0.01" name="peso" [(ngModel)]="form.peso_actual"></label>
          @for (field of notesFields; track field.key) { <label class="grid gap-1 text-sm font-semibold sm:col-span-2">{{ field.label }}<textarea class="site-input" [name]="field.key" [(ngModel)]="form[field.key]" rows="2" [maxlength]="field.max"></textarea></label> }
          <button class="site-button sm:col-span-2" [disabled]="petForm.invalid || saving()">{{ saving() ? 'Guardando…' : 'Guardar ficha' }}</button>
        </form>
        <label class="mt-5 grid gap-2 text-sm font-semibold">Actualizar foto (JPG, PNG o WEBP, hasta 5 MB)<input type="file" accept="image/jpeg,image/png,image/webp" [disabled]="saving()" (change)="upload($event)"></label>
      }
    </section>`,
})
export class PetEditorComponent {
  private readonly http = inject(HttpClient);
  private readonly notice = inject(NoticeService);
  readonly pet = input.required<Pet>();
  readonly saved = output<Pet>();
  readonly open = signal(false);
  readonly saving = signal(false);
  readonly error = signal('');
  readonly today = new Date().toISOString().slice(0, 10);
  readonly textFields = [{ key: 'nombre', label: 'Nombre', max: 100 }, { key: 'especie', label: 'Especie', max: 80 }, { key: 'raza', label: 'Raza', max: 100 }, { key: 'sexo', label: 'Sexo', max: 20 }] as const;
  readonly notesFields = [{ key: 'alergias', label: 'Alergias conocidas (alerta clínica)', max: 5000 }, { key: 'condiciones_especiales', label: 'Condiciones especiales (alerta clínica)', max: 5000 }, { key: 'caracteristicas', label: 'Características y antecedentes', max: 2000 }] as const;
  form = { nombre: '', especie: '', raza: '', sexo: '', fecha_nacimiento: '', peso_actual: '' as string | number, caracteristicas: '', alergias: '', condiciones_especiales: '' };
  constructor() { effect(() => { const pet = this.pet(); Object.assign(this.form, Object.fromEntries(Object.keys(this.form).map(key => [key, pet[key as keyof Pet] ?? '']))); }); }
  photoUrl(): string { const path = this.pet().foto_url; return path ? `${environment.apiUrl}${path}` : '/logo.png'; }
  save(): void {
    if (this.saving()) return;
    this.saving.set(true); this.error.set('');
    this.http.patch<Pet>(`${environment.apiUrl}/portal/mascotas/${this.pet().id}`, { ...this.form, fecha_nacimiento: this.form.fecha_nacimiento || null, peso_actual: this.form.peso_actual === '' ? null : this.form.peso_actual }).pipe(finalize(() => this.saving.set(false))).subscribe({
      next: pet => { this.saved.emit(pet); this.notice.show('Ficha del paciente actualizada'); }, error: error => this.showError(error),
    });
  }
  upload(event: Event): void {
    const input = event.target as HTMLInputElement; const file = input.files?.[0]; if (!file || this.saving()) return;
    const body = new FormData(); body.append('archivo', file); this.saving.set(true); this.error.set('');
    this.http.post<Pet>(`${environment.apiUrl}/portal/mascotas/${this.pet().id}/foto`, body).pipe(finalize(() => { this.saving.set(false); input.value = ''; })).subscribe({
      next: pet => { this.saved.emit(pet); this.notice.show('Foto actualizada'); }, error: error => this.showError(error),
    });
  }
  private showError(error: HttpErrorResponse): void { this.error.set(typeof error.error?.detail === 'string' ? error.error.detail : 'Revisa los datos ingresados e intenta nuevamente.'); }
}
