import { HttpClient } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { environment } from '../../../environments/environment';
import { CatalogProduct } from '../../core/services/public-products.service';
import { CartService } from '../../services/cart.service';
import { NoticeService } from '../../core/services/notice.service';
import { publicImageUrl } from '../../core/utils/public-image-url';

@Component({
  selector: 'app-product-detail', standalone: true, imports: [RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="mx-auto max-w-6xl px-4 py-12">
      <a routerLink="/productos" class="font-semibold text-brand-600">← Volver al catálogo</a>
      @if (error()) { <p class="mt-6 rounded-xl bg-rose-50 p-5 text-rose-700" role="alert">{{ error() }}</p><button type="button" (click)="load()" class="site-button mt-3">Reintentar</button> }
      @else if (product(); as item) {
        <article class="site-card mt-6 grid gap-8 p-6 md:grid-cols-2">
          <img [src]="item.imagen_url" [alt]="item.nombre" (error)="imageError($event)" class="aspect-square w-full rounded-2xl bg-slate-50 object-contain p-4">
          <div><p class="text-sm font-bold text-brand-600">{{ item.categoria_nombre }}</p><h1 class="mt-2 text-3xl font-extrabold">{{ item.nombre }}</h1>
            <p class="mt-5 whitespace-pre-line leading-7 text-slate-600">{{ item.descripcion || 'Consulta a la clínica para recibir orientación sobre este producto.' }}</p>
            @if (item.marca) { <p class="mt-4 font-semibold">Marca: {{ item.marca }}</p> }
            @if (item.presentacion) { <p class="mt-2 text-sm">Presentación: {{ item.presentacion }}</p> }
            <p class="mt-4 text-sm">Para: {{ item.especies.length ? item.especies.join(', ') : item.catalogo_origen?.especie === null ? 'Especie por confirmar' : 'Todas las especies' }}</p>
            <strong class="mt-6 block text-3xl">{{ item.precio_venta === null ? 'Precio por confirmar' : 'S/ ' + price(item)?.toFixed(2) }}</strong>
            @if (item.catalogo_origen?.fecha_consulta) { <p class="mt-2 text-xs text-slate-500">Precio referencial de catálogo consultado el {{ item.catalogo_origen?.fecha_consulta }}.</p> }
            @if (item.catalogo_origen?.tipo_precio_venta === 'publicado_historico_indexado') { <p class="mt-2 text-sm text-amber-800">Precio histórico, pendiente de actualización.</p> }
            @if (item.es_demostracion) { <p class="mt-3 font-bold text-amber-800">Existencias de demostración; no representan inventario real.</p> }
            <p class="mt-3 font-semibold" [class.text-rose-700]="item.stock_actual === 0">{{ item.stock_actual > 0 ? item.stock_actual + ' unidades disponibles' : 'Sin stock' }}</p>
            <button type="button" class="site-button mt-6" [disabled]="item.stock_actual <= 0 || item.precio_venta === null" (click)="add(item)">Agregar al carrito</button>
          </div>
        </article>
      } @else { <p class="py-12" role="status">Cargando producto…</p> }
    </section>`,
})
export class ProductDetailComponent {
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  private readonly cart = inject(CartService);
  private readonly notice = inject(NoticeService);
  readonly product = signal<CatalogProduct | null>(null);
  readonly error = signal('');
  constructor() { this.route.paramMap.pipe(takeUntilDestroyed()).subscribe(() => this.load()); }
  load(): void {
    this.product.set(null); this.error.set('');
    this.http.get<CatalogProduct>(`${environment.apiUrl}/catalogo/productos/${this.route.snapshot.paramMap.get('id')}`).subscribe({
      next: item => this.product.set({ ...item, imagen_url: publicImageUrl(item.imagen_url) }), error: () => this.error.set('El producto no está disponible o no se pudo cargar.'),
    });
  }
  price(item: CatalogProduct): number | null { return item.precio_venta === null ? null : Number(item.precio_venta); }
  imageError(event: Event): void { const image = event.target as HTMLImageElement; if (!image.src.endsWith('/catalogo/producto-sin-foto.svg')) image.src = '/catalogo/producto-sin-foto.svg'; }
  add(item: CatalogProduct): void { const price = this.price(item); if (price === null || item.stock_actual <= 0) return; this.cart.add({ id: String(item.id), nombre: item.nombre, precio: price, imagen: item.imagen_url, imageAlt: item.nombre, stock: item.stock_actual }); this.notice.show('Producto añadido al carrito'); }
}
