import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { CartService } from '../../services/cart.service';

@Component({
  selector: 'app-carrito',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="relative bg-pet-900 text-white py-10 text-center overflow-hidden">
      <img src="https://images.unsplash.com/photo-1601758228041-f3b2795255f1?auto=format&fit=crop&w=1600&q=80" class="absolute inset-0 w-full h-full object-cover opacity-30" alt="mascotas" />
      <h1 class="relative text-3xl font-extrabold">🛒 Carrito ({{ cart.count() }})</h1>
    </div>
    <div class="max-w-4xl mx-auto px-4 py-8">
      @if (cart.items().length === 0) { <div class="text-center py-12 bg-white rounded-2xl border">
        <p class="text-5xl mb-3">🐶</p>
        <p class="font-bold text-pet-900">Tu carrito está vacío</p>
        <a routerLink="/productos" class="mt-4 inline-block px-6 py-2 bg-brand-500 text-white rounded-full font-bold">Ver productos</a>
      </div> } @else { <div class="space-y-3">
        @for (it of cart.items(); track it.id) { <div class="bg-white rounded-2xl border p-4 flex gap-4 items-center">
          <img [src]="it.imagen || '/logo.png'" class="w-16 h-16 rounded-xl object-cover" [alt]="it.nombre" />
          <div class="flex-1">
            <p class="font-bold text-pet-900">{{ it.nombre }}</p>
            <p class="text-sm text-gray-500">S/ {{ it.precio.toFixed(2) }}</p>
            <div class="flex items-center gap-2 mt-2">
              <button (click)="cart.setQty(it.id, it.cantidad - 1)" class="w-7 h-7 rounded-full bg-gray-100 font-bold">-</button>
              <span class="font-bold">{{ it.cantidad }}</span>
               <button (click)="cart.setQty(it.id, it.cantidad + 1)" [disabled]="it.cantidad >= it.stock" class="w-7 h-7 rounded-full bg-gray-100 font-bold disabled:cursor-not-allowed disabled:opacity-40">+</button>
            </div>
          </div>
          <div class="text-right">
            <p class="font-extrabold">S/ {{ (it.precio * it.cantidad).toFixed(2) }}</p>
            <button (click)="cart.remove(it.id)" class="text-xs text-red-500 mt-2">Quitar</button>
          </div>
        </div> }
         <div class="bg-white rounded-2xl border p-5 flex flex-col gap-4 sm:flex-row sm:justify-between sm:items-center">
           <div class="flex items-center gap-4"><button (click)="cart.clear()" class="text-sm text-gray-500 underline">Vaciar</button><a routerLink="/productos" class="text-sm font-bold text-[#1A98A2] hover:underline">Seguir agregando productos</a></div>
           <div class="text-right"><p class="text-xl font-extrabold text-pet-900">Total: S/ {{ cart.total().toFixed(2) }}</p><a routerLink="/checkout" class="mt-3 inline-flex rounded-full bg-[#1A1E27] px-6 py-3 text-sm font-extrabold text-white transition hover:bg-[#1A98A2]">Continuar con la compra</a></div>
         </div>
         <p class="rounded-2xl bg-sky-50 p-4 text-center text-sm font-semibold text-[#0B1B6D]">Revisa las cantidades antes de continuar al formulario de compra y pago.</p>
      </div> }
    </div>
  `,
})
export class CarritoComponent {
  cart = inject(CartService);
}
