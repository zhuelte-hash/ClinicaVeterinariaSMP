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

export interface UpdateAdminUser {
  nombre?: string;
  correo?: string;
  contrasena?: string;
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

  getUser(id: number): Observable<AdminUser> {
    return this.http.get<AdminUser>(`${this.baseUrl}/${id}`);
  }

  createUser(data: CreateAdminUser): Observable<AdminUser> {
    return this.http.post<AdminUser>(this.baseUrl, data);
  }

  updateUser(id: number, data: UpdateAdminUser): Observable<AdminUser> {
    return this.http.patch<AdminUser>(`${this.baseUrl}/${id}`, data);
  }

  deleteUser(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${id}`);
  }
}
