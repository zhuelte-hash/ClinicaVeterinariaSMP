import { ChangeDetectionStrategy, Component, ElementRef, inject, signal, viewChild } from '@angular/core';
import { ClinicPolicyService } from '../../core/services/clinic-policy.service';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-installations-gallery',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section id="instalaciones" class="bg-brand-50/60 scroll-mt-24" aria-labelledby="installations-title">
      <div class="mx-auto max-w-7xl px-4 py-14 sm:px-6 sm:py-20 lg:px-8">
        <div class="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
          <div class="max-w-2xl">
            <p class="text-sm font-extrabold uppercase tracking-[0.18em] text-brand-600">Nuestra clínica, de cerca</p>
            <h2 id="installations-title" class="mt-3 text-3xl font-black tracking-tight text-pet-900 sm:text-4xl">Conoce nuestras instalaciones</h2>
            <p class="mt-4 leading-7 text-slate-600">Un vistazo a nuestros espacios, nuestro equipo y los pequeños compañeros que nos visitan cada día.</p>
          </div>
          @if (photos().length) {
            <p class="shrink-0 text-sm font-semibold text-brand-700">{{ photos().length }} fotografías · Toca para ampliar</p>
          }
        </div>

        @if (loading()) {
          <p role="status" class="mt-8 text-slate-600">Cargando fotografías de la clínica…</p>
        } @else if (error()) {
          <div class="mt-8 rounded-2xl border border-rose-200 bg-white p-6">
            <p role="alert">No pudimos cargar las instalaciones.</p>
            <button type="button" class="site-button mt-4" (click)="load()">Reintentar galería</button>
          </div>
        } @else {
          <div class="mt-9 columns-1 gap-6 sm:columns-2 lg:columns-3">
            @for (photo of photos(); track photo.url; let index = $index) {
              <figure class="mb-6 break-inside-avoid overflow-hidden rounded-3xl border border-slate-200/80 bg-white shadow-sm">
                <button type="button" class="group relative block w-full cursor-zoom-in overflow-hidden text-left focus-visible:outline focus-visible:outline-4 focus-visible:-outline-offset-4 focus-visible:outline-brand-600"
                  [attr.aria-label]="'Ampliar fotografía: ' + photo.titulo" aria-haspopup="dialog" (click)="openPhoto(index)">
                  <img [src]="imageUrl(photo.url)" [alt]="photo.titulo" loading="lazy" decoding="async"
                    class="h-auto w-full bg-slate-100 transition duration-500 motion-safe:group-hover:scale-[1.025]">
                  <span class="absolute bottom-3 right-3 flex items-center gap-2 rounded-full bg-pet-900/85 px-3 py-2 text-xs font-bold text-white shadow-sm" aria-hidden="true">
                    <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="10" cy="10" r="6"/><path d="m15 15 6 6M10 7v6M7 10h6"/></svg>
                    Ampliar
                  </span>
                </button>
                <figcaption class="px-5 py-4 text-sm font-bold leading-6 text-pet-900">{{ photo.titulo }}</figcaption>
              </figure>
            } @empty {
              <p class="text-slate-600">Próximamente compartiremos fotografías de nuestras instalaciones.</p>
            }
          </div>
        }
      </div>
    </section>

    <dialog #viewer aria-labelledby="gallery-photo-title" class="gallery-viewer"
      (click)="closeOnBackdrop($event)" (keydown.arrowleft)="navigate(-1, $event)" (keydown.arrowright)="navigate(1, $event)">
      @if (photos()[activeIndex()]; as photo) {
        <div class="overflow-hidden rounded-2xl bg-white shadow-2xl">
          <div class="flex items-center justify-between gap-4 border-b border-slate-100 px-4 py-3 sm:px-6">
            <p class="text-sm font-semibold text-slate-500">Fotografía {{ activeIndex() + 1 }} de {{ photos().length }}</p>
            <button type="button" autofocus (click)="closePhoto()" class="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-slate-100 text-2xl text-pet-900 hover:bg-slate-200" aria-label="Cerrar fotografía">×</button>
          </div>
          <div class="bg-slate-950">
            <img [src]="imageUrl(photo.url)" [alt]="photo.titulo" class="max-h-[65dvh] w-full object-contain">
          </div>
          <div class="flex items-center justify-between gap-3 px-4 py-4 sm:px-6">
            <button type="button" (click)="navigate(-1)" class="grid h-11 w-11 shrink-0 place-items-center rounded-full border border-slate-200 text-xl text-pet-900 hover:bg-brand-50" aria-label="Fotografía anterior">←</button>
            <h3 id="gallery-photo-title" class="text-center text-sm font-bold text-pet-900 sm:text-base" aria-live="polite">{{ photo.titulo }}</h3>
            <button type="button" (click)="navigate(1)" class="grid h-11 w-11 shrink-0 place-items-center rounded-full border border-slate-200 text-xl text-pet-900 hover:bg-brand-50" aria-label="Fotografía siguiente">→</button>
          </div>
        </div>
      }
    </dialog>
  `,
  styles: `
    .gallery-viewer { border: 0; padding: 0; background: transparent; width: min(960px, calc(100% - 24px)); max-height: calc(100dvh - 24px); margin: auto; color: inherit; }
    .gallery-viewer::backdrop { background: rgb(8 24 35 / 85%); backdrop-filter: blur(5px); }
  `,
})
export class InstallationsGalleryComponent {
  private readonly policy = inject(ClinicPolicyService);
  private readonly viewer = viewChild.required<ElementRef<HTMLDialogElement>>('viewer');
  readonly photos = signal<{ url: string; titulo: string }[]>([]);
  readonly loading = signal(false);
  readonly error = signal(false);
  readonly activeIndex = signal(0);

  constructor() { this.load(); }

  imageUrl(url: string) { return environment.apiUrl + url; }

  openPhoto(index: number): void {
    this.activeIndex.set(index);
    this.viewer().nativeElement.showModal();
  }

  closePhoto(): void { this.viewer().nativeElement.close(); }

  closeOnBackdrop(event: MouseEvent): void {
    if (event.target === this.viewer().nativeElement) this.closePhoto();
  }

  navigate(direction: number, event?: Event): void {
    event?.preventDefault();
    const count = this.photos().length;
    if (count) this.activeIndex.update(index => (index + direction + count) % count);
  }

  load(): void {
    if (this.loading()) return;
    this.loading.set(true);
    this.error.set(false);
    this.policy.get().subscribe({
      next: data => { this.photos.set(data.galeria); this.loading.set(false); },
      error: () => { this.error.set(true); this.loading.set(false); },
    });
  }
}
