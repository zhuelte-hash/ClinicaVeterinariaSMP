import { Component, computed, inject, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';
import { ClinicContactService } from '../../core/services/clinic-contact.service';

export type ManualContext = 'cita' | 'atencion' | 'orden' | 'venta' | 'cliente';

@Component({ selector: 'app-manual-communications-link', standalone: true, imports: [RouterLink], template: `
  @if (enabled()) { <a [routerLink]="path()" [queryParams]="params()" class="inline-flex items-center rounded-xl border border-teal-300 bg-white px-3 py-2 text-sm font-bold text-teal-800">{{ label() }}</a> }
` })
export class ManualCommunicationsLinkComponent {
  private readonly auth = inject(AuthService);
  private readonly contact = inject(ClinicContactService);
  readonly tipo = input<ManualContext>();
  readonly referencia = input<number>();
  readonly evento = input('');
  readonly label = input('Ver WhatsApp');
  readonly path = computed(() => ({ administrador: '/admin/comunicaciones', veterinario: '/veterinario/comunicaciones', cajero: '/caja/comunicaciones' } as Record<string, string>)[this.auth.currentUser()?.tipo || '']);
  readonly enabled = computed(() => this.contact.contact().modo_whatsapp === 'manual' && !!this.path() && this.auth.can(this.auth.isAdmin() ? 'usuarios' : this.auth.isCashier() ? 'ventas' : 'historias_clinicas'));
  readonly params = computed(() => ({ ...(this.tipo() && this.referencia() ? { tipo: this.tipo(), referencia: this.referencia() } : {}), ...(this.evento() ? { evento: this.evento() } : {}) }));
}
