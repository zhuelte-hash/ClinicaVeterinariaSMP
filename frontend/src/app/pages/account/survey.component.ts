import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { environment } from '../../../environments/environment';
import { operationError } from '../../features/admin/services/operations-api.service';

@Component({ standalone: true, imports: [FormsModule, RouterLink], template: `
  <main class="mx-auto my-12 max-w-xl space-y-5 rounded-2xl border bg-white p-6 text-slate-800">
    <h1 class="text-2xl font-bold">Tu opinión sobre la atención</h1>
    @if (loading()) { <p role="status">Consultando encuesta…</p> }
    @if (error()) { <p role="alert" class="text-rose-700">{{ error() }}</p><button type="button" class="rounded border p-2" (click)="load()">Consultar de nuevo</button> }
    @if (done()) { <p role="status">Gracias. Tu respuesta ya fue registrada.</p> }
    @if (ready() && !done()) {
      <form class="space-y-4" (ngSubmit)="save()"><label class="block font-bold">{{ question() }}
        <select class="mt-2 block w-full rounded border p-3" name="valoracion" required [(ngModel)]="rating"><option [ngValue]="0" disabled>Selecciona una valoración</option><option [ngValue]="1">1 · Muy mala</option><option [ngValue]="2">2 · Mala</option><option [ngValue]="3">3 · Regular</option><option [ngValue]="4">4 · Buena</option><option [ngValue]="5">5 · Excelente</option></select>
      </label><label class="block">Comentario opcional<textarea class="mt-2 block w-full rounded border p-3" name="comentario" maxlength="2000" [(ngModel)]="comment"></textarea></label>
      <button class="rounded-xl bg-teal-700 px-4 py-3 font-bold text-white" [disabled]="saving() || !rating">{{ saving() ? 'Enviando…' : 'Enviar valoración' }}</button></form>
    }
    <a routerLink="/inicio" class="block font-bold text-teal-700">Volver al inicio</a>
  </main>`,
})
export class SurveyComponent {
  private readonly http = inject(HttpClient); private readonly route = inject(ActivatedRoute);
  private readonly url = `${environment.apiUrl}/encuestas/${encodeURIComponent(this.route.snapshot.paramMap.get('token') || '')}`;
  readonly loading = signal(false); readonly saving = signal(false); readonly done = signal(false); readonly ready = signal(false); readonly error = signal(''); readonly question = signal('');
  rating = 0; comment = '';
  constructor() { this.load(); }
  load(): void { this.loading.set(true); this.error.set(''); this.ready.set(false); this.http.get<{ respondida: boolean; pregunta: string }>(this.url).subscribe({ next: data => { this.done.set(data.respondida); this.question.set(data.pregunta); this.ready.set(true); this.loading.set(false); }, error: e => { this.error.set(operationError(e)); this.loading.set(false); } }); }
  save(): void { if (this.saving() || !this.rating || this.done()) return; this.saving.set(true); this.error.set(''); this.http.post(this.url, { valoracion: this.rating, comentario: this.comment }).subscribe({ next: () => { this.done.set(true); this.comment = ''; this.saving.set(false); history.replaceState(null, '', '/encuesta/respondida'); }, error: e => { this.error.set(operationError(e)); this.saving.set(false); } }); }
}
