import { Component, computed, signal } from '@angular/core';
import { AdminDataService } from '../../services/admin-data.service';
import { PageHeaderComponent } from '../../shared/page-header.component';

@Component({ selector: 'app-admin-notificaciones', standalone: true, imports: [PageHeaderComponent], templateUrl: './notificaciones.component.html', styleUrl: '../../shared/admin-ui.css' })
export class NotificacionesComponent { readonly showUnread = signal(false); readonly items = computed(() => this.data.notifications().filter((item) => !this.showUnread() || !item.read)); constructor(readonly data: AdminDataService) {} }
