import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';

export function clinicalSearch(value: string): string {
  return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('es').trim();
}

export function clinicalDate(value: string | null | undefined, time = false): string {
  if (!value) return 'Sin registrar';
  const date = new Date(value.length === 10 ? `${value}T12:00:00-05:00` : value);
  if (Number.isNaN(date.getTime())) return 'Sin registrar';
  return new Intl.DateTimeFormat('es-PE', { dateStyle: 'medium', ...(time ? { timeStyle: 'short' as const } : {}), timeZone: 'America/Lima' }).format(date);
}

export class VeterinarianTableState<T> {
  readonly page = signal(1);
  readonly pageSize = signal(10);
  readonly total = computed(() => this.source().length);
  readonly pages = computed(() => this.pageSize() === 0 ? 1 : Math.max(1, Math.ceil(this.total() / this.pageSize())));
  readonly currentPage = computed(() => Math.min(Math.max(1, this.page()), this.pages()));
  readonly rows = computed(() => {
    if (this.pageSize() === 0) return this.source();
    const start = (this.currentPage() - 1) * this.pageSize();
    return this.source().slice(start, start + this.pageSize());
  });

  constructor(private readonly source: () => T[]) {}

  reset(): void { this.page.set(1); }
  resize(size: number): void { this.pageSize.set(size); this.reset(); }
}

@Component({
  selector: 'vet-pagination', standalone: true, changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nav class="vet-pagination" [attr.aria-label]="label()">
      <p aria-live="polite">Mostrando <strong>{{ start() }}–{{ end() }}</strong> de <strong>{{ total() }}</strong> registros</p>
      <div class="vet-pagination-controls">
        <label>Filas <select aria-label="Filas por página" [value]="pageSize()" (change)="pageSizeChange.emit(+$any($event.target).value)"><option value="10">10</option><option value="25">25</option><option value="50">50</option><option value="100">100</option><option value="0">Todas</option></select></label>
        <button type="button" class="vet-btn vet-btn-secondary vet-btn-small" [disabled]="page() <= 1" (click)="pageChange.emit(page() - 1)" aria-label="Página anterior">‹</button>
        <span class="vet-page-number">{{ page() }} / {{ pages() }}</span>
        <button type="button" class="vet-btn vet-btn-secondary vet-btn-small" [disabled]="page() >= pages()" (click)="pageChange.emit(page() + 1)" aria-label="Página siguiente">›</button>
      </div>
    </nav>
  `,
})
export class VeterinarianPaginationComponent {
  readonly total = input.required<number>();
  readonly page = input.required<number>();
  readonly pageSize = input.required<number>();
  readonly label = input('Paginación de registros');
  readonly pageChange = output<number>();
  readonly pageSizeChange = output<number>();
  readonly pages = computed(() => this.pageSize() === 0 ? 1 : Math.max(1, Math.ceil(this.total() / this.pageSize())));
  readonly start = computed(() => this.total() === 0 ? 0 : this.pageSize() === 0 ? 1 : (this.page() - 1) * this.pageSize() + 1);
  readonly end = computed(() => this.pageSize() === 0 ? this.total() : Math.min(this.page() * this.pageSize(), this.total()));
}

const STATUS: Record<string, { label: string; tone: string }> = {
  pendiente: { label: 'Pendiente', tone: 'warning' }, pendiente_contacto: { label: 'Por confirmar', tone: 'warning' },
  contactando_cliente: { label: 'Contactando', tone: 'info' }, esperando_respuesta: { label: 'Esperando respuesta', tone: 'warning' },
  requiere_otro_horario: { label: 'Reprogramar', tone: 'warning' }, cliente_no_respondio: { label: 'Sin respuesta', tone: 'neutral' },
  confirmada: { label: 'Confirmada', tone: 'success' }, reprogramada: { label: 'Reprogramada', tone: 'info' },
  atendida: { label: 'Atendida', tone: 'success' }, cancelada: { label: 'Cancelada', tone: 'danger' }, no_asistio: { label: 'No asistió', tone: 'neutral' },
  borrador: { label: 'Borrador', tone: 'neutral' }, en_atencion: { label: 'En atención', tone: 'info' }, cerrada: { label: 'Cerrada', tone: 'success' },
};

@Component({
  selector: 'vet-status', standalone: true, changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<span class="vet-status" [attr.data-tone]="value().tone">{{ value().label }}</span>`,
})
export class VeterinarianStatusComponent {
  readonly status = input.required<string>();
  readonly value = computed(() => STATUS[this.status()] || { label: this.status(), tone: 'neutral' });
}

@Component({
  selector: 'vet-icon', standalone: true, changeDetection: ChangeDetectionStrategy.OnPush,
  host: { 'aria-hidden': 'true', class: 'vet-icon' },
  template: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    @switch (name()) {
      @case ('plus') { <path d="M12 5v14M5 12h14"/> }
      @case ('refresh') { <path d="M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 11-2l3 3M4 16l3 3a7 7 0 0 0 11-2"/> }
      @case ('search') { <circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/> }
      @case ('file') { <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM14 3v6h6M8 13h8M8 17h5"/> }
      @case ('edit') { <path d="m16 3 5 5-12 12-6 1 1-6zM14 5l5 5"/> }
      @case ('calendar') { <rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 11h18M8 15h3"/> }
      @case ('arrow') { <path d="M5 12h14m-5-5 5 5-5 5"/> }
      @case ('check') { <path d="m5 12 4 4L19 6"/> }
      @case ('download') { <path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/> }
      @case ('close') { <path d="m6 6 12 12M6 18 18 6"/> }
      @default { <circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h.01"/> }
    }
  </svg>`,
})
export class VeterinarianIconComponent {
  readonly name = input('file');
}
