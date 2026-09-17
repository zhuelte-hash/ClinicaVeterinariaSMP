import { ChangeDetectionStrategy, Component, computed, signal } from '@angular/core';
import { BLOG_ARTICLES } from '../../core/data/blog.mock';
import { BlogCategory } from '../../core/models/blog.model';
import { BlogCardComponent } from '../../shared/blog-card/blog-card.component';

type BlogFilter = 'Todos' | BlogCategory;

@Component({
  selector: 'app-blog-page', standalone: true, imports: [BlogCardComponent], changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="relative overflow-hidden bg-[#FFF9F4]"><div class="absolute -right-20 -top-24 h-72 w-72 rounded-full bg-orange-200/50"></div><div class="absolute right-32 top-20 h-28 w-28 rounded-full bg-sky-200/60"></div><div class="relative mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8 lg:py-24"><p class="text-sm font-bold uppercase tracking-[0.2em] text-[#FF6B35]">Consejos de nuestro equipo</p><h1 class="mt-3 text-5xl font-black text-[#0B1B6D]">Blog</h1><p class="mt-5 max-w-2xl text-lg leading-8 text-slate-600">Información confiable para cuidar mejor a tu mascota: consejos, prevención y bienestar.</p></div></section>
    <section class="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8"><div class="grid gap-8 lg:grid-cols-[220px_1fr]"><aside><h2 class="mb-4 text-sm font-extrabold uppercase tracking-wider text-slate-500">Categorías</h2><div class="flex gap-2 overflow-x-auto pb-2 lg:flex-col">@for (category of categories; track category) { <button type="button" (click)="selectedCategory.set(category)" class="whitespace-nowrap rounded-full px-5 py-2.5 text-left text-sm font-bold transition lg:rounded-xl" [class.bg-[#0B1B6D]]="selectedCategory() === category" [class.text-white]="selectedCategory() === category" [class.bg-white]="selectedCategory() !== category" [class.text-slate-600]="selectedCategory() !== category">{{ category }}</button> }</div></aside><div>@if (articles().length) { <div class="grid gap-6 md:grid-cols-2 xl:grid-cols-3">@for (article of articles(); track article.slug) { <app-blog-card [article]="article" /> }</div> } @else { <p class="rounded-3xl border border-dashed p-12 text-center text-slate-500">No hay artículos en esta categoría.</p> }</div></div></section>
  `,
})
export class BlogPageComponent {
  readonly categories: BlogFilter[] = ['Todos', 'Alimentación', 'Consejos', 'Educación', 'Salud'];
  readonly selectedCategory = signal<BlogFilter>('Todos');
  readonly articles = computed(() => this.selectedCategory() === 'Todos' ? BLOG_ARTICLES : BLOG_ARTICLES.filter((article) => article.category === this.selectedCategory()));
}
