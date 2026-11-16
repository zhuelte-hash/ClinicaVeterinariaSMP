import { Component, effect, inject, input, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';
import { AuthService } from '../../core/auth/auth.service';
import { operationError } from '../admin/services/operations-api.service';
import { VeterinarianApiService } from './veterinarian-api.service';

@Component({
  selector: 'app-private-clinical-notes', standalone: true, imports: [ReactiveFormsModule],
  template: `<section class="rounded-2xl border border-amber-200 bg-amber-50 p-5" [attr.aria-labelledby]="'private-notes-title-' + processId()">
    <h3 [id]="'private-notes-title-' + processId()" class="text-lg font-bold text-amber-950">Notas internas privadas</h3>
    <p class="mt-2 text-sm text-amber-900">Solo el profesional autorizado puede consultar estas notas. Se guardan por separado del historial y los documentos visibles al cliente.</p>
    @if (loading()) { <p role="status" class="mt-3 text-sm">Cargando notas…</p> }
    @if (error()) { <p role="alert" class="mt-3 text-sm text-rose-700">{{ error() }}</p> }
    @if (message()) { <p role="status" class="mt-3 text-sm text-emerald-800">{{ message() }}</p> }
    @if (loaded()) {
      <form class="mt-4 grid gap-3" [formGroup]="form" (ngSubmit)="save()">
        <label [for]="'private-notes-' + processId()" class="grid gap-2 text-sm font-bold">Observaciones internas
          <textarea [id]="'private-notes-' + processId()" formControlName="notas" rows="4" maxlength="10000" class="rounded-xl border border-amber-300 bg-white p-3 font-normal" [readOnly]="saving() || !auth.can('historias_clinicas', 'editar')"></textarea>
        </label>
        @if (auth.can('historias_clinicas', 'editar')) { <button class="site-button justify-self-start" [disabled]="saving() || notes.invalid || !notes.dirty">{{ saving() ? 'Guardando…' : 'Guardar notas privadas' }}</button> }
        @else { <p class="text-sm text-amber-900">Acceso de solo consulta.</p> }
      </form>
    } @else if (!loading()) { <button type="button" class="site-button mt-3" (click)="load()">Reintentar carga</button> }
  </section>`,
})
export class PrivateClinicalNotesComponent {
  readonly processId = input.required<number>();
  readonly auth = inject(AuthService);
  private readonly api = inject(VeterinarianApiService);
  readonly form = inject(FormBuilder).nonNullable.group({ notas: ['', Validators.maxLength(10000)] });
  readonly notes = this.form.controls.notas;
  readonly loading = signal(false); readonly loaded = signal(false); readonly saving = signal(false);
  readonly error = signal(''); readonly message = signal('');
  private version = 0;

  constructor() { effect(() => { this.processId(); this.load(); }); }

  load(): void {
    const id = this.processId(); const version = ++this.version;
    this.loading.set(true); this.loaded.set(false); this.error.set(''); this.message.set(''); this.notes.reset();
    this.api.getPrivateNotes(id).subscribe({
      next: result => { if (version !== this.version) return; this.notes.reset(result.notas); this.loaded.set(true); this.loading.set(false); },
      error: error => { if (version !== this.version) return; this.loading.set(false); this.error.set(operationError(error)); },
    });
  }

  save(): void {
    if (this.saving() || !this.loaded() || this.notes.invalid || !this.auth.can('historias_clinicas', 'editar')) return;
    const id = this.processId(); const version = this.version;
    this.saving.set(true); this.error.set(''); this.message.set('');
    this.api.savePrivateNotes(id, this.notes.value).pipe(finalize(() => this.saving.set(false))).subscribe({
      next: result => { if (version !== this.version) return; this.notes.reset(result.notas); this.message.set('Notas privadas guardadas.'); },
      error: error => { if (version === this.version) this.error.set(operationError(error)); },
    });
  }
}
