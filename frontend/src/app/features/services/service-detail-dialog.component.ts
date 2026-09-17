import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { DialogRef, DIALOG_DATA } from '@angular/cdk/dialog';
import { RouterLink } from '@angular/router';
import { VeterinaryService } from './service.model';

@Component({
  selector: 'app-service-detail-dialog',
  standalone: true,
  imports: [RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="relative max-h-[90vh] w-[calc(100vw-2rem)] max-w-2xl overflow-y-auto rounded-3xl bg-white shadow-2xl" aria-labelledby="service-dialog-title">
      <button
        type="button"
        class="absolute right-4 top-4 z-10 flex h-10 w-10 items-center justify-center rounded-full bg-white text-[#1A1E27] shadow-md transition hover:bg-[#D5D2D3] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#1A98A2]"
        aria-label="Cerrar detalle del servicio"
        (click)="dialogRef.close()"
      >
        <svg class="h-5 w-5" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"><path d="m5 5 10 10M15 5 5 15"/></svg>
      </button>
      <img [src]="service.imageUrl" [alt]="service.imageAlt" class="h-56 w-full object-cover sm:h-72" />
      <div class="p-6 sm:p-8">
        <p class="text-xs font-bold uppercase tracking-[0.14em] text-[#1A98A2]">{{ service.category }}</p>
        <h2 id="service-dialog-title" class="mt-2 text-3xl font-extrabold text-[#1A1E27]">{{ service.name }}</h2>
        <p class="mt-4 leading-7 text-[#1A1E27]/75">{{ service.description }}</p>
        <div class="mt-7 flex flex-col gap-3 sm:flex-row">
          <a href="tel:965939522" class="inline-flex items-center justify-center rounded-full bg-[#1A98A2] px-6 py-3 font-bold text-white transition hover:bg-[#276508] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1A98A2]">Llamar ahora</a>
          <a routerLink="/contacto" (click)="dialogRef.close()" class="inline-flex items-center justify-center rounded-full border-2 border-[#1A1E27] px-6 py-3 font-bold text-[#1A1E27] transition hover:bg-[#1A1E27] hover:text-white">Reservar cita</a>
        </div>
      </div>
    </section>
  `,
})
export class ServiceDetailDialogComponent {
  readonly dialogRef = inject<DialogRef<void>>(DialogRef);
  readonly service = inject<VeterinaryService>(DIALOG_DATA);
}
