import { Component, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';
import { NoticeService } from '../../core/services/notice.service';
import { CartService } from '../../services/cart.service';

@Component({
  selector: 'app-carrito',
  standalone: true,
  imports: [RouterLink],
  template: `
    <header class="bg-[#0B1B6D] px-4 py-10 text-white sm:px-6 sm:py-12">
      <div class="mx-auto max-w-7xl">
        <p class="text-xs font-bold uppercase tracking-[.18em] text-[#aee5e9]">Tienda veterinaria</p>
        <h1 class="mt-2 text-3xl font-extrabold sm:text-4xl">Mi carrito</h1>
        <p class="mt-2 text-sm text-white/85">Revisa tus productos antes de continuar con el pedido.</p>
      </div>
    </header>

    <main class="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8 lg:py-14">
      @if (cart.items().length === 0) {
        <div class="site-card mx-auto max-w-xl px-6 py-12 text-center">
          <h2 class="text-xl font-bold text-[#0B1B6D]">Tu carrito está vacío</h2>
          <p class="mt-2 text-sm text-slate-600">Explora los productos para el cuidado de tu mascota.</p>
          <a routerLink="/productos" class="site-button mt-6">Ver productos</a>
        </div>
      } @else {
        <div class="grid items-start gap-7 lg:grid-cols-[minmax(0,1fr)_minmax(280px,340px)]">
          <section aria-labelledby="cart-products-title" class="min-w-0">
            <div class="mb-5 flex flex-wrap items-center justify-between gap-3">
              <h2 id="cart-products-title" class="text-xl font-bold text-[#0B1B6D]">Productos ({{ cart.count() }})</h2>
              <a routerLink="/productos" class="inline-flex min-h-11 items-center text-sm font-bold text-[#147d87] hover:underline">Seguir comprando →</a>
            </div>
            <div class="space-y-4">
              @for (it of cart.items(); track it.id) {
                <article class="site-card flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:p-5">
                  <img [src]="it.imagen || '/logo.png'" [alt]="it.imageAlt || it.nombre" class="h-28 w-full shrink-0 rounded-xl bg-[#f6f8f8] object-contain p-2 sm:h-24 sm:w-24" />
                  <div class="min-w-0 flex-1">
                    <h3 class="font-bold leading-snug text-[#0B1B6D]">{{ it.nombre }}</h3>
                    <p class="mt-1 text-sm text-slate-600">Precio unitario: S/ {{ it.precio.toFixed(2) }}</p>
                    <div class="mt-3 flex flex-wrap items-center gap-3">
                      <div class="inline-flex items-center rounded-full border border-slate-300 bg-white" [attr.aria-label]="'Cantidad de ' + it.nombre">
                        <button type="button" (click)="cart.setQty(it.id, it.cantidad - 1)" class="grid h-11 w-11 place-items-center rounded-l-full text-lg font-bold text-[#0B1B6D] hover:bg-brand-50" [attr.aria-label]="'Reducir cantidad de ' + it.nombre">−</button>
                        <span class="min-w-8 text-center text-sm font-bold" aria-live="polite">{{ it.cantidad }}</span>
                        <button type="button" (click)="cart.setQty(it.id, it.cantidad + 1)" [disabled]="it.cantidad >= it.stock" class="grid h-11 w-11 place-items-center rounded-r-full text-lg font-bold text-[#0B1B6D] hover:bg-brand-50 disabled:cursor-not-allowed disabled:opacity-40" [attr.aria-label]="'Aumentar cantidad de ' + it.nombre">+</button>
                      </div>
                      <button type="button" (click)="cart.remove(it.id)" class="inline-flex min-h-11 items-center text-sm font-semibold text-rose-700 hover:underline" [attr.aria-label]="'Eliminar ' + it.nombre + ' del carrito'">Eliminar</button>
                    </div>
                  </div>
                  <p class="text-right text-lg font-bold text-[#0B1B6D] sm:self-start">S/ {{ (it.precio * it.cantidad).toFixed(2) }}</p>
                </article>
              }
            </div>
            <button type="button" (click)="cart.clear()" class="mt-4 inline-flex min-h-11 items-center text-sm font-semibold text-slate-600 hover:text-rose-700 hover:underline">Vaciar carrito</button>
          </section>

          <aside class="site-card p-5 sm:p-6 lg:sticky lg:top-24" aria-labelledby="order-summary-title">
            <h2 id="order-summary-title" class="text-xl font-bold text-[#0B1B6D]">Resumen del pedido</h2>
            <dl class="mt-6 space-y-4 text-sm">
              <div class="flex justify-between gap-3 text-slate-600"><dt>Subtotal</dt><dd>S/ {{ cart.total().toFixed(2) }}</dd></div>
              <div class="flex justify-between gap-3 border-t border-slate-200 pt-4 text-lg font-bold text-[#0B1B6D]"><dt>Total de productos</dt><dd>S/ {{ cart.total().toFixed(2) }}</dd></div>
            </dl>
            <p class="mt-3 text-xs leading-5 text-slate-600">Si eliges delivery, el costo se calculará en el siguiente paso.</p>
            <button type="button" (click)="continuePurchase()" class="site-button mt-6 w-full">Continuar con la compra</button>
          </aside>
        </div>
      }
    </main>
  `,
})
export class CarritoComponent {
  readonly cart = inject(CartService);
  private readonly auth = inject(AuthService);
  private readonly notice = inject(NoticeService);
  private readonly router = inject(Router);

  continuePurchase(): void {
    if (this.cart.items().length === 0) return;
    if (!this.auth.isAuthenticated() && !this.auth.isLoading()) {
      this.notice.show('Para continuar con tu pedido, inicia sesión.');
    }
    void this.router.navigate(['/checkout']);
  }
}
