import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { EstheticService } from './services-menu.data';
import { ServiceMenuIconComponent } from './service-menu-icon.component';

@Component({
  selector: 'app-esthetic-service-card', standalone: true, imports: [ServiceMenuIconComponent], changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'block h-full scroll-mt-36' },
  template: `<article class="flex h-full gap-4 rounded-3xl border border-[#0799AE]/15 bg-white p-5 shadow-[0_10px_30px_rgba(11,27,109,0.05)] transition hover:-translate-y-0.5 hover:border-[#0799AE]/35 hover:shadow-[0_15px_35px_rgba(7,153,174,0.11)]"><span class="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-[#0799AE]/10 text-[#0799AE]"><app-service-menu-icon [icon]="service().icon" class="h-5 w-5" /></span><div><p class="text-[10px] font-bold uppercase tracking-wider text-[#0799AE]">{{ service().group }}</p><h3 class="mt-1 text-lg font-extrabold text-[#0B1B6D]">{{ service().name }}</h3><p class="mt-2 text-sm leading-6 text-slate-600">{{ service().description }}</p></div></article>`,
})
export class EstheticServiceCardComponent { readonly service = input.required<EstheticService>(); }
