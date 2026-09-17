import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { BlogArticle } from '../../core/models/blog.model';

@Component({
  selector: 'app-blog-card', standalone: true, imports: [RouterLink], changeDetection: ChangeDetectionStrategy.OnPush, host: { class: 'block h-full' },
  template: `<article class="group flex h-full flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_10px_30px_rgba(11,27,109,0.06)] transition hover:-translate-y-1 hover:shadow-xl"><div class="h-52 overflow-hidden"><img [src]="article().image" [alt]="article().imageAlt" loading="lazy" class="h-full w-full object-cover transition duration-500 group-hover:scale-105" /></div><div class="flex flex-1 flex-col p-6"><div class="flex items-center justify-between gap-3 text-xs"><span class="font-bold uppercase tracking-wider text-sky-600">{{ article().category }}</span><time class="text-slate-400">{{ article().date }}</time></div><h2 class="mt-3 text-xl font-extrabold leading-7 text-[#0B1B6D]">{{ article().title }}</h2><p class="mt-3 flex-1 text-sm leading-6 text-slate-600">{{ article().excerpt }}</p><a [routerLink]="['/blog', article().slug]" class="mt-6 inline-flex items-center gap-2 self-start font-bold text-[#FF6B35] transition hover:gap-3">Leer artículo <span aria-hidden="true">→</span></a></div></article>`,
})
export class BlogCardComponent { readonly article = input.required<BlogArticle>(); }
