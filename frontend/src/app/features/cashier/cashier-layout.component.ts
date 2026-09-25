import { Component, computed, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';

@Component({
  selector: 'app-cashier-layout',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="min-h-screen bg-[#f5f7fa] text-slate-800">
      @if (drawerOpen()) {
        <button class="fixed inset-0 z-40 bg-slate-950/50 lg:hidden" aria-label="Cerrar menu" (click)="drawerOpen.set(false)"></button>
      }
      <aside class="sidebar fixed inset-y-0 left-0 z-50 flex flex-col bg-[#102a43] text-white" [class.drawer-open]="drawerOpen()">
        <div class="border-b border-white/10 px-6 py-6">
          <div class="flex items-center gap-3">
            <span class="grid h-11 w-11 place-items-center rounded-2xl bg-[#f4c430] font-black text-[#102a43]">SMP</span>
            <div><p class="font-black">Punto de caja</p><p class="text-xs text-slate-300">Clinica Veterinaria</p></div>
          </div>
        </div>
        <nav class="flex-1 p-4" aria-label="Navegacion de caja">
          <a routerLink="dashboard" routerLinkActive="active" (click)="drawerOpen.set(false)" class="nav-link flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-bold">
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 13h6V4H4v9Zm0 7h6v-3H4v3Zm10 0h6v-9h-6v9Zm0-13h6V4h-6v3Z"/></svg>
            Resumen de caja
          </a>
          <a routerLink="ventas" routerLinkActive="active" (click)="drawerOpen.set(false)" class="nav-link mt-2 flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-bold">
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3h2l2 13h11l2-9H6M9 21h.01M18 21h.01"/></svg>
            Punto de venta
          </a>
        </nav>
        <div class="border-t border-white/10 p-4">
          <p class="truncate text-sm font-bold">{{ cashierName() }}</p>
          <p class="mb-3 text-xs text-slate-400">Cajero</p>
          <button (click)="logout()" class="w-full rounded-xl border border-white/15 px-4 py-2.5 text-left text-sm font-semibold hover:bg-white/10">Cerrar sesion</button>
        </div>
      </aside>
      <div class="page-shell">
        <header class="sticky top-0 z-30 flex h-20 items-center border-b border-slate-200 bg-white/95 px-4 backdrop-blur sm:px-8">
          <button class="rounded-xl border border-slate-200 p-2.5 lg:hidden" aria-label="Abrir menu" (click)="drawerOpen.set(true)">☰</button>
          <div class="ml-3 lg:ml-0"><p class="text-xs font-bold uppercase tracking-[.18em] text-teal-600">Operacion diaria</p><h1 class="font-black text-[#102a43]">Panel del cajero</h1></div>
          <div class="ml-auto grid h-10 w-10 place-items-center rounded-xl bg-teal-100 font-black text-teal-800">{{ cashierInitials() }}</div>
        </header>
        <main class="p-4 sm:p-6 lg:p-8"><router-outlet /></main>
      </div>
    </div>
  `,
  styles: [`
    .sidebar { width: 16rem; }
    .page-shell { margin-left: 16rem; }
    .nav-link { color: rgb(203 213 225); }
    .nav-link:hover, .active { background: rgb(255 255 255 / .1); color: white; box-shadow: inset 3px 0 #f4c430; }
    @media (max-width: 1023px) { .sidebar { width: min(18rem, 86vw); transform: translateX(-105%); transition: transform .25s; } .sidebar.drawer-open { transform: translateX(0); } .page-shell { margin-left: 0; } }
  `],
})
export class CashierLayoutComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  readonly drawerOpen = signal(false);
  readonly cashierName = computed(() => this.auth.currentUser()?.nombre || 'Cajero');
  readonly cashierInitials = computed(() => this.cashierName().split(/\s+/).slice(0, 2).map((part) => part.charAt(0)).join('').toUpperCase());

  logout(): void {
    this.auth.logout();
    void this.router.navigateByUrl('/login');
  }
}
