import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { PRODUCTS } from '../../core/data/productos.mock';
import { ProductCategory } from '../../core/models/producto.model';
import { ProductCardComponent } from '../../shared/product-card/product-card.component';

type CategoryFilter = 'Todos' | ProductCategory;

@Component({
  selector: 'app-products-page',
  standalone: true,
  imports: [ProductCardComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
     <section class="border-b border-[#e3e6ea] bg-[#FFF9F4]">
       <div class="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8 lg:py-16">
        <div class="max-w-3xl">
           <p class="mb-3 text-sm font-bold uppercase tracking-[0.14em] text-[#147d87]">Tienda veterinaria</p>
           <h1 class="text-3xl font-extrabold tracking-tight text-[#0B1B6D] sm:text-4xl lg:text-5xl">Productos para tu mascota</h1>
           <p class="mt-4 text-base leading-7 text-slate-600 sm:text-lg">Encuentra alimentos, accesorios, ropa y artículos para el bienestar de tu compañero.</p>
        </div>
         <div class="site-card mt-8 flex flex-col gap-5 p-4 sm:p-5 lg:flex-row lg:items-center lg:justify-between">
           <div class="flex gap-2 overflow-x-auto pb-2 lg:flex-wrap lg:overflow-visible lg:pb-0" role="group" aria-label="Categorías de productos">
            @for (category of categories; track category) {
               <button type="button" (click)="selectedCategory.set(category)" class="min-h-11 shrink-0 whitespace-nowrap rounded-full border px-4 py-2 text-sm font-semibold transition hover:border-[#1A98A2]" [class.border-[#0B1B6D]]="selectedCategory() === category" [class.bg-[#0B1B6D]]="selectedCategory() === category" [class.text-white]="selectedCategory() === category" [class.border-slate-300]="selectedCategory() !== category" [class.text-slate-700]="selectedCategory() !== category" [attr.aria-pressed]="selectedCategory() === category">{{ category }}</button>
            }
          </div>
          <label class="relative block w-full lg:max-w-sm">
            <span class="sr-only">Buscar productos</span>
             <svg class="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-[#147d87]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
             <input type="search" [value]="search()" (input)="setSearch($event)" placeholder="Buscar productos" class="site-input rounded-full pl-12" />
          </label>
        </div>
      </div>
    </section>
    <section class="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
       <div class="mb-7 flex flex-wrap items-end justify-between gap-2"><h2 class="text-2xl font-bold text-[#0B1B6D]">Nuestro catálogo</h2><p class="text-sm text-slate-600" aria-live="polite">{{ filteredProducts().length }} productos</p></div>
      @if (filteredProducts().length) {
         <div class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          @for (product of filteredProducts(); track product.id) { <app-product-card [item]="product" /> }
        </div>
      } @else {
         <div class="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center"><p class="text-xl font-bold text-[#0B1B6D]">No encontramos productos</p><p class="mt-2 text-slate-600">Prueba con otra categoría o término de búsqueda.</p><button type="button" (click)="clearFilters()" class="site-button mt-5">Limpiar filtros</button></div>
      }
    </section>
  `,
})
export class ProductsPageComponent {
  readonly categories: CategoryFilter[] = ['Todos', 'Alimentos', 'Accesorios', 'Ropa', 'Descanso y dormitorio'];
  readonly selectedCategory = signal<CategoryFilter>('Todos');
  readonly search = signal('');
  readonly filteredProducts = computed(() => {
    const term = this.search().trim().toLocaleLowerCase('es');
    return PRODUCTS.filter((product) => (this.selectedCategory() === 'Todos' || product.category === this.selectedCategory()) && (!term || `${product.name} ${product.category}`.toLocaleLowerCase('es').includes(term)));
  });

  constructor() {
    inject(ActivatedRoute).queryParamMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const category = params.get('categoria') as CategoryFilter | null;
      if (category && this.categories.includes(category)) this.selectedCategory.set(category);
    });
  }

  setSearch(event: Event): void { this.search.set((event.target as HTMLInputElement).value); }
  clearFilters(): void { this.search.set(''); this.selectedCategory.set('Todos'); }
}
