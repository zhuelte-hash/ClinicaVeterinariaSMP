import { Component, computed, HostListener, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '../../../core/auth/auth.service';
import { AdminDataService } from '../services/admin-data.service';

interface NavItem { label: string; path: string; icon: 'grid' | 'box' | 'stock' | 'tag' | 'calendar' | 'sale' | 'record' | 'bell' | 'users' | 'settings'; }

@Component({
  selector: 'app-admin-layout', standalone: true, imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './admin-layout.component.html', styleUrl: './admin-layout.component.css',
})
export class AdminLayoutComponent {
  readonly collapsed = signal(false);
  readonly drawerOpen = signal(false);
  readonly profileOpen = signal(false);
  readonly notificationOpen = signal(false);
  readonly searchOpen = signal(false);
  readonly unread = computed(() => this.data.notifications().filter((item) => !item.read).length);
  readonly administratorName = computed(() => this.auth.currentUser()?.full_name || this.auth.currentUser()?.username || 'Administrador');
  readonly administratorInitials = computed(() => this.administratorName().split(/\s+/).slice(0, 2).map((part) => part.charAt(0)).join('').toUpperCase());
  readonly navItems: NavItem[] = [
    { label: 'Dashboard', path: 'dashboard', icon: 'grid' }, { label: 'Productos', path: 'productos', icon: 'box' },
    { label: 'Inventario', path: 'inventario', icon: 'stock' }, { label: 'Categorias', path: 'categorias', icon: 'tag' },
    { label: 'Citas', path: 'citas', icon: 'calendar' }, { label: 'Ventas', path: 'ventas', icon: 'sale' },
    { label: 'Historial clinico', path: 'historial-clinico', icon: 'record' }, { label: 'Notificaciones', path: 'notificaciones', icon: 'bell' },
    { label: 'Usuarios', path: 'usuarios', icon: 'users' }, { label: 'Configuracion', path: 'configuracion', icon: 'settings' },
  ];

  constructor(readonly auth: AuthService, private readonly router: Router, readonly data: AdminDataService) {}
  closeDrawer(): void { this.drawerOpen.set(false); }
  toggleProfile(): void { this.profileOpen.update((open) => !open); this.notificationOpen.set(false); }
  toggleNotifications(): void { this.notificationOpen.update((open) => !open); this.profileOpen.set(false); }
  logout(): void {
    this.auth.logout();
    void this.router.navigateByUrl('/login');
  }
  @HostListener('document:keydown.escape') closeMenus(): void { this.drawerOpen.set(false); this.profileOpen.set(false); this.notificationOpen.set(false); this.searchOpen.set(false); }
}
