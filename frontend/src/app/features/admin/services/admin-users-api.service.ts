import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';

export type BackendRole = 'cliente' | 'veterinario' | 'cajero' | 'administrador';

export interface AdminUser {
  id: number;
  nombre: string;
  correo: string;
  tipo: BackendRole;
  telefono: string | null;
  colegiatura: string | null;
  especialidad: string | null;
}

export interface CreateAdminUser {
  nombre: string;
  correo: string;
  contrasena: string;
  tipo: BackendRole;
  telefono?: string;
  colegiatura?: string;
  especialidad?: string;
}

@Injectable({ providedIn: 'root' })
export class AdminUsersApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/usuarios`;

  getUsers(): Observable<AdminUser[]> {
    return this.http.get<AdminUser[]>(this.baseUrl);
  }

  createUser(data: CreateAdminUser): Observable<AdminUser> {
    return this.http.post<AdminUser>(this.baseUrl, data);
  }
}
