import { Component, computed, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';

interface NavigationItem {
  label: string;
  route: string;
  icon: string;
}

interface NavigationGroup {
  label: string;
  items: NavigationItem[];
}

@Component({
  selector: 'app-veterinarian-layout',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="vet-app min-h-screen text-slate-800">
      @if (drawerOpen()) {
        <button class="fixed inset-0 z-40 bg-slate-950/55 lg:hidden" aria-label="Cerrar menú" (click)="drawerOpen.set(false)"></button>
      }
      <aside class="sidebar fixed inset-y-0 left-0 z-50 flex flex-col text-white" [class.drawer-open]="drawerOpen()">
        <div class="border-b border-white/10 px-5 py-5">
          <div class="flex items-center gap-3">
            <span class="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-[#58d3c2] font-black text-[#102b35] shadow-lg">SMP</span>
            <div class="min-w-0"><p class="truncate font-black">Clínica Veterinaria</p><p class="text-xs text-teal-100/75">Centro clínico</p></div>
          </div>
        </div>
        <nav class="sidebar-nav flex-1 overflow-y-auto px-3 py-4" aria-label="Navegación veterinaria">
          @for (group of navigation; track group.label) {
            <p class="mb-1 mt-4 px-3 text-[10px] font-black uppercase tracking-[.18em] text-teal-100/45 first:mt-0">{{ group.label }}</p>
            @for (item of group.items; track item.route) {
              <a [routerLink]="item.route" routerLinkActive="active" [routerLinkActiveOptions]="{exact: true}" (click)="drawerOpen.set(false)" class="nav-link flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold">
                <span class="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-white/5 text-[10px] font-black tracking-tight">{{ item.icon }}</span>
                <span>{{ item.label }}</span>
              </a>
            }
          }
        </nav>
        <div class="border-t border-white/10 p-4">
          <div class="mb-3 flex items-center gap-3"><span class="grid h-9 w-9 place-items-center rounded-full bg-white/10 text-xs font-black">{{ veterinarianInitials() }}</span><div class="min-w-0"><p class="truncate text-sm font-bold">{{ veterinarianName() }}</p><p class="text-xs text-teal-100/60">Veterinario</p></div></div>
          <button (click)="logout()" class="w-full rounded-xl border border-white/10 px-4 py-2.5 text-left text-sm font-semibold hover:bg-white/10">Cerrar sesión</button>
        </div>
      </aside>
      <div class="page-shell">
        <header class="sticky top-0 z-30 flex h-20 items-center border-b border-slate-200/80 bg-white/90 px-4 backdrop-blur-xl sm:px-8">
          <button class="rounded-xl border border-slate-200 bg-white p-2.5 lg:hidden" aria-label="Abrir menú" (click)="drawerOpen.set(true)">☰</button>
          <div class="ml-3 lg:ml-0"><p class="text-[10px] font-black uppercase tracking-[.2em] text-[#168b83]">Gestión clínica</p><h1 class="font-black text-[#102b35]">Panel del veterinario</h1></div>
           <div class="ml-auto flex items-center gap-3"><span class="hidden rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700 md:block">● Turno activo</span><div class="grid h-10 w-10 place-items-center rounded-xl bg-[#dff8f3] font-black text-[#176f68]">{{ veterinarianInitials() }}</div></div>
        </header>
        <main class="p-4 sm:p-6 lg:p-8"><router-outlet /></main>
      </div>
    </div>
  `,
  styles: [`
    .vet-app { background: radial-gradient(circle at 88% 0, rgb(88 211 194 / .11), transparent 25rem), #f4f7f6; }
    .sidebar { width: 17.5rem; background: linear-gradient(180deg, #123b44, #0d2d35 56%, #071e25); box-shadow: 12px 0 38px rgb(7 30 37 / .16); }
    .page-shell { margin-left: 17.5rem; }
    .nav-link { color: rgb(213 236 233 / .76); transition: .18s ease; }
    .nav-link:hover { background: rgb(255 255 255 / .07); color: white; }
    .nav-link.active { background: #58d3c2; color: #102b35; box-shadow: 0 8px 22px rgb(0 0 0 / .18); }
    .nav-link.active span:first-child { background: rgb(16 43 53 / .12); }
    .sidebar-nav { scrollbar-color: rgb(255 255 255 / .15) transparent; scrollbar-width: thin; }
    @media (max-width: 1023px) { .sidebar { width: min(19rem, 88vw); transform: translateX(-105%); transition: transform .25s; } .sidebar.drawer-open { transform: translateX(0); } .page-shell { margin-left: 0; } }
  `],
})
export class VeterinarianLayoutComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  readonly drawerOpen = signal(false);
  readonly navigation: NavigationGroup[] = [
    { label: 'Inicio', items: [{ label: 'Nueva atención', route: 'consultas', icon: '01' }] },
    { label: 'Pacientes', items: [{ label: 'Historial', route: 'mascotas', icon: '03' }] },
    { label: 'Atención', items: [{ label: 'Hospitalización', route: 'hospitalizacion', icon: '06' }, { label: 'Hospedaje', route: 'hospedaje', icon: '07' }, { label: 'Vacunación', route: 'vacunacion', icon: '08' }, { label: 'Desparasitación', route: 'desparasitacion', icon: '09' }, { label: 'Estética', route: 'estetica', icon: '10' }, { label: 'A domicilio', route: 'domicilio', icon: '11' }] },
    { label: 'Diagnóstico y gestión', items: [{ label: 'Imágenes médicas', route: 'imagenes', icon: '12' }, { label: 'Laboratorio', route: 'laboratorio', icon: '13' }, { label: 'Reportes', route: 'reportes', icon: '15' }] },
  ];
  readonly veterinarianName = computed(() => this.auth.currentUser()?.nombre || 'Veterinario');
  readonly veterinarianInitials = computed(() => this.veterinarianName().split(/\s+/).slice(0, 2).map((part) => part.charAt(0)).join('').toUpperCase());

  logout(): void {
    this.auth.logout();
    void this.router.navigateByUrl('/login');
  }
}
