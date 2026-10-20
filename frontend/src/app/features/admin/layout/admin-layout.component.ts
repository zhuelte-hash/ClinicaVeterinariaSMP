import { Component, computed, HostListener, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '../../../core/auth/auth.service';
import { AdminApiService, AdminNotification } from '../services/admin-api.service';

interface NavItem { label: string; path: string; icon: 'grid' | 'box' | 'stock' | 'tag' | 'calendar' | 'sale' | 'bell' | 'users' | 'settings'; }

@Component({
  selector: 'app-admin-layout', standalone: true, imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './admin-layout.component.html', styleUrl: './admin-layout.component.css',
})
export class AdminLayoutComponent {
  readonly collapsed = signal(false);
  readonly drawerOpen = signal(false);
  readonly profileOpen = signal(false);
  readonly notificationOpen = signal(false);
  readonly notifications = signal<AdminNotification[]>([]);
  readonly unread = computed(() => this.notifications().filter((item) => !item.leida).length);
  readonly administratorName = computed(() => this.auth.currentUser()?.nombre || 'Administrador');
  readonly administratorInitials = computed(() => this.administratorName().split(/\s+/).slice(0, 2).map((part) => part.charAt(0)).join('').toUpperCase());
  readonly today = new Intl.DateTimeFormat('es-PE', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date());
  readonly navItems: NavItem[] = [
    { label: 'Dashboard', path: 'dashboard', icon: 'grid' }, { label: 'Productos', path: 'productos', icon: 'box' },
    { label: 'Inventario', path: 'inventario', icon: 'stock' }, { label: 'Categorías', path: 'categorias', icon: 'tag' },
    { label: 'Citas', path: 'citas', icon: 'calendar' }, { label: 'Ventas', path: 'ventas', icon: 'sale' },
    { label: 'Notificaciones', path: 'notificaciones', icon: 'bell' },
    { label: 'Usuarios', path: 'usuarios', icon: 'users' }, { label: 'Clientes', path: 'clientes', icon: 'users' },
    { label: 'Configuración', path: 'configuracion', icon: 'settings' },
  ];

  private readonly api = inject(AdminApiService);
  constructor(readonly auth: AuthService, private readonly router: Router) { this.api.getNotifications().subscribe({ next: (items) => this.notifications.set(items) }); }
  closeDrawer(): void { this.drawerOpen.set(false); }
  toggleProfile(): void { this.profileOpen.update((open) => !open); this.notificationOpen.set(false); }
  toggleNotifications(): void { this.notificationOpen.update((open) => !open); this.profileOpen.set(false); }
  logout(): void {
    this.auth.logout();
    void this.router.navigateByUrl('/login');
  }
  @HostListener('document:keydown.escape') closeMenus(): void { this.drawerOpen.set(false); this.profileOpen.set(false); this.notificationOpen.set(false); }
}
