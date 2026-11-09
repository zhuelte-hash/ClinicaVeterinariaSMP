import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { EstheticService } from './services-menu.data';
import { ServiceMenuIconComponent } from './service-menu-icon.component';

@Component({
  selector: 'app-esthetic-service-card', standalone: true, imports: [ServiceMenuIconComponent], changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'block h-full scroll-mt-36' },
  template: `<article class="site-card flex h-full gap-4 p-5 hover:-translate-y-0.5"><span class="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-brand-50 text-brand-600"><app-service-menu-icon [icon]="service().icon" class="h-5 w-5" /></span><div><p class="text-[10px] font-bold uppercase tracking-wider text-brand-600">{{ service().group }}</p><h3 class="mt-1 text-lg font-extrabold text-pet-900">{{ service().name }}</h3><p class="mt-2 text-sm leading-6 text-slate-600">{{ service().description }}</p></div></article>`,
})
export class EstheticServiceCardComponent { readonly service = input.required<EstheticService>(); }
