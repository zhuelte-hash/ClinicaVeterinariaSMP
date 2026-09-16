import { Component, computed, input } from '@angular/core';
import { AdminStatus } from '../models/admin.models';

@Component({
  selector: 'admin-status-badge',
  standalone: true,
  template: `<span class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold" [class]="tone()"><span class="h-1.5 w-1.5 rounded-full bg-current"></span>{{ status() }}</span>`,
})
export class StatusBadgeComponent {
  readonly status = input.required<AdminStatus>();
  readonly tone = computed(() => {
    switch (this.status()) {
      case 'Activo': case 'Confirmada': case 'Pagada': case 'Completada': return 'bg-emerald-50 text-emerald-700';
      case 'Pendiente': return 'bg-amber-50 text-amber-700';
      case 'Bajo stock': case 'Cancelada': return 'bg-rose-50 text-rose-700';
      default: return 'bg-slate-100 text-slate-600';
    }
  });
}
