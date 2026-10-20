import { Component, HostListener, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';

interface NavigationItem {
  label: string;
  route: string;
  icon: 'grid' | 'calendar' | 'users' | 'plus' | 'home' | 'file' | 'lab' | 'image' | 'vaccine' | 'surgery' | 'bed' | 'sparkle';
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
      <a href="#veterinarian-content" class="skip-link">Saltar al contenido</a>
      <aside class="sidebar fixed inset-y-0 left-0 z-50 flex flex-col text-white transition-all duration-300" [class.sidebar-collapsed]="collapsed()" [class.drawer-open]="drawerOpen()">
         <div class="brand-row flex h-20 items-center gap-3 px-4">
          <div class="brand-mark grid h-11 w-11 shrink-0 place-items-center rounded-2xl text-sm font-black">VET</div>
          @if (!collapsed()) {
            <div class="min-w-0"><p class="truncate text-sm font-extrabold tracking-tight">Clínica Veterinaria</p><p class="mt-0.5 text-[10px] font-semibold uppercase tracking-[.18em] text-[#8bd7e5]">Centro clínico</p></div>
           }
           <button type="button" (click)="toggleSidebar()" class="ml-auto grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-white/15 text-[#8bd7e5] hover:bg-white/10" [attr.aria-label]="collapsed() ? 'Expandir menú' : 'Contraer menú'"><span aria-hidden="true">{{ collapsed() ? '»' : '«' }}</span></button>
        </div>

        <nav class="flex-1 space-y-1 overflow-y-auto px-3 py-5" aria-label="Navegación veterinaria">
          @for (group of navigation; track group.label) {
            @if (!collapsed()) { <p class="mb-2 mt-4 px-3 text-[10px] font-bold uppercase tracking-[.2em] text-[#8bd7e5] first:mt-0">{{ group.label }}</p> }
            @for (item of group.items; track item.route) {
              <a [routerLink]="item.route" routerLinkActive="active-link" [routerLinkActiveOptions]="{ exact: item.route === 'inicio' }" (click)="closeDrawer()" class="nav-link group flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm font-medium" [title]="collapsed() ? item.label : ''">
                <span class="nav-icon grid h-8 w-8 shrink-0 place-items-center rounded-xl"><svg viewBox="0 0 24 24" class="h-[18px] w-[18px]" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  @switch (item.icon) {
                    @case ('grid') { <path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z"/> }
                    @case ('home') { <path d="m3 11 9-8 9 8M5 10v10h14V10M9 20v-6h6v6"/> }
                    @case ('calendar') { <rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/> }
                    @case ('users') { <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/> }
                    @case ('plus') { <circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/> }
                    @case ('file') { <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM14 3v6h6M8 13h8M8 17h6"/> }
                    @case ('lab') { <path d="M9 3v6l-5 9a2 2 0 0 0 1.8 3h12.4A2 2 0 0 0 20 18l-5-9V3M8 3h8M7 16h10"/> }
                    @case ('image') { <rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9" r="1.5"/><path d="m21 15-5-5L5 20"/> }
                    @case ('vaccine') { <path d="m15 4 5 5M13 6l5 5M4 20l6-6M3 21l4-1 10-10-3-3L4 17z"/> }
                    @case ('surgery') { <path d="M4 20 14 10M12 4l8 8M14 3l7 7M4 20l-1 1 1-1 1-1M8 16l3 3"/> }
                    @case ('bed') { <path d="M3 18v-7M3 15h18v3M7 11V8a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v3M3 20v1M21 20v1"/> }
                    @case ('sparkle') { <path d="m12 3 1.6 5.4L19 10l-5.4 1.6L12 17l-1.6-5.4L5 10l5.4-1.6zM19 16l.7 2.3L22 19l-2.3.7L19 22l-.7-2.3L16 19l2.3-.7z"/> }
                  }
                </svg></span>
                @if (!collapsed()) { <span>{{ item.label }}</span> }
              </a>
            }
          }
        </nav>

        <button (click)="logout()" class="m-3 flex min-h-10 items-center justify-center gap-2 rounded-xl border border-white/15 bg-white/5 text-xs font-bold text-[#8bd7e5] transition hover:border-[#56c4d8] hover:bg-[#56c4d8]/10 hover:text-white" aria-label="Cerrar sesión"><svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 17l5-5-5-5M15 12H3M14 3h5a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-5"/></svg>@if (!collapsed()) { <span>Cerrar sesión</span> }</button>
       </aside>
       @if (drawerOpen()) { <button type="button" class="drawer-backdrop fixed inset-0 z-40 bg-slate-950/50" aria-label="Cerrar menú" (click)="closeDrawer()"></button> }

       <div class="page-shell transition-all duration-300" [class.page-collapsed]="collapsed()">
          <div class="mobile-topbar fixed inset-x-0 top-0 z-30 flex h-[4.5rem] items-center bg-[#111827] px-4 shadow-lg lg:hidden"><button type="button" (click)="toggleSidebar()" class="rounded-xl border border-white/20 px-3 py-2 text-sm font-bold text-white">Menú</button><span class="ml-3 text-sm font-black text-[#8bd7e5]">Panel veterinario</span></div>
         <main id="veterinarian-content" class="mx-auto w-full max-w-[1600px] p-4 sm:p-6 lg:p-8" tabindex="-1">
          <router-outlet />
        </main>
      </div>
    </div>
  `,
  styles: [`
    .vet-app { min-height: 100dvh; background: #f5faf8; }
    .sidebar { width: 17rem; background: linear-gradient(165deg, #161d2b 0%, #111827 52%, #030712 100%); box-shadow: 12px 0 35px rgb(3 7 18 / 18%); }
    .sidebar-collapsed { width: 5.25rem; }
    .page-shell { min-height: 100dvh; margin-left: 17rem; }
    .page-collapsed { margin-left: 5.25rem; }
    .brand-mark { color: #111827; background: linear-gradient(145deg, #dff8fc, #56c4d8); box-shadow: 0 10px 22px rgb(0 0 0 / 22%); }
    .nav-link { color: rgb(226 232 240 / 82%); }
    .nav-icon { color: #89d7e5; background: rgb(255 255 255 / 5%); transition: background .2s, color .2s, transform .2s; }
    .nav-link:hover { color: white; background: rgb(255 255 255 / 8%); }
    .nav-link:hover .nav-icon { color: #56c4d8; transform: scale(1.05); }
    .active-link { color: #111827; background: linear-gradient(90deg, #8bd7e5, #56c4d8); box-shadow: 0 10px 24px rgb(3 7 18 / 30%); font-weight: 800; }
    .active-link .nav-icon { color: #111827; background: rgb(255 255 255 / 45%); }
    .header-button { display: grid; width: 2.65rem; height: 2.65rem; place-items: center; border: 1px solid #dce8e5; border-radius: .9rem; color: #526b68; background: rgb(255 255 255 / 82%); transition: .2s; }
    .header-button:hover { border-color: #56c4d8; color: #111827; background: #f0fbfd; }
    .skip-link { position: fixed; left: 1rem; top: -5rem; z-index: 100; border-radius: .75rem; background: #111827; padding: .75rem 1rem; color: white; font-size: .8rem; font-weight: 700; transition: top .2s; }
    .skip-link:focus { top: 1rem; }
     .drawer-backdrop { display: none; }
     @media (max-width: 1023px) { .sidebar, .sidebar-collapsed { position: fixed; inset: 0 auto 0 0; width: 17rem; min-height: 100dvh; transform: translateX(-105%); } .sidebar.drawer-open { transform: translateX(0); } .sidebar-collapsed { width: 17rem; } .page-shell, .page-collapsed { margin-left: 0; padding-top: 4.5rem; } .drawer-backdrop { display: block; } }
    @media (prefers-reduced-motion: reduce) { .sidebar, .page-shell, .nav-icon { transition: none; } }
  `],
})
export class VeterinarianLayoutComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  readonly collapsed = signal(false);
  readonly drawerOpen = signal(false);
  readonly navigation: NavigationGroup[] = [
    { label: 'Área de trabajo', items: [{ label: 'Inicio', route: 'inicio', icon: 'home' }, { label: 'Citas', route: 'agenda', icon: 'calendar' }, { label: 'Pacientes e historial', route: 'mascotas', icon: 'users' }, { label: 'Nueva atención', route: 'nueva-atencion', icon: 'plus' }] },
    { label: 'Pacientes', items: [{ label: 'Hospedaje', route: 'hospedaje', icon: 'bed' }] },
    { label: 'Servicios clínicos', items: [{ label: 'Laboratorio', route: 'laboratorio', icon: 'lab' }, { label: 'Rayos X / Ecografía', route: 'imagenes', icon: 'image' }, { label: 'Vacunas y controles', route: 'vacunacion', icon: 'vaccine' }, { label: 'Cirugía', route: 'cirugia', icon: 'surgery' }, { label: 'Hospitalización', route: 'hospitalizacion', icon: 'bed' }, { label: 'Estética', route: 'estetica', icon: 'sparkle' }] },
    { label: 'Otros servicios', items: [{ label: 'Documentos', route: 'documentos', icon: 'file' }] },
  ];

  closeDrawer(): void { this.drawerOpen.set(false); }
  toggleSidebar(): void {
    if (window.matchMedia('(max-width: 1023px)').matches) this.drawerOpen.update((value) => !value);
    else this.collapsed.update((value) => !value);
  }
  logout(): void { this.auth.logout(); void this.router.navigateByUrl('/login'); }
  @HostListener('document:keydown.escape') closeMenus(): void { this.drawerOpen.set(false); }
}
