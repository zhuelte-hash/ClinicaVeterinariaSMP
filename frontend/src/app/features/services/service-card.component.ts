import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { VeterinaryService } from './service.model';

@Component({
  selector: 'app-service-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'block h-full' },
  template: `
    <article class="site-card group flex h-full flex-col overflow-hidden hover:-translate-y-0.5">
      <div class="relative h-52 overflow-hidden">
        <img
          [src]="service().imageUrl"
          [alt]="service().imageAlt"
          loading="lazy"
          class="h-full w-full object-cover transition duration-500 group-hover:scale-105"
        />
        <div class="absolute left-4 top-4 flex h-11 w-11 items-center justify-center rounded-xl border border-[#1A98A2]/15 bg-white text-[#147d87]" aria-hidden="true">
          @switch (service().icon) {
            @case ('science') { <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 3h6M10 3v6l-5.4 9.1A2 2 0 0 0 6.3 21h11.4a2 2 0 0 0 1.7-2.9L14 9V3M8 15h8"/></svg> }
            @case ('bed') { <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 19v-8m18 8v-6a2 2 0 0 0-2-2H9v8M3 15h18M5 11V7h4a2 2 0 0 1 2 2v2"/></svg> }
            @case ('home_health') { <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m3 11 9-8 9 8v10h-6v-6H9v6H3V11Z"/><path d="M12 7v4m-2-2h4"/></svg> }
            @case ('emergency') { <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3 2.5 20h19L12 3Z"/><path d="M12 9v5m0 3h.01"/></svg> }
            @default { <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M8.5 10.5c-1.7 0-3.5 1.8-3.5 4.3C5 18.1 8.1 20 12 20s7-1.9 7-5.2c0-2.5-1.8-4.3-3.5-4.3-1.4 0-2.2.8-3.5.8s-2.1-.8-3.5-.8Z"/><circle cx="5" cy="7" r="2"/><circle cx="10" cy="5" r="2"/><circle cx="19" cy="7" r="2"/><circle cx="14" cy="5" r="2"/></svg> }
          }
        </div>
      </div>
      <div class="flex flex-1 flex-col p-6">
        <p class="mb-2 text-xs font-bold uppercase tracking-[0.12em] text-[#1A98A2]">{{ service().category }}</p>
        <h3 class="text-xl font-bold leading-snug text-[#1A1E27]">{{ service().name }}</h3>
        <p class="mt-3 flex-1 text-sm leading-6 text-[#1A1E27]/70">{{ service().summary }}</p>
        <button
          type="button"
          class="mt-6 inline-flex min-h-11 items-center gap-2 self-start font-bold text-[#0B1B6D] transition hover:text-[#147d87] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#1A98A2]"
          [attr.aria-label]="'Ver más sobre ' + service().name"
          (click)="showDetails.emit(service())"
        >
          Ver más
          <svg class="h-4 w-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 10h12m-5-5 5 5-5 5"/></svg>
        </button>
      </div>
    </article>
  `,
})
export class ServiceCardComponent {
  readonly service = input.required<VeterinaryService>();
  readonly showDetails = output<VeterinaryService>();
}
