import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { CartService } from '../../services/cart.service';

@Component({
  selector: 'app-carrito',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="relative bg-pet-900 text-white py-10 text-center overflow-hidden">
      <img src="https://images.unsplash.com/photo-1601758228041-f3b2795255f1?auto=format&fit=crop&w=1600&q=80" class="absolute inset-0 w-full h-full object-cover opacity-30" alt="mascotas" />
      <h1 class="relative text-3xl font-extrabold">🛒 Carrito ({{ cart.count() }})</h1>
    </div>
    <div class="max-w-4xl mx-auto px-4 py-8">
      <div *ngIf="cart.items().length === 0" class="text-center py-12 bg-white rounded-2xl border">
        <p class="text-5xl mb-3">🐶</p>
        <p class="font-bold text-pet-900">Tu carrito está vacío</p>
        <a routerLink="/" class="mt-4 inline-block px-6 py-2 bg-brand-500 text-white rounded-full font-bold">Ver servicios</a>
      </div>
      <div *ngIf="cart.items().length > 0" class="space-y-3">
        <div *ngFor="let it of cart.items()" class="bg-white rounded-2xl border p-4 flex gap-4 items-center">
          <img [src]="it.imagen || '/logo.png'" class="w-16 h-16 rounded-xl object-cover" alt="" />
          <div class="flex-1">
            <p class="font-bold text-pet-900">{{ it.nombre }}</p>
            <p class="text-sm text-gray-500">S/ {{ it.precio.toFixed(2) }}</p>
            <div class="flex items-center gap-2 mt-2">
              <button (click)="cart.setQty(it.id, it.cantidad - 1)" class="w-7 h-7 rounded-full bg-gray-100 font-bold">-</button>
              <span class="font-bold">{{ it.cantidad }}</span>
              <button (click)="cart.setQty(it.id, it.cantidad + 1)" class="w-7 h-7 rounded-full bg-gray-100 font-bold">+</button>
            </div>
          </div>
          <div class="text-right">
            <p class="font-extrabold">S/ {{ (it.precio * it.cantidad).toFixed(2) }}</p>
            <button (click)="cart.remove(it.id)" class="text-xs text-red-500 mt-2">Quitar</button>
          </div>
        </div>
        <div class="bg-white rounded-2xl border p-5 flex justify-between items-center">
          <button (click)="cart.clear()" class="text-sm text-gray-500 underline">Vaciar</button>
          <p class="text-xl font-extrabold text-pet-900">Total: S/ {{ cart.total().toFixed(2) }}</p>
        </div>
        <button (click)="pedir()" class="w-full py-3 bg-[#25D366] text-white font-bold rounded-2xl">Pedir por WhatsApp 🟢</button>
      </div>
    </div>
  `,
})
export class CarritoComponent {
  cart = inject(CartService);
  pedir() {
    const lines = this.cart.items().map(i => `- ${i.nombre} x${i.cantidad} = S/${(i.precio*i.cantidad).toFixed(2)}`).join('%0A');
    window.open(`https://wa.me/51965939522?text=Hola quiero comprar:%0A${lines}%0A%0ATotal: S/${this.cart.total().toFixed(2)}`, '_blank');
  }
}
