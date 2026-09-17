import { ChangeDetectionStrategy, Component, computed, signal } from '@angular/core';
import { PHARMACY_PRODUCTS } from '../../core/data/productos.mock';
import { PharmacyCategory, PharmacyPresentation, PharmacySpecies } from '../../core/models/producto.model';
import { ProductCardComponent } from '../../shared/product-card/product-card.component';

type SortOption = 'Recomendados' | 'Menor precio' | 'Mayor precio' | 'Nombre A-Z';

@Component({
  selector: 'app-pharmacy-page', standalone: true, imports: [ProductCardComponent], changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="border-b border-sky-100 bg-gradient-to-br from-[#FFF9F4] via-white to-sky-50">
      <div class="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8 lg:py-20"><p class="text-sm font-bold uppercase tracking-[0.2em] text-sky-600">Cuidado responsable</p><h1 class="mt-3 text-4xl font-black text-[#0B1B6D] sm:text-5xl">Farmacia Veterinaria</h1><p class="mt-5 max-w-2xl text-lg text-slate-600">Productos de apoyo para el cuidado y bienestar de tu mascota.</p><div class="mt-7 inline-flex max-w-2xl items-start gap-3 rounded-2xl border border-orange-200 bg-orange-50 px-4 py-3 text-sm text-orange-900"><span class="font-black">i</span><p>Los productos deben utilizarse bajo recomendación de un médico veterinario.</p></div></div>
    </section>
    <section class="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <div class="mb-7 flex flex-col gap-4 rounded-3xl bg-white p-4 shadow-sm sm:flex-row">
        <label class="relative flex-1"><span class="sr-only">Buscar en farmacia</span><svg class="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg><input type="search" [value]="search()" (input)="setSearch($event)" placeholder="Buscar por nombre, categoría o presentación" class="w-full rounded-full border border-slate-200 py-3 pl-12 pr-4 outline-none focus:border-sky-400" /></label>
        <select aria-label="Ordenar productos" (change)="setSort($event)" class="rounded-full border border-slate-200 bg-white px-5 py-3 font-semibold text-slate-700 outline-none focus:border-sky-400">@for (option of sortOptions; track option) { <option [value]="option">{{ option }}</option> }</select>
        <button type="button" (click)="mobileFiltersOpen.update(value => !value)" class="rounded-full bg-[#0B1B6D] px-5 py-3 font-bold text-white lg:hidden" [attr.aria-expanded]="mobileFiltersOpen()">Filtros</button>
      </div>
      <div class="grid gap-8 lg:grid-cols-[270px_1fr]">
        <aside class="rounded-3xl border border-slate-200 bg-white p-6 lg:block" [class.hidden]="!mobileFiltersOpen()">
          <div class="flex items-center justify-between"><h2 class="text-xl font-extrabold text-[#0B1B6D]">Filtrar por</h2><button type="button" (click)="clearFilters()" class="text-xs font-bold text-sky-600">Limpiar</button></div>
          <div class="mt-7 space-y-7">
            <div><h3 class="mb-3 text-sm font-extrabold text-slate-800">Categoría</h3><div class="space-y-2">@for (category of categories; track category) { <button type="button" (click)="categoryFilter.set(categoryFilter() === category ? '' : category)" class="block w-full rounded-xl px-3 py-2 text-left text-sm transition hover:bg-sky-50" [class.bg-sky-50]="categoryFilter() === category" [class.font-bold]="categoryFilter() === category" [class.text-sky-700]="categoryFilter() === category">{{ category }}</button> }</div></div>
            <div><h3 class="mb-3 text-sm font-extrabold text-slate-800">Presentación</h3><div class="flex flex-wrap gap-2">@for (item of presentations; track item) { <button type="button" (click)="presentationFilter.set(presentationFilter() === item ? '' : item)" class="rounded-full border px-3 py-1.5 text-xs" [class.border-sky-500]="presentationFilter() === item" [class.bg-sky-50]="presentationFilter() === item">{{ item }}</button> }</div></div>
            <div><h3 class="mb-3 text-sm font-extrabold text-slate-800">Especie</h3><div class="space-y-2">@for (species of speciesOptions; track species) { <button type="button" (click)="speciesFilter.set(speciesFilter() === species ? '' : species)" class="block w-full rounded-xl px-3 py-2 text-left text-sm" [class.bg-sky-50]="speciesFilter() === species" [class.font-bold]="speciesFilter() === species">{{ species }}</button> }</div></div>
          </div>
        </aside>
        <div><div class="mb-5 flex items-center justify-between"><p class="text-sm text-slate-500">{{ filteredProducts().length }} resultados</p></div>
          @if (filteredProducts().length) { <div class="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">@for (product of filteredProducts(); track product.id) { <app-product-card [item]="product" [compactLabel]="true" /> }</div> }
          @else { <div class="rounded-3xl border border-dashed border-slate-300 py-16 text-center"><p class="text-xl font-bold text-[#0B1B6D]">No hay resultados con estos filtros</p><button type="button" (click)="clearFilters()" class="mt-4 font-bold text-sky-600">Limpiar filtros</button></div> }
        </div>
      </div>
    </section>
  `,
})
export class PharmacyPageComponent {
  readonly categories: PharmacyCategory[] = ['Medicamentos veterinarios', 'Alimento medicado', 'Higiene y cuidado', 'Suplementos'];
  readonly presentations: PharmacyPresentation[] = ['Tableta', 'Gotas', 'Jarabe', 'Crema', 'Lata', 'Polvo'];
  readonly speciesOptions: PharmacySpecies[] = ['Perros', 'Gatos', 'Uso general'];
  readonly sortOptions: SortOption[] = ['Recomendados', 'Menor precio', 'Mayor precio', 'Nombre A-Z'];
  readonly search = signal(''); readonly categoryFilter = signal<PharmacyCategory | ''>(''); readonly presentationFilter = signal<PharmacyPresentation | ''>(''); readonly speciesFilter = signal<PharmacySpecies | ''>(''); readonly sort = signal<SortOption>('Recomendados'); readonly mobileFiltersOpen = signal(false);
  readonly filteredProducts = computed(() => {
    const term = this.search().trim().toLocaleLowerCase('es');
    const products = PHARMACY_PRODUCTS.filter((product) => (!this.categoryFilter() || product.category === this.categoryFilter()) && (!this.presentationFilter() || product.presentation === this.presentationFilter()) && (!this.speciesFilter() || product.species === this.speciesFilter()) && (!term || `${product.name} ${product.category} ${product.presentation}`.toLocaleLowerCase('es').includes(term)));
    return [...products].sort((a, b) => this.sort() === 'Menor precio' ? a.price - b.price : this.sort() === 'Mayor precio' ? b.price - a.price : this.sort() === 'Nombre A-Z' ? a.name.localeCompare(b.name, 'es') : Number(Boolean(b.badge)) - Number(Boolean(a.badge)));
  });
  setSearch(event: Event): void { this.search.set((event.target as HTMLInputElement).value); }
  setSort(event: Event): void { this.sort.set((event.target as HTMLSelectElement).value as SortOption); }
  clearFilters(): void { this.categoryFilter.set(''); this.presentationFilter.set(''); this.speciesFilter.set(''); this.search.set(''); }
}
