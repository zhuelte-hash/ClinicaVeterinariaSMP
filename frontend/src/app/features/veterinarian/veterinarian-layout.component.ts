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
      <header class="topbar flex items-center justify-between gap-4 border-b border-[#dfe7ed] bg-white px-5 py-4 sm:px-7">
        <div class="flex items-center gap-3"><span class="grid h-10 w-10 place-items-center rounded-[11px] bg-[#087f83] text-xl font-black text-white">✚</span><div><strong class="block text-base text-[#233748]">VET · Centro clínico</strong><small class="text-[#637888]">Gestión de atención veterinaria</small></div></div>
        <div class="flex items-center gap-3"><span class="hidden rounded-md bg-[#edf5f5] px-2.5 py-1.5 text-xs font-bold text-[#2e686b] sm:block">Almacenamiento clínico</span><span class="grid h-10 w-10 place-items-center rounded-xl bg-[#dff8f3] text-sm font-black text-[#176f68]">{{ veterinarianInitials() }}</span></div>
      </header>
      <div class="shell">
      <aside class="sidebar fixed inset-y-0 left-0 z-50 flex flex-col text-white" [class.drawer-open]="drawerOpen()">
        <div class="border-b border-white/10 px-5 py-5 lg:hidden"><strong>VET · Centro clínico</strong><small class="block text-xs text-teal-100/70">Gestión veterinaria</small></div>
        <nav class="sidebar-nav flex-1 overflow-y-auto px-3 py-5" aria-label="Navegación veterinaria">
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
      <div class="page-shell"><main class="w-full p-5 sm:p-7"><button class="mb-4 rounded-lg border border-[#dfe7ed] bg-white px-3 py-2 lg:hidden" aria-label="Abrir menú" (click)="drawerOpen.set(true)">☰ Menú</button><router-outlet /></main></div>
      </div>
    </div>
  `,
  styles: [`
     .vet-app { background: #f2f5f7; }
      .topbar { min-height: 76px; }
      .shell { display: grid; grid-template-columns: 13.875rem minmax(0, 1fr); min-height: calc(100vh - 76px); }
      .sidebar { position: relative; width: 13.875rem; background: #172f40; box-shadow: none; }
      .page-shell { min-width: 0; }
    .nav-link { color: #d5e3ed; transition: .18s ease; }
    .nav-link:hover { background: #25495e; color: white; }
      .nav-link.active { background: #246b77; color: white; box-shadow: inset 3px 0 #86dcd7; }
      .nav-link.active span:first-child { background: rgb(16 43 53 / .12); }
      .sidebar-nav { scrollbar-color: rgb(255 255 255 / .15) transparent; scrollbar-width: thin; }
      .crumb { color: #637888; font-size: 10px; font-weight: 800; letter-spacing: .14em; margin-bottom: 12px; }
       @media (max-width: 1023px) { .shell { display: block; } .sidebar { position: fixed; width: min(18rem, 88vw); transform: translateX(-105%); transition: transform .25s; } .sidebar.drawer-open { transform: translateX(0); } }
  `],
})
export class VeterinarianLayoutComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  readonly drawerOpen = signal(false);
  readonly navigation: NavigationGroup[] = [
    { label: 'Área de trabajo', items: [{ label: 'Inicio', route: 'inicio', icon: '01' }, { label: 'Citas', route: 'agenda', icon: '02' }, { label: 'Pacientes e historial', route: 'mascotas', icon: '03' }, { label: 'Nueva atención', route: 'nueva-atencion', icon: '04' }] },
    { label: 'Pacientes', items: [{ label: 'Hospedaje', route: 'hospedaje', icon: '05' }] },
    { label: 'Servicios clínicos', items: [{ label: 'Laboratorio', route: 'laboratorio', icon: '06' }, { label: 'Rayos X / Ecografía', route: 'imagenes', icon: '07' }, { label: 'Vacunas y controles', route: 'vacunacion', icon: '08' }, { label: 'Cirugía', route: 'cirugia', icon: '09' }, { label: 'Hospitalización', route: 'hospitalizacion', icon: '10' }, { label: 'Estética', route: 'estetica', icon: '11' }] },
    { label: 'Otros servicios', items: [{ label: 'Documentos', route: 'documentos', icon: '12' }] },
  ];
  readonly veterinarianName = computed(() => this.auth.currentUser()?.nombre || 'Veterinario');
  readonly veterinarianInitials = computed(() => this.veterinarianName().split(/\s+/).slice(0, 2).map((part) => part.charAt(0)).join('').toUpperCase());

  logout(): void {
    this.auth.logout();
    void this.router.navigateByUrl('/login');
  }
}
