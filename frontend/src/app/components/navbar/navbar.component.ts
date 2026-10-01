import { ChangeDetectionStrategy, Component, ElementRef, HostListener, OnDestroy, computed, inject, signal, viewChild } from '@angular/core';
import { CdkTrapFocus } from '@angular/cdk/a11y';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';
import { AuthDialogService } from '../../core/auth/auth-dialog.service';
import { VisualSessionService } from '../../core/services/visual-session.service';
import { NoticeService } from '../../core/services/notice.service';
import { CartService } from '../../services/cart.service';
import { PetCarrierIconComponent } from '../../shared/icons/pet-carrier-icon.component';
import { ServiceMenuIconComponent } from '../../features/services/service-menu-icon.component';
import { RELATED_PRODUCT_LINKS, SERVICES_MENU_CATEGORIES, ServicesMenuCategoryId } from '../../features/services/services-menu.data';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, CdkTrapFocus, PetCarrierIconComponent, ServiceMenuIconComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    .nav-link {
      position: relative;
      padding: 0.55rem 0.58rem;
       letter-spacing: 0.015em;
      transition: color .2s;
    }
    .nav-link::after {
      content: '';
      position: absolute;
      left: 0.58rem;
      right: 0.58rem;
      bottom: 2px;
      height: 2px;
      border-radius: 2px;
      background: #1A98A2;
      transform: scaleX(0);
      transform-origin: left;
      transition: transform .25s ease;
    }
    .nav-link:hover::after, .nav-link.active::after { transform: scaleX(1); }
     .nav-link:hover, .nav-link.active { color: #147d87; }
    .cart-drawer { animation: cart-drawer-in .22s ease-out both; }
    .cart-backdrop { animation: cart-backdrop-in .22s ease-out both; }
    @keyframes cart-drawer-in { from { transform: translateX(100%); } to { transform: translateX(0); } }
    @keyframes cart-backdrop-in { from { opacity: 0; } to { opacity: 1; } }
    @media (prefers-reduced-motion: reduce) {
      .cart-drawer, .cart-backdrop { animation: none; }
    }
  `],
  template: `
    <!-- Barra superior -->
    <div class="bg-[#1A1E27] text-white text-xs sm:text-[13px] font-medium">
       <div class="mx-auto flex max-w-[1450px] items-center justify-between gap-4 px-4 py-1.5 sm:px-6">
        <p class="flex items-center gap-2 truncate">
          <svg class="w-3.5 h-3.5 shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clip-rule="evenodd"/></svg>
          <span class="truncate">Jr. Quinua N° 178 – Cercado, Ayacucho</span>
          <span class="hidden md:inline text-[#1A98A2]">|</span>
           <a href="tel:965939522" class="hidden md:inline hover:text-[#E0A71A]">965 939 522</a>
        </p>
        <p class="hidden sm:flex items-center gap-1.5">vamospetshop&#64;gmail.com</p>
      </div>
    </div>

    <!-- Header principal -->
     <header class="sticky top-0 z-50 border-b border-[#e3e6ea] bg-white shadow-[0_4px_18px_rgba(11,27,109,0.06)]">
       <div class="mx-auto max-w-[1450px] px-4 sm:px-6">
        <div class="flex items-center justify-between h-[76px] gap-4">

          <!-- Logo -->
           <a routerLink="/inicio" class="flex min-w-0 shrink items-center gap-2 sm:gap-3" aria-label="Clínica Veterinaria San Martín de Porres, ir al inicio">
             <img src="/logo.png" alt="" class="h-11 w-11 shrink-0 rounded-full border border-[#D5D2D3] object-contain sm:h-12 sm:w-12" />
            <span class="leading-tight hidden xs:block sm:block">
              <span class="block text-[19px] font-extrabold text-[#1A1E27] tracking-tight">San Martín de Porres</span>
              <span class="block text-[10px] tracking-[0.22em] uppercase text-[#1A98A2] font-semibold">Clínica Veterinaria</span>
            </span>
          </a>

          <!-- Menú central -->
           <nav class="hidden xl:flex items-center gap-0 text-xs font-semibold text-gray-800 uppercase" aria-label="Navegación principal">
            <a routerLink="/inicio" routerLinkActive="active" class="nav-link">Nosotros</a>
            <div class="relative" (mouseenter)="desktopServicesOpen.set(true)" (mouseleave)="desktopServicesOpen.set(false)" (focusout)="closeDesktopMenuAfterFocus($event)" (keydown.escape)="desktopServicesOpen.set(false)">
              <button
                type="button"
                class="nav-link uppercase font-semibold flex items-center gap-1"
                [class.active]="desktopServicesOpen()"
                [attr.aria-expanded]="desktopServicesOpen()"
                aria-haspopup="menu"
                (click)="desktopServicesOpen.update(open => !open)"
              >Servicios
                <svg class="w-3 h-3 transition" [class.rotate-180]="desktopServicesOpen()" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg>
              </button>
              @if (desktopServicesOpen()) {
                <div class="absolute left-0 top-full pt-2 normal-case tracking-normal" role="menu" aria-label="Categorías de servicios">
                  <div class="flex w-[700px] overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_20px_55px_rgba(11,27,109,0.16)]">
                    <div class="w-[265px] shrink-0 border-r border-slate-100 p-3">
                      <a routerLink="/servicios" (click)="closeDesktopServices()" class="mb-2 flex items-center justify-between rounded-2xl bg-[#0B1B6D] px-4 py-3 text-xs font-bold text-white" role="menuitem"><span>Ver todos los servicios</span><span aria-hidden="true">→</span></a>
                      @for (category of serviceMenuCategories; track category.id) {
                        <button type="button" (mouseenter)="activeDesktopCategory.set(category.id)" (focus)="activeDesktopCategory.set(category.id)" (click)="activeDesktopCategory.set(category.id)" class="group flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left transition" [class.bg-[#0799AE]/10]="activeDesktopCategory() === category.id" [attr.aria-expanded]="activeDesktopCategory() === category.id" aria-haspopup="menu">
                          <span class="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#FFF9F4] text-[#0799AE] group-hover:bg-white"><app-service-menu-icon [icon]="category.icon" class="h-5 w-5" /></span>
                          <span class="min-w-0 flex-1"><strong class="block text-xs text-[#0B1B6D]">{{ category.name }}</strong><small class="mt-0.5 block text-[10px] leading-4 text-slate-500">{{ category.description }}</small></span>
                          <svg class="h-4 w-4 shrink-0 text-[#0799AE]" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"><path d="m7 4 6 6-6 6"/></svg>
                        </button>
                      }
                    </div>
                    <div class="max-h-[68vh] w-[435px] overflow-y-auto bg-[#FFF9F4]/60 p-5">
                      @for (category of serviceMenuCategories; track category.id) {
                        @if (activeDesktopCategory() === category.id) {
                          <div role="menu" [attr.aria-label]="category.name">
                            <div class="mb-4 flex items-center gap-2"><span class="h-2 w-2 rounded-full bg-[#F4C430]"></span><h3 class="text-sm font-extrabold text-[#0B1B6D]">{{ category.name }}</h3></div>
                            <div class="grid grid-cols-2 gap-x-5 gap-y-4">
                              @for (group of category.groups; track group.label) {
                                <div><p class="mb-1.5 text-[9px] font-black uppercase tracking-[0.12em] text-slate-400">{{ group.label }}</p>
                                  @for (link of group.links; track link.name) {
                                    <a [routerLink]="link.route" [fragment]="link.fragment" (click)="closeDesktopServices()" class="flex items-center gap-2 rounded-lg px-2 py-1.5 text-[11px] font-semibold text-slate-700 transition hover:bg-white hover:text-[#0799AE] focus-visible:bg-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#0799AE]" role="menuitem"><app-service-menu-icon [icon]="link.icon" class="h-4 w-4 text-[#0799AE]" />{{ link.name }}</a>
                                  }
                                </div>
                              }
                            </div>
                            @if (category.id === 'grooming') {
                              <div class="mt-5 border-t border-slate-200 pt-4"><p class="mb-2 text-[9px] font-black uppercase tracking-[0.12em] text-[#0B1B6D]">Productos relacionados</p><div class="flex flex-wrap gap-2">@for (link of relatedProductLinks; track link.name) { <a [routerLink]="link.route" (click)="closeDesktopServices()" class="inline-flex items-center gap-1.5 rounded-full border border-[#0799AE]/20 bg-white px-3 py-1.5 text-[10px] font-bold text-[#0B1B6D] hover:border-[#0799AE] hover:text-[#0799AE]" role="menuitem"><app-service-menu-icon [icon]="link.icon" class="h-3.5 w-3.5" />{{ link.name }}</a> }</div></div>
                            }
                          </div>
                        }
                      }
                    </div>
                  </div>
                </div>
              }
            </div>
            <a routerLink="/productos" routerLinkActive="active" class="nav-link">Productos</a>
            <a routerLink="/farmacia" routerLinkActive="active" class="nav-link">Farmacia</a>
             <a routerLink="/contacto" routerLinkActive="active" class="nav-link">Contáctanos</a>
            <a routerLink="/blog" routerLinkActive="active" class="nav-link">Blog</a>
          </nav>

          <!-- Acciones -->
          <div class="flex shrink-0 items-center gap-1 sm:gap-1.5">
             <a routerLink="/reservar-cita" class="hidden min-h-11 items-center rounded-full bg-[#0B1B6D] px-4 py-2.5 text-xs font-bold text-white transition hover:bg-[#147d87] md:inline-flex">Agenda tu cita</a>
            <a routerLink="/productos" title="Buscar" aria-label="Buscar productos" class="hidden h-10 w-10 items-center justify-center rounded-full text-[#0B1B6D] transition hover:bg-[#0799AE]/10 hover:text-[#0799AE] lg:flex">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35M10 17a7 7 0 110-14 7 7 0 010 14z"/></svg>
            </a>
            <div>
              <button #cartToggle type="button" (click)="toggleCart()" title="Carrito de compras" [attr.aria-label]="cartOpen() ? 'Cerrar carrito de compras' : 'Abrir carrito de compras'" [attr.aria-expanded]="cartOpen()" aria-controls="cart-drawer" class="relative grid h-10 w-10 place-items-center rounded-full text-[#0B1B6D] transition hover:bg-[#0799AE]/10 hover:text-[#0799AE]">
                <app-pet-carrier-icon class="h-6 w-6" />
                @if (cart.count() > 0) { <span class="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-[#F4C430] px-1 text-[10px] font-black text-[#0B1B6D]">{{ cart.count() }}</span> }
              </button>
              @if (cartOpen()) {
                <div class="cart-backdrop fixed inset-0 z-[60] bg-[#1A1E27]/45" (click)="closeCart()" aria-hidden="true"></div>
                <aside id="cart-drawer" role="dialog" aria-modal="true" aria-labelledby="cart-drawer-title" cdkTrapFocus [cdkTrapFocusAutoCapture]="true" class="cart-drawer fixed inset-y-0 right-0 z-[61] flex h-dvh w-[min(26rem,100vw)] flex-col bg-white text-[#1A1E27] shadow-[-12px_0_36px_rgba(11,27,109,0.16)]">
                  <div class="flex shrink-0 items-center justify-between border-b border-slate-200 px-5 py-4">
                    <h2 id="cart-drawer-title" class="text-lg font-extrabold text-[#0B1B6D]">Carrito de compra <span class="text-sm font-semibold text-slate-500">({{ cart.count() }})</span></h2>
                    <button type="button" (click)="closeCart()" class="grid h-11 w-11 place-items-center rounded-full text-slate-600 transition hover:bg-slate-100" aria-label="Cerrar carrito">✕</button>
                  </div>

                  <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-5 sm:px-5" aria-live="polite">
                    @if (cart.items().length === 0) {
                      <div class="flex min-h-full flex-col items-center justify-center text-center">
                        <app-pet-carrier-icon class="block h-12 w-12 text-slate-300" />
                        <p class="mt-4 text-sm font-semibold text-slate-600">No hay productos en el carrito.</p>
                      </div>
                    } @else {
                      <ul class="space-y-3">
                        @for (item of cart.items(); track item.id) {
                          <li class="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
                            <div class="flex gap-3">
                              <img [src]="item.imagen || '/logo.png'" [alt]="item.imageAlt || item.nombre" class="h-20 w-20 shrink-0 rounded-xl bg-slate-50 object-contain p-1" />
                              <div class="min-w-0 flex-1">
                                <p class="text-sm font-bold leading-snug text-[#0B1B6D]">{{ item.nombre }}</p>
                                <p class="mt-1 text-xs text-slate-600">S/ {{ item.precio.toFixed(2) }} por unidad</p>
                                <p class="mt-1 text-sm font-bold text-[#1A1E27]">S/ {{ (item.precio * item.cantidad).toFixed(2) }}</p>
                              </div>
                            </div>
                            <div class="mt-3 flex items-center justify-between gap-3 border-t border-slate-100 pt-3">
                              <div class="inline-flex items-center rounded-full border border-slate-200" [attr.aria-label]="'Cantidad de ' + item.nombre">
                                <button type="button" (click)="cart.setQty(item.id, item.cantidad - 1)" [attr.aria-label]="'Disminuir cantidad de ' + item.nombre" class="grid h-11 w-11 place-items-center rounded-l-full text-lg font-bold text-[#0B1B6D] hover:bg-brand-50">−</button>
                                <span class="min-w-7 text-center text-sm font-bold">{{ item.cantidad }}</span>
                                <button type="button" (click)="cart.setQty(item.id, item.cantidad + 1)" [disabled]="item.cantidad >= item.stock" [attr.aria-label]="'Aumentar cantidad de ' + item.nombre" class="grid h-11 w-11 place-items-center rounded-r-full text-lg font-bold text-[#0B1B6D] hover:bg-brand-50 disabled:cursor-not-allowed disabled:opacity-40">+</button>
                              </div>
                              <button type="button" (click)="cart.remove(item.id)" [attr.aria-label]="'Eliminar ' + item.nombre + ' del carrito'" class="grid h-11 w-11 place-items-center rounded-full text-rose-700 hover:bg-rose-50">
                                <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M4 7h16M9 7V4h6v3m3 0-1 13H7L6 7m4 4v5m4-5v5"/></svg>
                              </button>
                            </div>
                          </li>
                        }
                      </ul>
                    }
                  </div>

                  <div class="shrink-0 border-t border-slate-200 bg-white px-4 py-4 sm:px-5">
                    @if (cart.items().length > 0) {
                      <div class="mb-4 space-y-1.5 text-sm" aria-live="polite">
                        <div class="flex justify-between gap-3 text-slate-600"><span>Subtotal</span><span>S/ {{ cart.total().toFixed(2) }}</span></div>
                        <div class="flex justify-between gap-3 font-bold text-[#0B1B6D]"><span>Total de productos</span><span>S/ {{ cart.total().toFixed(2) }}</span></div>
                      </div>
                    }
                    <button type="button" (click)="closeCart()" class="inline-flex min-h-11 w-full items-center justify-center rounded-full border border-[#0B1B6D]/25 px-4 py-2.5 text-sm font-bold text-[#0B1B6D] transition hover:bg-brand-50">Seguir comprando</button>
                    @if (cart.items().length > 0) {
                      <button type="button" (click)="continuePurchase()" class="mt-2 inline-flex min-h-11 w-full items-center justify-center rounded-full bg-[#0B1B6D] px-4 py-2.5 text-sm font-bold text-white transition hover:bg-[#147d87]">Continuar con la compra</button>
                      <a routerLink="/carrito" (click)="closeCart()" class="mt-2 inline-flex min-h-10 w-full items-center justify-center text-sm font-semibold text-[#147d87] hover:underline">Ver carrito completo</a>
                    }
                  </div>
                </aside>
              }
            </div>
            @if (auth.isAuthenticated()) {
              <a [routerLink]="accountRoute()" class="hidden items-center gap-2 rounded-full border border-[#0B1B6D]/25 bg-white px-3 py-2 text-xs font-bold text-[#0B1B6D] transition hover:border-[#0799AE] hover:bg-[#0799AE]/10 md:inline-flex" aria-label="Mi cuenta"><svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM5 21a7 7 0 0 1 14 0"/></svg>Mi cuenta</a>
              <button type="button" (click)="logout()" class="hidden rounded-full px-3 py-2 text-xs font-bold text-rose-600 transition hover:bg-rose-50 md:inline-flex">Cerrar sesión</button>
            } @else {
              <button type="button" (click)="openLogin()" class="hidden items-center gap-2 rounded-full border border-[#0B1B6D]/25 bg-white px-3 py-2 text-xs font-bold text-[#0B1B6D] transition hover:border-[#0799AE] hover:bg-[#0799AE]/10 md:inline-flex" aria-label="Iniciar sesión"><svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM5 21a7 7 0 0 1 14 0"/></svg>Iniciar sesión</button>
            }
            <button type="button" (click)="mobileMenuOpen.update(open => !open)" class="grid h-10 w-10 place-items-center rounded-full text-[#0B1B6D] hover:bg-sky-50 xl:hidden" aria-label="Abrir menú de navegación" [attr.aria-expanded]="mobileMenuOpen()" aria-controls="mobile-navigation">
              @if (mobileMenuOpen()) { <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m6 6 12 12M18 6 6 18"/></svg> }
              @else { <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 7h16M4 12h16M4 17h16"/></svg> }
            </button>
          </div>
        </div>
      </div>

      <!-- Menú móvil -->
       @if (mobileMenuOpen()) { <nav id="mobile-navigation" class="max-h-[calc(100dvh-7rem)] overflow-y-auto overscroll-contain border-t border-gray-100 px-4 py-4 text-sm font-semibold uppercase tracking-wide text-gray-700 xl:hidden" aria-label="Navegación móvil">
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <a routerLink="/inicio" (click)="closeMobileMenu()" routerLinkActive="text-[#1A98A2]" class="rounded-xl px-3 py-2.5 hover:bg-sky-50 hover:text-[#1A98A2]">Nosotros</a>
          <button type="button" class="flex items-center gap-1 rounded-xl px-3 py-2.5 whitespace-nowrap hover:bg-sky-50 hover:text-[#1A98A2]" [attr.aria-expanded]="mobileServicesOpen()" aria-controls="mobile-services-menu" (click)="mobileServicesOpen.update(open => !open)" aria-label="Abrir menú de servicios">
            Servicios
            <svg class="h-3 w-3 transition" [class.rotate-180]="mobileServicesOpen()" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path d="m5 9 7 7 7-7"/></svg>
          </button>
          <a routerLink="/productos" (click)="closeMobileMenu()" routerLinkActive="text-[#1A98A2]" class="rounded-xl px-3 py-2.5 hover:bg-sky-50 hover:text-[#1A98A2]">Productos</a>
          <a routerLink="/farmacia" (click)="closeMobileMenu()" routerLinkActive="text-[#1A98A2]" class="rounded-xl px-3 py-2.5 hover:bg-sky-50 hover:text-[#1A98A2]">Farmacia</a>
           <a routerLink="/contacto" (click)="closeMobileMenu()" routerLinkActive="text-[#1A98A2]" class="rounded-xl px-3 py-2.5 hover:bg-sky-50 hover:text-[#1A98A2]">Contáctanos</a>
          <a routerLink="/blog" (click)="closeMobileMenu()" routerLinkActive="text-[#1A98A2]" class="rounded-xl px-3 py-2.5 hover:bg-sky-50 hover:text-[#1A98A2]">Blog</a>
        </div>
        @if (mobileServicesOpen()) {
          <div id="mobile-services-menu" class="mt-3 space-y-2 border-t border-[#D5D2D3] pt-3 normal-case tracking-normal">
            <a routerLink="/servicios" (click)="closeMobileMenu()" class="block rounded-xl bg-[#0B1B6D] px-3 py-2.5 text-center text-white">Ver todos los servicios</a>
            @for (category of serviceMenuCategories; track category.id) {
              <div class="overflow-hidden rounded-2xl border border-slate-200 bg-white">
                <button type="button" (click)="toggleMobileCategory(category.id)" class="flex w-full items-center gap-3 px-4 py-3 text-left" [attr.aria-expanded]="mobileServiceCategory() === category.id" [attr.aria-controls]="'mobile-' + category.id">
                  <span class="grid h-9 w-9 place-items-center rounded-xl bg-[#0799AE]/10 text-[#0799AE]"><app-service-menu-icon [icon]="category.icon" class="h-5 w-5" /></span><span class="flex-1 font-extrabold text-[#0B1B6D]">{{ category.name }}</span><svg class="h-4 w-4 transition" [class.rotate-180]="mobileServiceCategory() === category.id" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"><path d="m4 7 6 6 6-6"/></svg>
                </button>
                @if (mobileServiceCategory() === category.id) {
                  <div [id]="'mobile-' + category.id" class="border-t border-slate-100 bg-[#FFF9F4]/60 px-3 py-3">
                    @for (group of category.groups; track group.label) {
                      <p class="mb-1 mt-2 text-[9px] font-black uppercase tracking-wider text-slate-400 first:mt-0">{{ group.label }}</p>
                      <div class="grid gap-1 sm:grid-cols-2">@for (link of group.links; track link.name) { <a [routerLink]="link.route" [fragment]="link.fragment" (click)="closeMobileMenu()" class="flex items-center gap-2 rounded-xl px-3 py-2 text-[11px] font-semibold text-slate-700 hover:bg-white hover:text-[#0799AE]"><app-service-menu-icon [icon]="link.icon" class="h-4 w-4 text-[#0799AE]" />{{ link.name }}</a> }</div>
                    }
                    @if (category.id === 'grooming') { <div class="mt-3 border-t border-slate-200 pt-3"><p class="mb-2 text-[9px] font-black uppercase tracking-wider text-[#0B1B6D]">Productos relacionados</p><div class="grid gap-1 sm:grid-cols-3">@for (link of relatedProductLinks; track link.name) { <a [routerLink]="link.route" (click)="closeMobileMenu()" class="flex items-center gap-2 rounded-xl bg-white px-3 py-2 text-[11px] font-bold text-[#0B1B6D]"><app-service-menu-icon [icon]="link.icon" class="h-4 w-4 text-[#0799AE]" />{{ link.name }}</a> }</div></div> }
                  </div>
                }
              </div>
            }
          </div>
         }
         <div class="mt-4 grid gap-2 border-t border-slate-100 pt-4 sm:grid-cols-2">
           <a routerLink="/reservar-cita" (click)="closeMobileMenu()" class="rounded-full bg-[#0B1B6D] px-4 py-3 text-center text-white hover:bg-[#0799AE]">Agenda tu cita</a>
           @if (auth.isAuthenticated()) {
             <a [routerLink]="accountRoute()" (click)="closeMobileMenu()" class="flex items-center justify-center gap-2 rounded-full border border-[#0B1B6D]/25 px-4 py-3 text-[#0B1B6D] hover:bg-[#0799AE]/10"><svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM5 21a7 7 0 0 1 14 0"/></svg>Mi cuenta</a>
             <button type="button" (click)="logout()" class="rounded-full border border-rose-200 px-4 py-3 text-center font-bold text-rose-600 hover:bg-rose-50">Cerrar sesión</button>
           } @else {
             <button type="button" (click)="openLogin()" class="flex items-center justify-center gap-2 rounded-full border border-[#0B1B6D]/25 px-4 py-3 text-[#0B1B6D] hover:bg-[#0799AE]/10"><svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM5 21a7 7 0 0 1 14 0"/></svg>Iniciar sesión</button>
           }
         </div>
      </nav> }
    </header>
  `,
})
export class NavbarComponent implements OnDestroy {
  readonly cart = inject(CartService);
  readonly auth = inject(AuthService);
  private readonly notice = inject(NoticeService);
  private readonly authDialog = inject(AuthDialogService);
  private readonly visualSession = inject(VisualSessionService);
  private readonly router = inject(Router);
  private readonly cartToggle = viewChild<ElementRef<HTMLButtonElement>>('cartToggle');
  private previousBodyOverflow = '';
  readonly accountRoute = computed(() => {
    if (this.auth.isAdmin()) return '/admin/dashboard';
    if (this.auth.isCashier()) return '/caja/dashboard';
    if (this.auth.isVeterinarian()) return '/veterinario';
    return this.auth.isAuthenticated() ? '/reservar-cita' : '/login';
  });
  readonly desktopServicesOpen = signal(false);
  readonly mobileServicesOpen = signal(false);
  readonly mobileMenuOpen = signal(false);
  readonly cartOpen = signal(false);
  readonly serviceMenuCategories = SERVICES_MENU_CATEGORIES;
  readonly relatedProductLinks = RELATED_PRODUCT_LINKS;
  readonly activeDesktopCategory = signal<ServicesMenuCategoryId>('veterinary');
  readonly mobileServiceCategory = signal<ServicesMenuCategoryId | null>(null);

  toggleCart(): void {
    if (this.cartOpen()) {
      this.closeCart();
    } else {
      this.previousBodyOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      this.cartOpen.set(true);
      this.closeMobileMenu();
    }
  }

  closeCart(): void {
    if (!this.cartOpen()) return;
    this.cartOpen.set(false);
    document.body.style.overflow = this.previousBodyOverflow;
    this.cartToggle()?.nativeElement.focus();
  }

  continuePurchase(): void {
    if (this.cart.items().length === 0) return;
    this.closeCart();
    if (!this.auth.isAuthenticated() && !this.auth.isLoading()) {
      this.notice.show('Para continuar con tu pedido, inicia sesión.');
    }
    void this.router.navigate(['/checkout']);
  }

  @HostListener('document:keydown.escape')
  onEscape(): void { this.closeCart(); }

  ngOnDestroy(): void {
    if (this.cartOpen()) document.body.style.overflow = this.previousBodyOverflow;
  }

  closeDesktopMenuAfterFocus(event: FocusEvent): void {
    const container = event.currentTarget as HTMLElement;
    if (!container.contains(event.relatedTarget as Node | null)) {
      this.desktopServicesOpen.set(false);
    }
  }

  closeMobileMenu(): void {
    this.mobileMenuOpen.set(false);
    this.mobileServicesOpen.set(false);
    this.mobileServiceCategory.set(null);
  }

  closeDesktopServices(): void {
    this.desktopServicesOpen.set(false);
    this.activeDesktopCategory.set('veterinary');
  }

  toggleMobileCategory(category: ServicesMenuCategoryId): void {
    this.mobileServiceCategory.update((current) => current === category ? null : category);
  }

  logout(): void {
    this.auth.logout();
    this.visualSession.logout();
    this.cart.clear();
    this.closeMobileMenu();
    void this.router.navigateByUrl('/inicio');
  }

  openLogin(): void {
    this.closeMobileMenu();
    this.authDialog.open().subscribe((authenticated) => {
      if (authenticated) void this.router.navigateByUrl(this.accountRoute());
    });
  }
}
