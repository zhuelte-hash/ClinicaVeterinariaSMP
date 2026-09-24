import { ChangeDetectionStrategy, Component, inject, input, signal } from '@angular/core';
import { Router } from '@angular/router';
import { PharmacyProduct, Product } from '../../core/models/producto.model';
import { NoticeService } from '../../core/services/notice.service';
import { VisualSessionService } from '../../core/services/visual-session.service';
import { CartService } from '../../services/cart.service';

@Component({
  selector: 'app-product-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'block h-full' },
  template: `
    <article class="group flex h-full flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_10px_35px_rgba(11,27,109,0.06)] transition duration-300 hover:-translate-y-1 hover:shadow-[0_18px_45px_rgba(11,27,109,0.12)]">
      <div class="relative h-56 overflow-hidden bg-slate-100">
        <img [src]="item().image" [alt]="item().imageAlt" loading="lazy" class="h-full w-full object-cover transition duration-500 group-hover:scale-105" />
        @if (badge()) { <span class="absolute left-4 top-4 rounded-full bg-white/95 px-3 py-1 text-xs font-bold text-[#0B1B6D] shadow">{{ badge() }}</span> }
        <button type="button" (click)="favorite.update(value => !value)" class="absolute right-4 top-4 grid h-10 w-10 place-items-center rounded-full bg-white/95 shadow transition hover:scale-105" [class.text-[#FF6B35]]="favorite()" [class.text-slate-500]="!favorite()" [attr.aria-label]="favorite() ? 'Quitar de favoritos' : 'Añadir a favoritos'" [attr.aria-pressed]="favorite()">
          <svg class="h-5 w-5" viewBox="0 0 24 24" [attr.fill]="favorite() ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="1.8"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.5 1.1-1.1a5.5 5.5 0 0 0-.1-7.8Z"/></svg>
        </button>
      </div>
      <div class="flex flex-1 flex-col p-5">
        <p class="text-xs font-bold uppercase tracking-[0.12em] text-sky-600">{{ item().category }}</p>
        <h3 class="mt-2 min-h-12 text-lg font-extrabold leading-6 text-[#0B1B6D]">{{ item().name }}</h3>
        @if (presentation()) { <p class="mt-2 text-sm text-slate-500">Presentación: {{ presentation() }}</p> }
        <div class="mt-auto flex items-end gap-2 pt-5">
          <strong class="text-xl text-[#0B1B6D]">S/ {{ item().price.toFixed(2) }}</strong>
          @if (previousPrice()) { <span class="pb-0.5 text-sm text-slate-400 line-through">S/ {{ previousPrice()!.toFixed(2) }}</span> }
        </div>
        <p class="mt-2 text-xs font-semibold text-[#276508]">{{ item().stock }} unidades disponibles</p>
        <button type="button" (click)="buyNow()" [disabled]="item().stock <= 0" class="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-full bg-[#E0A71A] px-5 py-3 text-sm font-extrabold text-[#1A1E27] shadow-sm transition hover:-translate-y-0.5 hover:bg-[#1A98A2] hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1A98A2] disabled:cursor-not-allowed disabled:bg-[#D5D2D3] disabled:text-slate-500 disabled:hover:translate-y-0">
          <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v18m6-12H6"/><path d="M5 7h14l-1 13H6L5 7Z"/></svg>
          {{ item().stock > 0 ? 'Comprar ahora' : 'Producto agotado' }}
        </button>
        <button type="button" (click)="addToCart()" class="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-full border border-[#1A1E27]/20 bg-white px-5 py-2.5 text-sm font-bold text-[#1A1E27] transition hover:border-[#1A98A2] hover:bg-[#1A98A2]/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1A98A2]">
          <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3h2l2 12h11l2-8H6m4 12a1 1 0 1 1-2 0 1 1 0 0 1 2 0Zm9 0a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z"/></svg>
          {{ compactLabel() ? 'Agregar' : 'Añadir al carrito' }}
        </button>
      </div>
    </article>
  `,
})
export class ProductCardComponent {
  readonly item = input.required<Product | PharmacyProduct>();
  readonly compactLabel = input(false);
  readonly favorite = signal(false);
  private readonly cart = inject(CartService);
  private readonly notice = inject(NoticeService);
  private readonly session = inject(VisualSessionService);
  private readonly router = inject(Router);

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
    if (!this.session.isLoggedIn()) {
      this.cart.queuePending(cartItem);
      void this.router.navigate(['/login'], { queryParams: { returnUrl: '/carrito' } });
      return;
    }
    this.cart.add(cartItem);
    this.notice.show('Producto añadido al carrito');
  }

  buyNow(): void {
    const product = this.item();
    if (product.stock <= 0) return;
    const cartItem = this.toCartItem(product);
    if (!this.session.isLoggedIn()) {
      this.cart.queuePending(cartItem);
      void this.router.navigate(['/login'], { queryParams: { returnUrl: '/carrito' } });
      return;
    }
    this.cart.add(cartItem);
    void this.router.navigate(['/carrito']);
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
