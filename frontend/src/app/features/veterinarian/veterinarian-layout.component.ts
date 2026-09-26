import { Component, computed, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';

@Component({
  selector: 'app-veterinarian-layout',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="min-h-screen bg-[#f5f7fa] text-slate-800">
      @if (drawerOpen()) { <button class="fixed inset-0 z-40 bg-slate-950/50 lg:hidden" aria-label="Cerrar menú" (click)="drawerOpen.set(false)"></button> }
      <aside class="sidebar fixed inset-y-0 left-0 z-50 flex flex-col bg-[#0B1B6D] text-white" [class.drawer-open]="drawerOpen()">
        <div class="border-b border-white/10 px-6 py-6"><div class="flex items-center gap-3"><span class="grid h-11 w-11 place-items-center rounded-2xl bg-[#F4C430] font-black text-[#0B1B6D]">SMP</span><div><p class="font-black">Clínica Veterinaria</p><p class="text-xs text-sky-200">Panel veterinario</p></div></div></div>
        <nav class="flex-1 space-y-2 p-4" aria-label="Navegación veterinaria">
          <a routerLink="dashboard" routerLinkActive="active" (click)="drawerOpen.set(false)" class="nav-link flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-bold"><span class="text-lg">⌂</span>Resumen y solicitudes</a>
        </nav>
        <div class="border-t border-white/10 p-4"><p class="truncate text-sm font-bold">{{ veterinarianName() }}</p><p class="mb-3 text-xs text-sky-200">Veterinario</p><button (click)="logout()" class="w-full rounded-xl border border-white/15 px-4 py-2.5 text-left text-sm font-semibold hover:bg-white/10">Cerrar sesión</button></div>
      </aside>
      <div class="page-shell"><header class="sticky top-0 z-30 flex h-20 items-center border-b border-slate-200 bg-white/95 px-4 backdrop-blur sm:px-8"><button class="rounded-xl border border-slate-200 p-2.5 lg:hidden" aria-label="Abrir menú" (click)="drawerOpen.set(true)">☰</button><div class="ml-3 lg:ml-0"><p class="text-xs font-bold uppercase tracking-[.18em] text-[#0799AE]">Área privada</p><h1 class="font-black text-[#0B1B6D]">Panel del veterinario</h1></div><div class="ml-auto grid h-10 w-10 place-items-center rounded-xl bg-[#0799AE]/15 font-black text-[#0B1B6D]">{{ veterinarianInitials() }}</div></header><main class="p-4 sm:p-6 lg:p-8"><router-outlet /></main></div>
    </div>
  `,
  styles: [`
    .sidebar { width: 16rem; }
    .page-shell { margin-left: 16rem; }
    .nav-link { color: rgb(224 242 254); }
    .nav-link:hover, .active { background: rgb(255 255 255 / .12); color: white; box-shadow: inset 3px 0 #F4C430; }
    @media (max-width: 1023px) { .sidebar { width: min(18rem, 86vw); transform: translateX(-105%); transition: transform .25s; } .sidebar.drawer-open { transform: translateX(0); } .page-shell { margin-left: 0; } }
  `],
})
export class VeterinarianLayoutComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  readonly drawerOpen = signal(false);
  readonly veterinarianName = computed(() => this.auth.currentUser()?.nombre || 'Veterinario');
  readonly veterinarianInitials = computed(() => this.veterinarianName().split(/\s+/).slice(0, 2).map((part) => part.charAt(0)).join('').toUpperCase());

  logout(): void {
    this.auth.logout();
    void this.router.navigateByUrl('/login');
  }
}
