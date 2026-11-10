import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface UserNotification {
  id: number;
  cita_id: number | null;
  tipo: string;
  titulo: string;
  mensaje: string;
  leida: boolean;
  fecha_creacion: string;
}

@Injectable({ providedIn: 'root' })
export class UserNotificationsService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/portal/notificaciones`;

  getNotifications(): Observable<UserNotification[]> {
    return this.http.get<UserNotification[]>(this.baseUrl);
  }

  markAsRead(id: number): Observable<UserNotification> {
    return this.http.patch<UserNotification>(`${this.baseUrl}/${id}/leer`, {});
  }
}
