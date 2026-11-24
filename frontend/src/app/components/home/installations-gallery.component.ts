import { Component, inject, signal } from '@angular/core';
import { ClinicPolicyService } from '../../core/services/clinic-policy.service';
import { environment } from '../../../environments/environment';

@Component({ selector: 'app-installations-gallery', standalone: true, template: `
  <section class="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8" aria-labelledby="installations-title">
    <h2 id="installations-title" class="text-3xl font-black text-pet-900">Conoce nuestras instalaciones</h2>
    @if (loading()) { <p role="status" class="mt-4">Cargando fotografías de la clínica…</p> }
    @else if (error()) { <p role="alert" class="mt-4">No pudimos cargar las instalaciones.</p><button type="button" class="site-button mt-4" (click)="load()">Reintentar galería</button> }
    @else {
      <div class="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        @for (photo of photos(); track photo.url) {
          <figure class="overflow-hidden rounded-2xl border bg-white shadow-sm"><img [src]="imageUrl(photo.url)" [alt]="photo.titulo" loading="lazy" class="aspect-square w-full bg-slate-50 object-contain"><figcaption class="p-4 font-bold text-pet-900">{{ photo.titulo }}</figcaption></figure>
        } @empty { <p class="text-slate-600">Próximamente compartiremos fotografías de nuestras instalaciones.</p> }
      </div>
    }
  </section>
` })
export class InstallationsGalleryComponent {
  private readonly policy = inject(ClinicPolicyService);
  readonly photos = signal<{ url: string; titulo: string }[]>([]); readonly loading = signal(false); readonly error = signal(false);
  constructor() { this.load(); }
  imageUrl(url: string) { return environment.apiUrl + url; }
  load() { if (this.loading()) return; this.loading.set(true); this.error.set(false); this.policy.get().subscribe({ next: data => { this.photos.set(data.galeria); this.loading.set(false); }, error: () => { this.error.set(true); this.loading.set(false); } }); }
}
