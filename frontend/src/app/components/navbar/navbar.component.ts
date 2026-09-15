import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';
import { CartService } from '../../services/cart.service';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, CommonModule],
  template: `
    <div class="bg-pet-900 text-white text-xs sm:text-sm">
      <div class="max-w-7xl mx-auto px-4 py-1.5 flex justify-between items-center">
        <p class="flex items-center gap-2">📍 Jr. Quinua N° 178 – Cercado, Ayacucho | 📞 965 939 522</p>
        <p class="hidden sm:block">✉️ vamospetshop@gmail.com</p>
      </div>
    </div>
    <nav class="bg-white shadow-md sticky top-0 z-50 border-b border-gray-100">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-[72px] items-center">
          <a routerLink="/" class="flex items-center gap-2">
            <img src="/logo.png" alt="Clínica Veterinaria San Martín de Porres" class="w-12 h-12 rounded-full object-cover border-2 border-brand-200 shadow-sm" />
            <span class="leading-tight">
              <span class="block text-xl font-extrabold text-pet-900">San Martín de Porres</span>
              <span class="block text-[11px] tracking-widest uppercase text-brand-600 font-semibold">Clínica Veterinaria - Ayacucho</span>
            </span>
          </a>
          <div class="hidden lg:flex items-center gap-1 text-[15px] font-medium text-gray-700">
            <a routerLink="/" class="px-3 py-2 hover:text-brand-600">Nosotros</a>
            <div class="relative group">
              <button class="px-3 py-2 hover:text-brand-600 flex items-center gap-1">Servicios ▾</button>
              <div class="absolute left-0 top-full hidden group-hover:block bg-white shadow-xl border rounded-xl w-64 py-2">
                <a *ngFor="let s of servicios" routerLink="/contacto" class="block px-4 py-2 hover:bg-brand-50 hover:text-brand-700 text-sm">{{ s }}</a>
              </div>
            </div>
            <a routerLink="/" class="px-3 py-2 hover:text-brand-600">Laboratorio</a>
            <a routerLink="/" class="px-3 py-2 hover:text-brand-600">Farmacia</a>
            <a routerLink="/" class="px-3 py-2 hover:text-brand-600">Accesorios</a>
            <a routerLink="/contacto" routerLinkActive="text-brand-600 font-bold" class="px-3 py-2 hover:text-brand-600">Contacto</a>
            <a routerLink="/" class="px-3 py-2 hover:text-brand-600">Blog</a>
          </div>
          <div class="flex items-center gap-2">
            <button class="p-2 hover:bg-gray-100 rounded-full">🔍</button>
            <a routerLink="/carrito" class="relative p-2 hover:bg-gray-100 rounded-full">🛒<span *ngIf="cart.count() > 0" class="absolute -top-1 -right-1 bg-red-500 text-white text-[11px] w-5 h-5 rounded-full flex items-center justify-center font-bold">{{ cart.count() }}</span></a>
            <a routerLink="/users" class="hidden sm:inline-flex px-4 py-2 bg-pet-700 text-white text-sm font-semibold rounded-full hover:bg-pet-900">Mi Cuenta</a>
            <a routerLink="/contacto" class="inline-flex px-4 py-2 bg-brand-500 text-white text-sm font-semibold rounded-full hover:bg-brand-600">Reservar Cita</a>
          </div>
        </div>
      </div>
      <div class="lg:hidden border-t px-4 py-2 flex gap-4 overflow-x-auto text-sm text-gray-700">
        <a routerLink="/" class="whitespace-nowrap">Nosotros</a>
        <a routerLink="/" class="whitespace-nowrap">Servicios</a>
        <a routerLink="/" class="whitespace-nowrap">Laboratorio</a>
        <a routerLink="/" class="whitespace-nowrap">Farmacia</a>
        <a routerLink="/contacto" class="whitespace-nowrap font-bold text-brand-600">Contacto</a>
      </div>
    </nav>
  `,
})
export class NavbarComponent {
  cart = inject(CartService);
  servicios = ['Consulta Médica','Consulta a Domicilio','Consulta virtual','Especialidades','Cirugía','Internamiento','Medicina preventiva','Laboratorio y exámenes','Hospedaje','Grooming','Viaja con tu mascota'];
}
