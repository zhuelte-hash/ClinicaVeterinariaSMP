import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { finalize } from 'rxjs';
import { NoticeService } from '../../../../core/services/notice.service';
import { AdminApiService, AdminUserNotification } from '../../services/admin-api.service';
import { PageHeaderComponent } from '../../shared/page-header.component';

@Component({ selector: 'app-admin-notificaciones', standalone: true, imports: [PageHeaderComponent, DatePipe], templateUrl: './notificaciones.component.html', styleUrl: '../../shared/admin-ui.css' })
export class NotificacionesComponent {
  private readonly api = inject(AdminApiService); private readonly notice = inject(NoticeService);
  readonly showUnread = signal(false); readonly all = signal<AdminUserNotification[]>([]); readonly loading = signal(true); readonly error = signal(''); readonly items = computed(() => this.all().filter((item) => !this.showUnread() || !item.leida));
  readonly saving = signal(false);
  readonly unread = computed(() => this.all().filter(item => !item.leida).length);
  constructor() { this.load(); }
  load(): void { this.loading.set(true); this.api.getAdminNotifications().pipe(finalize(() => this.loading.set(false))).subscribe({ next: (items) => { this.all.set(items); this.error.set(''); }, error: (error: unknown) => this.error.set(this.errorText(error)) }); }
  markAll(): void { if (this.saving() || !this.unread()) return; this.saving.set(true); this.api.markAllNotifications().pipe(finalize(() => this.saving.set(false))).subscribe({ next: () => { this.all.update((items) => items.map((item) => ({ ...item, leida: true }))); this.error.set(''); this.notice.show('Notificaciones marcadas como leídas'); }, error: (error: unknown) => this.error.set(this.errorText(error)) }); }
  markRead(item: AdminUserNotification): void { if (item.leida || this.saving()) return; this.saving.set(true); this.api.markNotificationRead(item.id).pipe(finalize(() => this.saving.set(false))).subscribe({ next: () => { this.all.update(items => items.map(current => current.id === item.id ? { ...current, leida: true } : current)); this.error.set(''); }, error: (error: unknown) => this.error.set(this.errorText(error)) }); }
  private errorText(error: unknown): string { return error instanceof HttpErrorResponse && typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudieron cargar las notificaciones.'; }
}
