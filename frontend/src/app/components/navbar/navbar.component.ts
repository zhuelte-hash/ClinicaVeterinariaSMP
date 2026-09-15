import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';
import { CartService } from '../../services/cart.service';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, CommonModule],
  styles: [`
    .nav-link {
      position: relative;
      padding: 0.5rem 0.9rem;
      letter-spacing: 0.06em;
      transition: color .2s;
    }
    .nav-link::after {
      content: '';
      position: absolute;
      left: 0.9rem;
      right: 0.9rem;
      bottom: 2px;
      height: 2px;
      border-radius: 2px;
      background: #0ea5e9;
      transform: scaleX(0);
      transform-origin: left;
      transition: transform .25s ease;
    }
    .nav-link:hover::after, .nav-link.active::after { transform: scaleX(1); }
    .nav-link:hover, .nav-link.active { color: #0284c7; }
  `],
  template: `
    <!-- Barra superior -->
    <div class="bg-pet-900 text-white text-[12px] sm:text-[13px] font-medium">
      <div class="max-w-7xl mx-auto px-4 py-1.5 flex justify-between items-center gap-4">
        <p class="flex items-center gap-2 truncate">
          <svg class="w-3.5 h-3.5 shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clip-rule="evenodd"/></svg>
          <span class="truncate">Jr. Quinua N° 178 – Cercado, Ayacucho</span>
          <span class="hidden md:inline text-sky-300">|</span>
          <span class="hidden md:inline">📞 965 939 522</span>
        </p>
        <p class="hidden sm:flex items-center gap-1.5">✉️ vamospetshop&#64;gmail.com</p>
      </div>
    </div>

    <!-- Header principal -->
    <header class="bg-white shadow-md sticky top-0 z-50 border-b border-gray-100">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-[76px] gap-4">

          <!-- Logo -->
          <a routerLink="/" class="flex items-center gap-3 shrink-0">
            <img src="/logo.png" alt="Clínica Veterinaria San Martín de Porres" class="w-12 h-12 rounded-full object-cover border-2 border-brand-200 shadow-sm" />
            <span class="leading-tight hidden xs:block sm:block">
              <span class="block text-[19px] font-extrabold text-pet-900 tracking-tight">San Martín de Porres</span>
              <span class="block text-[10px] tracking-[0.22em] uppercase text-brand-600 font-semibold">Clínica Veterinaria</span>
            </span>
          </a>

          <!-- Menú central -->
          <nav class="hidden lg:flex items-center gap-0.5 text-[13.5px] font-semibold tracking-wider text-gray-800 uppercase">
            <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{exact:true}" class="nav-link">Nosotros</a>
            <div class="relative group">
              <button class="nav-link uppercase font-semibold flex items-center gap-1">Servicios
                <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg>
              </button>
              <div class="absolute left-0 top-full pt-2 hidden group-hover:block">
                <div class="bg-white shadow-xl border border-gray-100 rounded-2xl w-68 py-2 min-w-[260px]">
                  <a *ngFor="let s of servicios" routerLink="/contacto" class="block px-5 py-2.5 hover:bg-brand-50 hover:text-brand-700 text-[13px] normal-case font-medium tracking-normal">{{ s }}</a>
                </div>
              </div>
            </div>
            <a routerLink="/" class="nav-link">Productos</a>
            <a routerLink="/" class="nav-link">Farmacia</a>
            <a routerLink="/contacto" routerLinkActive="active" class="nav-link">Contactanos</a>
            <a routerLink="/" class="nav-link">Blog</a>
          </nav>

          <!-- Acciones -->
          <div class="flex items-center gap-1.5 sm:gap-2 shrink-0">
            <button title="Buscar" class="w-10 h-10 hidden sm:flex items-center justify-center rounded-full text-gray-600 hover:bg-gray-100 hover:text-pet-900 transition">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35M10 17a7 7 0 110-14 7 7 0 010 14z"/></svg>
            </button>
            <a routerLink="/carrito" title="Carrito" class="relative w-10 h-10 flex items-center justify-center rounded-full text-gray-600 hover:bg-gray-100 hover:text-pet-900 transition">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.3 4.6a1 1 0 00.9 1.4H17M17 17a2 2 0 100 4 2 2 0 000-4zM9 21a2 2 0 100-4 2 2 0 000 4z"/></svg>
              <span *ngIf="cart.count() > 0" class="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-[11px] min-w-5 h-5 px-1 rounded-full flex items-center justify-center font-bold">{{ cart.count() }}</span>
            </a>
            <!-- Mi cuenta: personita -->
            <a routerLink="/users" title="Mi cuenta" class="w-10 h-10 flex items-center justify-center rounded-full border-2 border-pet-100 bg-pet-50 text-pet-900 hover:bg-pet-900 hover:text-white hover:border-pet-900 transition">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
            </a>
            <a routerLink="/contacto" class="hidden md:inline-flex ml-1 px-5 py-2.5 bg-brand-500 text-white text-[13px] font-bold uppercase tracking-wider rounded-full hover:bg-brand-600 shadow-md shadow-brand-200 transition">Reservar Cita</a>
          </div>
        </div>
      </div>

      <!-- Menú móvil -->
      <nav class="lg:hidden border-t border-gray-100 px-4 py-2.5 flex gap-5 overflow-x-auto text-[12px] font-bold uppercase tracking-wider text-gray-700">
        <a routerLink="/" class="whitespace-nowrap hover:text-brand-600">Nosotros</a>
        <a routerLink="/" class="whitespace-nowrap hover:text-brand-600">Servicios</a>
        <a routerLink="/" class="whitespace-nowrap hover:text-brand-600">Productos</a>
        <a routerLink="/" class="whitespace-nowrap hover:text-brand-600">Farmacia</a>
        <a routerLink="/contacto" class="whitespace-nowrap text-brand-600">Contactanos</a>
        <a routerLink="/" class="whitespace-nowrap hover:text-brand-600">Blog</a>
      </nav>
    </header>
  `,
})
export class NavbarComponent {
  cart = inject(CartService);
  servicios = ['Consulta Médica','Consulta a Domicilio','Consulta virtual','Especialidades','Cirugía','Internamiento','Medicina preventiva','Laboratorio y exámenes','Hospedaje','Grooming','Viaja con tu mascota'];
}
