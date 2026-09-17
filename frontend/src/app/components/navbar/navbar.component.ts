import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { CartService } from '../../services/cart.service';
import { VisualSessionService } from '../../core/services/visual-session.service';
import { PetCarrierIconComponent } from '../../shared/icons/pet-carrier-icon.component';
import { ServiceMenuIconComponent } from '../../features/services/service-menu-icon.component';
import { RELATED_PRODUCT_LINKS, SERVICES_MENU_CATEGORIES, ServicesMenuCategoryId } from '../../features/services/services-menu.data';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, PetCarrierIconComponent, ServiceMenuIconComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    .nav-link {
      position: relative;
      padding: 0.55rem 0.58rem;
      letter-spacing: 0.035em;
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
    .nav-link:hover, .nav-link.active { color: #1A98A2; }
  `],
  template: `
    <!-- Barra superior -->
    <div class="bg-[#1A1E27] text-white text-[12px] sm:text-[13px] font-medium">
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
    <header class="bg-white shadow-md sticky top-0 z-50 border-b border-gray-100">
       <div class="mx-auto max-w-[1450px] px-4 sm:px-6">
        <div class="flex items-center justify-between h-[76px] gap-4">

          <!-- Logo -->
          <a routerLink="/inicio" class="flex items-center gap-3 shrink-0">
            <img src="/logo.png" alt="Clínica Veterinaria San Martín de Porres" class="w-12 h-12 rounded-full object-cover border-2 border-[#D5D2D3] shadow-sm" />
            <span class="leading-tight hidden xs:block sm:block">
              <span class="block text-[19px] font-extrabold text-[#1A1E27] tracking-tight">San Martín de Porres</span>
              <span class="block text-[10px] tracking-[0.22em] uppercase text-[#1A98A2] font-semibold">Clínica Veterinaria</span>
            </span>
          </a>

          <!-- Menú central -->
          <nav class="hidden xl:flex items-center gap-0 text-[12px] font-bold text-gray-800 uppercase">
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
            <a routerLink="/contacto" routerLinkActive="active" class="nav-link">Contactanos</a>
            <a routerLink="/blog" routerLinkActive="active" class="nav-link">Blog</a>
          </nav>

          <!-- Acciones -->
          <div class="flex shrink-0 items-center gap-1 sm:gap-1.5">
            <a routerLink="/contacto" class="hidden rounded-full bg-[#0B1B6D] px-4 py-2.5 text-[11px] font-bold uppercase tracking-wide text-white shadow-sm transition hover:-translate-y-0.5 hover:bg-[#0799AE] md:inline-flex">Agenda tu cita</a>
            <a routerLink="/productos" title="Buscar" aria-label="Buscar productos" class="hidden h-10 w-10 items-center justify-center rounded-full text-[#0B1B6D] transition hover:bg-[#0799AE]/10 hover:text-[#0799AE] lg:flex">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35M10 17a7 7 0 110-14 7 7 0 010 14z"/></svg>
            </a>
            <div class="relative">
              <button type="button" (click)="cartOpen.update(open => !open)" title="Carrito de compras" aria-label="Abrir carrito de compras" [attr.aria-expanded]="cartOpen()" class="relative grid h-10 w-10 place-items-center rounded-full text-[#0B1B6D] transition hover:bg-[#0799AE]/10 hover:text-[#0799AE]">
                <app-pet-carrier-icon class="h-6 w-6" />
                @if (cart.count() > 0) { <span class="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-[#F4C430] px-1 text-[10px] font-black text-[#0B1B6D]">{{ cart.count() }}</span> }
              </button>
              @if (cartOpen()) {
                <div class="absolute right-0 top-12 z-50 w-72 rounded-2xl border border-slate-200 bg-white p-4 normal-case tracking-normal shadow-2xl" role="dialog" aria-label="Resumen del carrito">
                  <div class="flex items-center justify-between"><h2 class="font-extrabold text-[#0B1B6D]">Tu carrito</h2><button type="button" (click)="cartOpen.set(false)" class="rounded-full p-1 text-slate-400 hover:bg-slate-100" aria-label="Cerrar carrito">✕</button></div>
                  @if (cart.items().length === 0) { <div class="py-7 text-center"><app-pet-carrier-icon class="mx-auto block h-10 w-10 text-slate-300" /><p class="mt-3 text-sm font-semibold text-slate-500">Tu carrito está vacío.</p></div> }
                  @else { <div class="mt-3 max-h-52 space-y-2 overflow-auto">@for (item of cart.items(); track item.id) { <div class="flex items-center gap-3 rounded-xl bg-slate-50 p-2"><img [src]="item.imagen || '/logo.png'" [alt]="item.nombre" class="h-10 w-10 rounded-lg object-cover" /><p class="min-w-0 flex-1 truncate text-xs font-bold text-slate-700">{{ item.nombre }}</p><span class="text-xs font-black text-[#0B1B6D]">x{{ item.cantidad }}</span></div> }</div><a routerLink="/carrito" (click)="cartOpen.set(false)" class="mt-4 flex justify-center rounded-full bg-[#0B1B6D] px-4 py-2.5 text-xs font-bold text-white hover:bg-[#0799AE]">Ver carrito</a> }
                </div>
              }
            </div>
            <a [routerLink]="session.isLoggedIn() ? '/inicio' : '/login'" class="hidden items-center gap-2 rounded-full border border-[#0B1B6D]/25 bg-white px-3 py-2 text-xs font-bold text-[#0B1B6D] transition hover:border-[#0799AE] hover:bg-[#0799AE]/10 md:inline-flex" [attr.aria-label]="session.isLoggedIn() ? 'Mi cuenta' : 'Iniciar sesión'">
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM5 21a7 7 0 0 1 14 0"/></svg>{{ session.isLoggedIn() ? 'Mi cuenta' : 'Iniciar sesión' }}
            </a>
            <span class="hidden h-9 w-9 place-items-center rounded-full bg-[#F4C430]/20 text-[#F4C430] xl:grid" title="Cuidamos a tu mascota" aria-hidden="true"><svg class="h-5 w-5" viewBox="0 0 24 24" fill="currentColor"><circle cx="6" cy="8" r="2"/><circle cx="10" cy="5" r="2"/><circle cx="14" cy="5" r="2"/><circle cx="18" cy="8" r="2"/><path d="M12 10c-3.5 0-6 2.5-6 5.4C6 18.3 8.6 20 12 20s6-1.7 6-4.6c0-2.9-2.5-5.4-6-5.4Z"/></svg></span>
            <button type="button" (click)="mobileMenuOpen.update(open => !open)" class="grid h-10 w-10 place-items-center rounded-full text-[#0B1B6D] hover:bg-sky-50 xl:hidden" aria-label="Abrir menú de navegación" [attr.aria-expanded]="mobileMenuOpen()" aria-controls="mobile-navigation">
              @if (mobileMenuOpen()) { <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m6 6 12 12M18 6 6 18"/></svg> }
              @else { <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 7h16M4 12h16M4 17h16"/></svg> }
            </button>
          </div>
        </div>
      </div>

      <!-- Menú móvil -->
      @if (mobileMenuOpen()) { <nav id="mobile-navigation" class="border-t border-gray-100 px-4 py-4 text-[12px] font-bold uppercase tracking-wider text-gray-700 xl:hidden" aria-label="Navegación móvil">
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <a routerLink="/inicio" (click)="closeMobileMenu()" routerLinkActive="text-[#1A98A2]" class="rounded-xl px-3 py-2.5 hover:bg-sky-50 hover:text-[#1A98A2]">Nosotros</a>
          <button type="button" class="flex items-center gap-1 rounded-xl px-3 py-2.5 whitespace-nowrap hover:bg-sky-50 hover:text-[#1A98A2]" [attr.aria-expanded]="mobileServicesOpen()" aria-controls="mobile-services-menu" (click)="mobileServicesOpen.update(open => !open)" aria-label="Abrir menú de servicios">
            Servicios
            <svg class="h-3 w-3 transition" [class.rotate-180]="mobileServicesOpen()" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path d="m5 9 7 7 7-7"/></svg>
          </button>
          <a routerLink="/productos" (click)="closeMobileMenu()" routerLinkActive="text-[#1A98A2]" class="rounded-xl px-3 py-2.5 hover:bg-sky-50 hover:text-[#1A98A2]">Productos</a>
          <a routerLink="/farmacia" (click)="closeMobileMenu()" routerLinkActive="text-[#1A98A2]" class="rounded-xl px-3 py-2.5 hover:bg-sky-50 hover:text-[#1A98A2]">Farmacia</a>
          <a routerLink="/contacto" (click)="closeMobileMenu()" routerLinkActive="text-[#1A98A2]" class="rounded-xl px-3 py-2.5 hover:bg-sky-50 hover:text-[#1A98A2]">Contactanos</a>
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
           <a routerLink="/contacto" (click)="closeMobileMenu()" class="rounded-full bg-[#0B1B6D] px-4 py-3 text-center text-white hover:bg-[#0799AE]">Agenda tu cita</a>
           <a [routerLink]="session.isLoggedIn() ? '/inicio' : '/login'" (click)="closeMobileMenu()" class="flex items-center justify-center gap-2 rounded-full border border-[#0B1B6D]/25 px-4 py-3 text-[#0B1B6D] hover:bg-[#0799AE]/10"><svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM5 21a7 7 0 0 1 14 0"/></svg>{{ session.isLoggedIn() ? 'Mi cuenta' : 'Iniciar sesión' }}</a>
         </div>
      </nav> }
    </header>
  `,
})
export class NavbarComponent {
  readonly cart = inject(CartService);
  readonly session = inject(VisualSessionService);
  readonly desktopServicesOpen = signal(false);
  readonly mobileServicesOpen = signal(false);
  readonly mobileMenuOpen = signal(false);
  readonly cartOpen = signal(false);
  readonly serviceMenuCategories = SERVICES_MENU_CATEGORIES;
  readonly relatedProductLinks = RELATED_PRODUCT_LINKS;
  readonly activeDesktopCategory = signal<ServicesMenuCategoryId>('veterinary');
  readonly mobileServiceCategory = signal<ServicesMenuCategoryId | null>(null);

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
}
