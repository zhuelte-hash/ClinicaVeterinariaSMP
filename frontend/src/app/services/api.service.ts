import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { User, UserCreate, UserUpdate } from '../models/user.model';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly baseUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getUsers(skip = 0, limit = 100): Observable<User[]> {
    return this.http.get<User[]>(`${this.baseUrl}/users/`, {
      params: { skip, limit },
    });
  }

  getUser(id: number): Observable<User> {
    return this.http.get<User>(`${this.baseUrl}/users/${id}`);
  }

  createUser(data: UserCreate): Observable<User> {
    return this.http.post<User>(`${this.baseUrl}/users/`, data);
  }

  updateUser(id: number, data: UserUpdate): Observable<User> {
    return this.http.put<User>(`${this.baseUrl}/users/${id}`, data);
  }

  deleteUser(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/users/${id}`);
  }
}
