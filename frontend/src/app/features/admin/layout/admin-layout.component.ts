import { Component, computed, HostListener, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '../../../core/auth/auth.service';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AdminApiService, AdminUserNotification } from '../services/admin-api.service';
import { ThemeToggleComponent } from '../../../shared/theme-toggle/theme-toggle.component';
import { routeModule } from '../../../core/guards/permission.guard';

interface NavItem { label: string; path: string; icon: 'grid' | 'box' | 'stock' | 'tag' | 'calendar' | 'sale' | 'bell' | 'users' | 'settings'; }

@Component({
  selector: 'app-admin-layout', standalone: true, imports: [RouterOutlet, RouterLink, RouterLinkActive, ThemeToggleComponent],
  templateUrl: './admin-layout.component.html', styleUrl: './admin-layout.component.css',
})
export class AdminLayoutComponent {
  readonly collapsed = signal(false);
  readonly drawerOpen = signal(false);
  readonly profileOpen = signal(false);
  readonly notificationOpen = signal(false);
  readonly notifications = signal<AdminUserNotification[]>([]);
  readonly unread = computed(() => this.notifications().filter((item) => !item.leida).length);
  readonly administratorName = computed(() => this.auth.currentUser()?.nombre || 'Administrador');
  readonly administratorInitials = computed(() => this.administratorName().split(/\s+/).slice(0, 2).map((part) => part.charAt(0)).join('').toUpperCase());
  readonly today = new Intl.DateTimeFormat('es-PE', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date());
  private readonly allNavItems: NavItem[] = [
    { label: 'Reportes Excel', path: 'reportes', icon: 'sale' },
    { label: 'Órdenes y pagos', path: 'ordenes', icon: 'sale' },
    { label: 'Pedidos web', path: 'pedidos-web', icon: 'sale' },
    { label: 'Dashboard', path: 'dashboard', icon: 'grid' }, { label: 'Productos', path: 'productos', icon: 'box' },
    { label: 'Inventario', path: 'inventario', icon: 'stock' }, { label: 'Categorías', path: 'categorias', icon: 'tag' },
    { label: 'Proveedores', path: 'proveedores', icon: 'box' },
    { label: 'Citas', path: 'citas', icon: 'calendar' }, { label: 'Ventas', path: 'ventas', icon: 'sale' },
    { label: 'Notificaciones', path: 'notificaciones', icon: 'bell' },
    { label: 'Usuarios', path: 'usuarios', icon: 'users' }, { label: 'Clientes', path: 'clientes', icon: 'users' },
    { label: 'Historial clínico', path: 'historial-clinico', icon: 'stock' },
    { label: 'Configuración', path: 'configuracion', icon: 'settings' },
  ];
  readonly navItems = computed(() => this.allNavItems.filter(item => { if (item.path === 'reportes') return ['ventas', 'citas', 'inventario'].some(module => this.auth.can(module)); const module = routeModule(`/admin/${item.path}`); return !module || this.auth.can(module); }));

  private readonly api = inject(AdminApiService);
  constructor(readonly auth: AuthService, private readonly router: Router) {
    this.refreshNotifications();
    this.api.notificationChanges.pipe(takeUntilDestroyed()).subscribe(() => this.refreshNotifications());
  }
  private refreshNotifications(): void { this.api.getAdminNotifications().subscribe({ next: (items) => this.notifications.set(items) }); }
  closeDrawer(): void { this.drawerOpen.set(false); }
  toggleProfile(): void { this.profileOpen.update((open) => !open); this.notificationOpen.set(false); }
  toggleNotifications(): void { this.notificationOpen.update((open) => !open); this.profileOpen.set(false); if (this.notificationOpen()) this.refreshNotifications(); }
  logout(): void {
    this.auth.logout();
    void this.router.navigateByUrl('/login');
  }
  @HostListener('document:keydown.escape') closeMenus(): void { this.drawerOpen.set(false); this.profileOpen.set(false); this.notificationOpen.set(false); }
}
