import { HttpClient } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { environment } from '../../../environments/environment';
import { Pet } from './appointments.models';
import { PetEditorComponent } from './pet-editor.component';

@Component({
  selector: 'app-my-pets', standalone: true, imports: [PetEditorComponent, RouterLink], changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<section class="mx-auto max-w-4xl space-y-5 px-4 py-10"><h1 class="text-3xl font-extrabold">Mis mascotas</h1><p class="text-slate-600">Mantén sus datos, peso, foto y antecedentes actualizados.</p><a routerLink="/reservar-cita" class="inline-block font-bold text-brand-600">Registrar mascota o reservar una cita →</a>@if (error()) { <p role="alert" class="text-rose-700">{{ error() }}</p><button class="site-button" (click)="load()">Reintentar</button> }@if (downloadError()) { <p role="alert" class="text-rose-700">{{ downloadError() }}</p> }@if (loading()) { <p role="status">Cargando mascotas…</p> } @else { @for (pet of pets(); track pet.id) { <app-pet-editor [pet]="pet" (saved)="updated($event)" /><div class="rounded-xl border border-teal-200 p-4"><h2 class="font-bold">Carnet de vacunación de {{ pet.nombre }}</h2><p class="my-2 text-sm text-slate-600">Descarga las vacunas registradas, sus lotes, próximas fechas y veterinario responsable.</p><button type="button" class="site-button" [disabled]="downloading() !== null" (click)="download(pet)">{{ downloading() === pet.id ? 'Generando PDF…' : 'Descargar carnet de ' + pet.nombre }}</button></div> } @empty { <p>No tienes mascotas registradas. Registra la primera desde la reserva de citas.</p> } }</section>`,
})
export class MyPetsComponent {
  private readonly http = inject(HttpClient);
  readonly pets = signal<Pet[]>([]); readonly error = signal(''); readonly loading = signal(true);
  readonly downloading = signal<number | null>(null); readonly downloadError = signal('');
  constructor() { this.load(); }
  load(): void { this.loading.set(true); this.error.set(''); this.http.get<Pet[]>(`${environment.apiUrl}/portal/mascotas`).subscribe({ next: pets => { this.pets.set(pets); this.loading.set(false); }, error: () => { this.error.set('No se pudieron cargar tus mascotas.'); this.loading.set(false); } }); }
  updated(pet: Pet): void { this.pets.update(items => items.map(item => item.id === pet.id ? pet : item)); }
  download(pet: Pet): void {
    if (this.downloading() !== null) return;
    this.downloading.set(pet.id); this.downloadError.set('');
    this.http.get(`${environment.apiUrl}/portal/mascotas/${pet.id}/carnet`, { responseType: 'blob' }).subscribe({ next: pdf => { const url = URL.createObjectURL(pdf); const link = document.createElement('a'); link.href = url; link.download = `carnet-${pet.id}.pdf`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); this.downloading.set(null); }, error: () => { this.downloadError.set('No se pudo descargar el carnet. Intenta nuevamente.'); this.downloading.set(null); } });
  }
}
