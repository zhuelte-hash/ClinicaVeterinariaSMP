import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';

export const BRANCH_KEY = 'clinic_branch_id';
export interface Branch { id: number; nombre: string; direccion: string; telefono: string; activa: boolean; }
@Injectable({ providedIn: 'root' })
export class BranchService {
  private readonly http = inject(HttpClient);
  available() { return this.http.get<Branch[]>(`${environment.apiUrl}/publico/sucursales`); }
  all() { return this.http.get<Branch[]>(`${environment.apiUrl}/admin/operaciones/sucursales`); }
  save(data: Omit<Branch, 'id'>, id?: number) {
    const url = `${environment.apiUrl}/admin/operaciones/sucursales`;
    return id ? this.http.put<Branch>(`${url}/${id}`, data) : this.http.post<Branch>(url, data);
  }
  selected(fallback = 1): number { return Number(localStorage.getItem(BRANCH_KEY)) || fallback; }
  select(id: number): void { localStorage.setItem(BRANCH_KEY, String(id)); location.reload(); }
}
