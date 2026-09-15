import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { CartService } from '../../services/cart.service';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="relative bg-pet-900 text-white overflow-hidden">
      <img src="https://images.unsplash.com/photo-1548199973-03cce0bbc87b?auto=format&fit=crop&w=1600&q=80" alt="perritos felices" class="absolute inset-0 w-full h-full object-cover opacity-40" />
      <div class="relative max-w-7xl mx-auto px-4 py-20 text-center">
        <img src="/logo.png" alt="logo" class="w-20 h-20 mx-auto rounded-full border-4 border-white/40 shadow-lg mb-4 bg-white" />
        <h1 class="text-4xl sm:text-5xl font-extrabold mb-3">Clínica Veterinaria<br/>San Martín de Porres</h1>
        <p class="text-lg text-sky-100 mb-2">Jr. Quinua N° 178 – Cercado, Ayacucho | 965 939 522</p>
        <p class="text-sky-100 mb-8">Cuidado, amor y salud para tus mejores amigos 🐶🐱</p>
        <div class="flex justify-center gap-3 flex-wrap">
          <a routerLink="/contacto" class="px-6 py-3 bg-brand-500 rounded-full font-bold hover:bg-brand-600 shadow-lg">Reservar Cita</a>
          <a routerLink="/contacto" class="px-6 py-3 bg-white text-pet-900 rounded-full font-bold hover:bg-sky-100">Contáctanos</a>
        </div>
      </div>
    </div>

    <div class="max-w-7xl mx-auto px-4 py-10">
      <h2 class="text-2xl font-extrabold text-pet-900 text-center mb-6">Nuestros pacientes felices</h2>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
        <img src="https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?auto=format&fit=crop&w=400&q=80" class="h-48 w-full object-cover rounded-2xl shadow" alt="perrito" />
        <img src="https://images.unsplash.com/photo-1592194996308-7b43878e84a6?auto=format&fit=crop&w=400&q=80" class="h-48 w-full object-cover rounded-2xl shadow" alt="gatito" />
        <img src="https://images.unsplash.com/photo-1601758228041-f3b2795255f1?auto=format&fit=crop&w=400&q=80" class="h-48 w-full object-cover rounded-2xl shadow" alt="perro familia" />
        <img src="https://images.unsplash.com/photo-1558788353-f76d92427f16?auto=format&fit=crop&w=400&q=80" class="h-48 w-full object-cover rounded-2xl shadow" alt="perro feliz" />
      </div>

      <div class="grid md:grid-cols-3 gap-6 text-left">
        <div class="bg-white p-6 rounded-2xl shadow-sm border">
          <img src="https://images.unsplash.com/photo-1576201836106-db1758fd1c97?auto=format&fit=crop&w=600&q=80" class="h-36 w-full object-cover rounded-xl mb-4" alt="consulta" />
          <h3 class="font-bold text-pet-900 mb-1">Consulta Médica - S/ 50</h3>
          <p class="text-sm text-gray-600">Atención integral para perros, gatos y más.</p>
          <button (click)="add('c1','Consulta Médica',50)" class="mt-3 w-full py-2 bg-pet-700 text-white rounded-full text-sm font-bold hover:bg-pet-900">Agregar 🛒</button>
        </div>
        <div class="bg-white p-6 rounded-2xl shadow-sm border">
          <img src="https://images.unsplash.com/photo-1516734212186-a967f81ad0d7?auto=format&fit=crop&w=600&q=80" class="h-36 w-full object-cover rounded-xl mb-4" alt="grooming" />
          <h3 class="font-bold text-pet-900 mb-1">Grooming y Baño - S/ 60</h3>
          <p class="text-sm text-gray-600">Belleza y higiene con amor.</p>
          <button (click)="add('g1','Grooming y Baño',60)" class="mt-3 w-full py-2 bg-pet-700 text-white rounded-full text-sm font-bold hover:bg-pet-900">Agregar 🛒</button>
        </div>
        <div class="bg-white p-6 rounded-2xl shadow-sm border">
          <img src="https://images.unsplash.com/photo-1629909613654-28e377c37b09?auto=format&fit=crop&w=600&q=80" class="h-36 w-full object-cover rounded-xl mb-4" alt="vacunas" />
          <h3 class="font-bold text-pet-900 mb-1">Vacunas - S/ 45</h3>
          <p class="text-sm text-gray-600">Prevención y cuidado seguro.</p>
          <button (click)="add('v1','Vacuna',45)" class="mt-3 w-full py-2 bg-pet-700 text-white rounded-full text-sm font-bold hover:bg-pet-900">Agregar 🛒</button>
        </div>
      </div>
    </div>
  `,
})
export class HomeComponent {
  cart = inject(CartService);
  add(id: string, nombre: string, precio: number) { this.cart.add({ id, nombre, precio }); }
}
