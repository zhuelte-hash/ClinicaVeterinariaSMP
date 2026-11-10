import { ChangeDetectionStrategy, Component, computed, DestroyRef, ElementRef, HostListener, inject, input, output, signal, viewChild } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink } from '@angular/router';
import { filter, finalize } from 'rxjs';
import { AuthService } from '../../core/auth/auth.service';
import { UserNotification, UserNotificationsService } from '../../core/services/user-notifications.service';
import { ThemeToggleComponent } from '../theme-toggle/theme-toggle.component';

type PanelRole = 'veterinario' | 'cajero';

const PANELS = {
  veterinario: {
    title: 'Panel veterinario',
    roleName: 'Veterinario',
    session: 'Sesión veterinaria',
    notifications: 'Avisos de tus citas y atenciones clínicas',
    home: '/veterinario/agenda',
    homeLabel: 'Ir a mi agenda',
    links: [
      { label: 'Mi agenda', path: '/veterinario/agenda' },
      { label: 'Pacientes e historial', path: '/veterinario/mascotas' },
    ],
  },
  cajero: {
    title: 'Panel del cajero',
    roleName: 'Cajero',
    session: 'Sesión de caja',
    notifications: 'Avisos dirigidos a tu usuario de caja',
    home: '/caja/dashboard',
    homeLabel: 'Ir al resumen de caja',
    links: [
      { label: 'Resumen de caja', path: '/caja/dashboard' },
      { label: 'Punto de venta', path: '/caja/ventas' },
      { label: 'Pedidos web', path: '/caja/pedidos-web' },
    ],
  },
};

@Component({
  selector: 'app-panel-header',
  standalone: true,
  imports: [RouterLink, ThemeToggleComponent],
  templateUrl: './panel-header.component.html',
  styleUrl: './panel-header.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PanelHeaderComponent {
  private readonly auth = inject(AuthService);
  private readonly api = inject(UserNotificationsService);
  private readonly router = inject(Router);
  private readonly element = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly destroyRef = inject(DestroyRef);
  private readonly notificationButton = viewChild<ElementRef<HTMLButtonElement>>('notificationButton');
  private readonly profileButton = viewChild<ElementRef<HTMLButtonElement>>('profileButton');
  private readonly mobile = signal(window.matchMedia('(max-width: 1023px)').matches);

  readonly role = input.required<PanelRole>();
  readonly navigationId = input.required<string>();
  readonly collapsed = input(false);
  readonly drawerOpen = input(false);
  readonly menuToggled = output<void>();
  readonly logoutRequested = output<void>();
  readonly panel = computed(() => PANELS[this.role()]);
  readonly userName = computed(() => this.auth.currentUser()?.nombre || this.panel().roleName);
  readonly userEmail = computed(() => this.auth.currentUser()?.correo || '');
  readonly userInitials = computed(() => this.userName().trim().split(/\s+/).slice(0, 2).map(part => part.charAt(0)).join('').toUpperCase());
  readonly navigationExpanded = computed(() => this.mobile() ? this.drawerOpen() : !this.collapsed());
  readonly menuLabel = computed(() => `${this.navigationExpanded() ? 'Contraer' : 'Abrir'} menú de ${this.panel().roleName.toLowerCase()}`);
  readonly profileOpen = signal(false);
  readonly notificationOpen = signal(false);
  readonly notifications = signal<UserNotification[]>([]);
  readonly notificationsLoading = signal(false);
  readonly notificationError = signal('');
  readonly markingRead = signal<number | null>(null);
  readonly unread = computed(() => this.notifications().filter(item => !item.leida).length);
  readonly notificationsId = computed(() => `${this.role()}-notifications`);
  readonly profileId = computed(() => `${this.role()}-profile`);
  readonly today = new Intl.DateTimeFormat('es-PE', { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'America/Lima' }).format(new Date());

  constructor() {
    this.refreshNotifications();
    this.router.events.pipe(filter(event => event instanceof NavigationEnd), takeUntilDestroyed()).subscribe(() => this.closeDropdowns());
  }

  toggleNavigation(): void {
    this.closeDropdowns();
    this.menuToggled.emit();
  }

  toggleProfile(): void {
    this.profileOpen.update(open => !open);
    this.notificationOpen.set(false);
  }

  toggleNotifications(): void {
    this.notificationOpen.update(open => !open);
    this.profileOpen.set(false);
    if (this.notificationOpen()) this.refreshNotifications();
  }

  refreshNotifications(): void {
    if (this.notificationsLoading()) return;
    this.notificationsLoading.set(true);
    this.notificationError.set('');
    this.api.getNotifications().pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.notificationsLoading.set(false))).subscribe({
      next: items => this.notifications.set(items),
      error: () => this.notificationError.set('No se pudieron cargar tus notificaciones.'),
    });
  }

  markAsRead(notification: UserNotification): void {
    if (notification.leida || this.markingRead() !== null) return;
    this.markingRead.set(notification.id);
    this.notificationError.set('');
    this.api.markAsRead(notification.id).pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.markingRead.set(null))).subscribe({
      next: updated => this.notifications.update(items => items.map(item => item.id === updated.id ? updated : item)),
      error: () => this.notificationError.set('No se pudo marcar el aviso como leído. Intenta nuevamente.'),
    });
  }

  notificationDate(value: string): string {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? '' : new Intl.DateTimeFormat('es-PE', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Lima' }).format(date);
  }

  closeDropdowns(): void {
    this.profileOpen.set(false);
    this.notificationOpen.set(false);
  }

  logout(): void {
    this.closeDropdowns();
    this.logoutRequested.emit();
  }

  @HostListener('window:resize') onResize(): void {
    this.mobile.set(window.matchMedia('(max-width: 1023px)').matches);
  }

  @HostListener('document:click', ['$event']) onOutsideClick(event: Event): void {
    if (event.target instanceof Node && !this.element.nativeElement.contains(event.target)) this.closeDropdowns();
  }

  @HostListener('document:keydown.escape') onEscape(): void {
    if (this.notificationOpen()) this.notificationButton()?.nativeElement.focus();
    else if (this.profileOpen()) this.profileButton()?.nativeElement.focus();
    this.closeDropdowns();
  }
}
