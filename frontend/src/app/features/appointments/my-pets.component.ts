import { HttpClient } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { environment } from '../../../environments/environment';
import { Pet } from './appointments.models';
import { PetEditorComponent } from './pet-editor.component';

@Component({
  selector: 'app-my-pets', standalone: true, imports: [PetEditorComponent, RouterLink], changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<section class="mx-auto max-w-4xl space-y-5 px-4 py-10"><h1 class="text-3xl font-extrabold">Mis mascotas</h1><p class="text-slate-600">Mantén sus datos, peso, foto y antecedentes actualizados.</p><a routerLink="/reservar-cita" class="inline-block font-bold text-brand-600">Registrar mascota o reservar una cita →</a>@if (error()) { <p role="alert" class="text-rose-700">{{ error() }}</p><button class="site-button" (click)="load()">Reintentar</button> }@if (loading()) { <p role="status">Cargando mascotas…</p> } @else { @for (pet of pets(); track pet.id) { <app-pet-editor [pet]="pet" (saved)="updated($event)" /> } @empty { <p>No tienes mascotas registradas. Registra la primera desde la reserva de citas.</p> } }</section>`,
})
export class MyPetsComponent {
  private readonly http = inject(HttpClient);
  readonly pets = signal<Pet[]>([]); readonly error = signal(''); readonly loading = signal(true);
  constructor() { this.load(); }
  load(): void { this.loading.set(true); this.error.set(''); this.http.get<Pet[]>(`${environment.apiUrl}/portal/mascotas`).subscribe({ next: pets => { this.pets.set(pets); this.loading.set(false); }, error: () => { this.error.set('No se pudieron cargar tus mascotas.'); this.loading.set(false); } }); }
  updated(pet: Pet): void { this.pets.update(items => items.map(item => item.id === pet.id ? pet : item)); }
}
