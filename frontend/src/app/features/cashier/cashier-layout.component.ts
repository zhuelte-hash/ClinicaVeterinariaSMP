import { Component, computed, HostListener, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';
import { PanelHeaderComponent } from '../../shared/panel-header/panel-header.component';

@Component({
  selector: 'app-cashier-layout',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, PanelHeaderComponent],
  template: `
    <div class="clinic-panel cashier-app min-h-screen bg-[#f3f7f8] text-slate-800">
      <a href="#cashier-content" class="skip-link">Saltar al contenido</a>
      @if (drawerOpen()) {
        <button type="button" class="fixed inset-0 z-40 bg-slate-950/50 lg:hidden" aria-label="Cerrar menú" (click)="closeDrawer()"></button>
      }
      <aside id="cashier-navigation" class="sidebar fixed inset-y-0 left-0 z-50 flex flex-col text-white" [class.sidebar-collapsed]="collapsed()" [class.drawer-open]="drawerOpen()">
        <div class="flex h-20 items-center gap-3 px-4">
          <img src="/logo.png" alt="San Martín de Porres" class="brand-mark h-11 w-11 shrink-0 rounded-full object-contain" />
          @if (!collapsed()) {
            <div class="min-w-0"><p class="truncate text-sm font-extrabold tracking-tight">Clínica Veterinaria</p><p class="mt-0.5 text-[10px] font-semibold uppercase tracking-[.18em] text-[#8bd7e5]">San Martín de Porres</p></div>
          }
          <button type="button" class="ml-auto rounded-xl p-2 text-[#8bd7e5] hover:bg-white/10 lg:hidden" aria-label="Cerrar menú" (click)="closeDrawer()"><svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg></button>
        </div>
        <nav class="flex-1 space-y-2 overflow-y-auto px-3 py-5" aria-label="Navegación de caja">
          @if (!collapsed()) { <p class="mb-2 px-3 text-[10px] font-bold uppercase tracking-[.2em] text-[#8bd7e5]">Operación de caja</p> }
          <a routerLink="pedidos-web" routerLinkActive="active" ariaCurrentWhenActive="page" (click)="closeDrawer()" class="nav-link flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-bold" [attr.aria-label]="collapsed() ? 'Pedidos web / Pagos pendientes' : null" [title]="collapsed() ? 'Pedidos web / Pagos pendientes' : ''">
            <svg class="h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M6 3h12v18l-3-2-3 2-3-2-3 2V3ZM9 7h6M9 11h6M9 15h3" /></svg>
            @if (!collapsed()) { <span>Pedidos web / Pagos pendientes</span> }
          </a>
          <a routerLink="dashboard" routerLinkActive="active" ariaCurrentWhenActive="page" (click)="closeDrawer()" class="nav-link flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-bold" [attr.aria-label]="collapsed() ? 'Resumen de caja' : null" [title]="collapsed() ? 'Resumen de caja' : ''">
            <svg class="h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 13h6V4H4v9Zm0 7h6v-3H4v3Zm10 0h6v-9h-6v9Zm0-13h6V4h-6v3Z"/></svg>
            @if (!collapsed()) { <span>Resumen de caja</span> }
          </a>
          <a routerLink="ventas" routerLinkActive="active" ariaCurrentWhenActive="page" (click)="closeDrawer()" class="nav-link flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-bold" [attr.aria-label]="collapsed() ? 'Punto de venta' : null" [title]="collapsed() ? 'Punto de venta' : ''">
            <svg class="h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3 3h2l2 13h11l2-9H6M9 21h.01M18 21h.01"/></svg>
            @if (!collapsed()) { <span>Punto de venta</span> }
          </a>
        </nav>
        <div class="border-t border-white/10 p-3">
          @if (!collapsed()) { <div class="px-1 pb-3"><p class="truncate text-sm font-bold">{{ cashierName() }}</p><p class="text-xs text-[#8bd7e5]">Cajero</p></div> }
          <button type="button" (click)="logout()" class="flex min-h-10 w-full items-center justify-center gap-2 rounded-xl border border-white/15 px-3 py-2.5 text-sm font-semibold hover:border-[#56c4d8] hover:bg-[#56c4d8]/10" aria-label="Cerrar sesión">
            <svg viewBox="0 0 24 24" class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 17l5-5-5-5M15 12H3M14 3h5a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-5" /></svg>@if (!collapsed()) { <span>Cerrar sesión</span> }
          </button>
        </div>
      </aside>
      <div class="page-shell" [class.page-collapsed]="collapsed()">
        <app-panel-header role="cajero" navigationId="cashier-navigation" [collapsed]="collapsed()" [drawerOpen]="drawerOpen()" (menuToggled)="toggleSidebar()" (logoutRequested)="logout()" />
        <main id="cashier-content" class="p-4 sm:p-6 lg:p-8" tabindex="-1"><router-outlet /></main>
      </div>
    </div>
  `,
  styles: [`
    .sidebar { width: 17rem; background: linear-gradient(165deg, var(--brand-ink), #1c303c); box-shadow: 12px 0 35px rgb(var(--brand-ink-rgb) / .18); transition: width .25s, transform .25s; }
    .sidebar-collapsed { width: 5.25rem; }
    .page-shell { min-height: 100dvh; min-width: 0; margin-left: 17rem; transition: margin-left .25s; }
    .page-collapsed { margin-left: 5.25rem; }
    .brand-mark { background: white; box-shadow: 0 0 0 3px rgb(var(--brand-turquoise-rgb) / 25%); }
    .nav-link { color: rgb(203 213 225); }
    .nav-link:hover { background: rgb(86 196 216 / .1); color: white; }
    .active { background: var(--brand-action); color: white; box-shadow: 0 10px 24px rgb(var(--brand-ink-rgb) / .22); }
    .skip-link { position: fixed; left: 1rem; top: -5rem; z-index: 100; border-radius: .75rem; background: #111827; padding: .75rem 1rem; color: white; font-size: .8rem; font-weight: 700; }
    .skip-link:focus { top: 1rem; }
    @media (max-width: 1023px) { .sidebar, .sidebar-collapsed { width: min(18rem, 86vw); transform: translateX(-105%); } .sidebar.drawer-open { transform: translateX(0); } .page-shell, .page-collapsed { margin-left: 0; } }
    @media (prefers-reduced-motion: reduce) { .sidebar, .page-shell { transition: none; } }
  `],
})
export class CashierLayoutComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  readonly collapsed = signal(false);
  readonly drawerOpen = signal(false);
  readonly cashierName = computed(() => this.auth.currentUser()?.nombre || 'Cajero');

  closeDrawer(): void { this.drawerOpen.set(false); }
  toggleSidebar(): void {
    if (window.matchMedia('(max-width: 1023px)').matches) { this.collapsed.set(false); this.drawerOpen.update(open => !open); }
    else this.collapsed.update(collapsed => !collapsed);
  }

  @HostListener('document:keydown.escape') closeMenus(): void { this.closeDrawer(); }

  logout(): void {
    this.auth.logout();
    void this.router.navigateByUrl('/login');
  }
}
