import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { AuthService } from '../../core/auth/auth.service';
import { VeterinarianApiService, Referral } from './veterinarian-api.service';
import { VeterinarianClinicalRecord } from './veterinarian.models';
import { operationError } from '../admin/services/operations-api.service';

@Component({ standalone: true, imports: [FormsModule, RouterLink], template: `
  <h1 class="mb-4 text-2xl font-bold">Derivaciones clínicas</h1>
  <button class="rounded-xl border px-4 py-2" (click)="load()" [disabled]="loading()">Actualizar derivaciones</button>
  @if (loading()) { <p role="status">Cargando derivaciones…</p> }
  @if (error()) { <p role="alert" class="my-3 text-rose-700">{{ error() }}</p> }
  @if (message()) { <p role="status" class="my-3 text-teal-700">{{ message() }}</p> }
  @if (auth.can('historias_clinicas', 'crear')) {
    <form class="my-5 space-y-3 rounded-2xl border bg-white p-4" (ngSubmit)="create()"><h2 class="text-xl font-bold">Derivar caso a especialista</h2>
      <label class="block">Atención a derivar<select class="block w-full rounded border p-2" required name="proceso" [(ngModel)]="process"><option [ngValue]="0">Selecciona una atención</option>@for (record of records(); track record.id) { <option [ngValue]="record.id">#{{ record.id }} · {{ record.mascota.nombre }} · {{ record.servicio_nombre }}</option> }</select></label>
      <label class="block">Especialista receptor<select class="block w-full rounded border p-2" required name="receptor" [(ngModel)]="target"><option [ngValue]="0">Selecciona un especialista</option>@for (item of specialists(); track item.id) { <option [ngValue]="item.id">{{ item.nombre }} · {{ item.especialidad || 'General' }}</option> }</select></label>
      <label class="block">Motivo de derivación<textarea class="block w-full rounded border p-2" required minlength="3" maxlength="500" name="motivo" [(ngModel)]="reason"></textarea></label>
      <button class="rounded-xl bg-teal-700 px-4 py-2 text-white" [disabled]="saving() || !process || !target">Enviar derivación</button>
    </form>
  }
  <div class="mt-5 grid gap-4">@for (item of items(); track item.id) {
    <article class="space-y-2 rounded-2xl border bg-white p-4"><h2 class="text-lg font-bold">{{ item.mascota }} · Atención #{{ item.proceso_id }}</h2>
      <p>{{ item.remitente }} → {{ item.receptor }} · {{ item.estado }}</p><p>{{ item.motivo }}</p><p>{{ item.respuesta }}</p>
      @if (item.estado === 'pendiente' && item.receptor_id === auth.currentUser()?.id && auth.can('historias_clinicas', 'crear')) {
        <label class="block">Respuesta a derivación #{{ item.id }}<textarea class="block w-full rounded border p-2" maxlength="5000" [(ngModel)]="answers[item.id]"></textarea></label>
        <button class="rounded border p-2" [disabled]="saving()" (click)="answer(item.id, true)">Aceptar derivación #{{ item.id }}</button>
        <button class="rounded border p-2" [disabled]="saving()" (click)="answer(item.id, false)">Rechazar derivación #{{ item.id }}</button>
      }
      @if (item.estado === 'aceptada') { <a class="block font-bold text-teal-700" [routerLink]="['/veterinario/mascota', item.mascota_id]" [queryParams]="{tab: 'historia'}">Continuar caso de {{ item.mascota }}</a> }
    </article>
  } @empty { @if (!loading()) { <p>No tienes derivaciones registradas.</p> } }</div>`,
})
export class ReferralsComponent {
  readonly auth = inject(AuthService); private readonly api = inject(VeterinarianApiService);
  readonly items = signal<Referral[]>([]); readonly records = signal<VeterinarianClinicalRecord[]>([]); readonly specialists = signal<{ id: number; nombre: string; especialidad: string | null }[]>([]);
  readonly loading = signal(false); readonly saving = signal(false); readonly error = signal(''); readonly message = signal('');
  process = 0; target = 0; reason = ''; answers: Record<number, string> = {};
  constructor() { this.load(); }
  load(): void { this.loading.set(true); this.error.set(''); forkJoin({ items: this.api.referrals(), records: this.api.getClinicalRecords(), specialists: this.api.specialists() }).subscribe({ next: data => { this.items.set(data.items); this.records.set(data.records); this.specialists.set(data.specialists); this.loading.set(false); }, error: e => { this.error.set(operationError(e)); this.loading.set(false); } }); }
  create(): void { if (this.saving()) return; this.saving.set(true); this.api.createReferral(this.process, this.target, this.reason).subscribe({ next: () => { this.saving.set(false); this.reason = ''; this.message.set('Derivación enviada.'); this.load(); }, error: e => { this.error.set(operationError(e)); this.saving.set(false); } }); }
  answer(id: number, accept: boolean): void { if (this.saving()) return; if ((this.answers[id] || '').trim().length < 3) { this.error.set('Escribe una respuesta de al menos tres caracteres.'); return; } this.saving.set(true); this.api.answerReferral(id, accept, this.answers[id]).subscribe({ next: () => { this.saving.set(false); this.message.set(accept ? 'Derivación aceptada. Ya puedes continuar el caso.' : 'Derivación rechazada.'); this.load(); }, error: e => { this.error.set(operationError(e)); this.saving.set(false); } }); }
}
