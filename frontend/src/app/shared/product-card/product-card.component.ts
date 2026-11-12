import { ChangeDetectionStrategy, Component, inject, input, signal } from '@angular/core';
import { PharmacyProduct, Product } from '../../core/models/producto.model';
import { NoticeService } from '../../core/services/notice.service';
import { CartService } from '../../services/cart.service';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-product-card',
  standalone: true,
  imports: [RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'block h-full' },
  template: `
    <article class="site-card group flex h-full flex-col overflow-hidden hover:-translate-y-0.5">
      <div class="relative aspect-[4/3] overflow-hidden bg-[#f6f8f8]">
         <img [src]="item().image" [alt]="item().imageAlt" (error)="onImageError($event)" loading="lazy" class="h-full w-full object-contain p-3 transition duration-300 group-hover:scale-[1.03]" />
        @if (badge()) { <span class="absolute left-4 top-4 rounded-full border border-brand-200 bg-white/95 px-3 py-1 text-xs font-bold text-brand-700">{{ badge() }}</span> }
        <button type="button" (click)="favorite.update(value => !value)" class="absolute right-4 top-4 grid h-11 w-11 place-items-center rounded-full border border-slate-200 bg-white/95 transition hover:border-[#1A98A2] hover:scale-105" [class.text-[#a8462c]]="favorite()" [class.text-slate-600]="!favorite()" [attr.aria-label]="favorite() ? 'Quitar de favoritos' : 'Añadir a favoritos'" [attr.aria-pressed]="favorite()">
          <svg class="h-5 w-5" viewBox="0 0 24 24" [attr.fill]="favorite() ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="1.8"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.5 1.1-1.1a5.5 5.5 0 0 0-.1-7.8Z"/></svg>
        </button>
      </div>
      <div class="flex flex-1 flex-col p-5">
        <p class="text-xs font-bold uppercase tracking-[0.08em] text-brand-600">{{ item().category }}</p>
        <h3 class="mt-2 text-lg font-bold leading-6 text-pet-900"><a [routerLink]="['/productos', item().id]" class="hover:underline">{{ item().name }}</a></h3>
        <a [routerLink]="['/productos', item().id]" class="mt-2 text-sm font-semibold text-brand-600">Ver detalle y disponibilidad</a>
        @if (presentation()) { <p class="mt-2 text-sm text-slate-500">Presentación: {{ presentation() }}</p> }
        <div class="mt-auto flex items-end gap-2 pt-5">
          <strong class="text-xl text-pet-900">S/ {{ item().price.toFixed(2) }}</strong>
          @if (previousPrice()) { <span class="pb-0.5 text-sm text-slate-400 line-through">S/ {{ previousPrice()!.toFixed(2) }}</span> }
        </div>
        <p class="mt-2 text-xs font-semibold" [class.text-[#276508]]="item().stock > 0" [class.text-rose-700]="item().stock <= 0">{{ item().stock > 0 ? item().stock + ' unidades disponibles' : 'Sin stock' }}</p>
        <button type="button" (click)="addToCart()" [disabled]="item().stock <= 0" class="site-button mt-4 w-full">
          <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3h2l2 12h11l2-8H6m4 12a1 1 0 1 1-2 0 1 1 0 0 1 2 0Zm9 0a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z"/></svg>
          Agregar al carrito
        </button>
      </div>
    </article>
  `,
})
export class ProductCardComponent {
  readonly item = input.required<Product | PharmacyProduct>();
  readonly favorite = signal(false);
  private readonly cart = inject(CartService);
  private readonly notice = inject(NoticeService);

  badge(): string | undefined {
    const product = this.item();
    return 'badge' in product ? product.badge : undefined;
  }

  presentation(): string | undefined {
    const product = this.item();
    return 'presentation' in product ? product.presentation : undefined;
  }

  previousPrice(): number | undefined {
    const product = this.item();
    return 'previousPrice' in product ? product.previousPrice : undefined;
  }

  addToCart(): void {
    const product = this.item();
    if (product.stock <= 0) return;
    const cartItem = this.toCartItem(product);
    this.cart.add(cartItem);
    this.notice.show('Producto añadido al carrito');
  }

  onImageError(event: Event): void {
    const image = event.target as HTMLImageElement;
    if (image.src.endsWith('/logo.png')) return;
    image.src = '/logo.png';
  }

  private toCartItem(product: Product | PharmacyProduct) {
    return {
      id: product.id,
      nombre: product.name,
      precio: product.price,
      imagen: product.image,
      imageAlt: product.imageAlt,
      stock: product.stock,
    };
  }
}
