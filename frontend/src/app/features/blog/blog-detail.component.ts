import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { BLOG_ARTICLES } from '../../core/data/blog.mock';

@Component({
  selector: 'app-blog-detail', standalone: true, imports: [RouterLink], changeDetection: ChangeDetectionStrategy.OnPush,
  template: `@if (article; as item) { <article><header class="bg-[#FFF9F4]"><div class="mx-auto max-w-4xl px-4 py-14 sm:px-6 lg:py-20"><a routerLink="/blog" class="font-bold text-sky-600">← Volver al blog</a><p class="mt-9 text-sm font-bold uppercase tracking-[0.18em] text-[#FF6B35]">{{ item.category }}</p><h1 class="mt-3 text-4xl font-black leading-tight text-[#0B1B6D] sm:text-5xl">{{ item.title }}</h1><time class="mt-5 block text-sm text-slate-500">{{ item.date }}</time></div></header><div class="mx-auto max-w-4xl px-4 py-10 sm:px-6"><img [src]="item.image" [alt]="item.imageAlt" class="h-72 w-full rounded-3xl object-cover shadow-lg sm:h-[430px]" /><div class="mx-auto max-w-3xl py-10">@for (paragraph of item.content; track paragraph) { <p class="mb-6 text-lg leading-8 text-slate-700">{{ paragraph }}</p> }<div class="mt-10 rounded-3xl bg-sky-50 p-6 text-slate-700"><strong class="text-[#0B1B6D]">Recuerda:</strong> esta información es educativa y no reemplaza una consulta veterinaria.</div><a routerLink="/blog" class="mt-10 inline-flex rounded-full bg-[#0B1B6D] px-6 py-3 font-bold text-white hover:bg-sky-500">Volver al blog</a></div></div></article> } @else { <div class="mx-auto max-w-3xl px-4 py-24 text-center"><h1 class="text-3xl font-black text-[#0B1B6D]">Artículo no encontrado</h1><a routerLink="/blog" class="mt-6 inline-block font-bold text-sky-600">Volver al blog</a></div> }`,
})
export class BlogDetailComponent {
  readonly article = BLOG_ARTICLES.find((item) => item.slug === inject(ActivatedRoute).snapshot.paramMap.get('slug'));
}
