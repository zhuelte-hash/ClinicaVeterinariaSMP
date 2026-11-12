import { HttpClient } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { catchError, finalize, Observable, tap, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  AUTH_TOKEN_KEY,
  AuthUser,
  ClientRegistration,
  LoginCredentials,
  LoginResponse,
} from './auth.models';

export interface UserPermission {
  modulo: string;
  puede_ver: boolean;
  puede_crear: boolean;
  puede_editar: boolean;
  puede_eliminar: boolean;
  puede_aprobar: boolean;
}
export type PermissionAction = 'ver' | 'crear' | 'editar' | 'eliminar' | 'aprobar';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly userState = signal<AuthUser | null>(null);
  private readonly permissionState = signal<UserPermission[]>([]);
  private readonly tokenState = signal<string | null>(
    localStorage.getItem(AUTH_TOKEN_KEY),
  );
  private readonly loadingState = signal(this.tokenState() !== null);

  readonly currentUser = computed(() => this.userState());
  readonly isAuthenticated = computed(
    () => this.tokenState() !== null && this.userState() !== null,
  );
  readonly isAdmin = computed(() => {
    const user = this.userState();
    return user?.tipo === 'administrador';
  });
  readonly isCashier = computed(() => this.userState()?.tipo === 'cajero');
  readonly isVeterinarian = computed(() => this.userState()?.tipo === 'veterinario');
  readonly isLoading = computed(() => this.loadingState());

  constructor() {
    if (this.tokenState()) {
      // El interceptor también inyecta AuthService; espera a que termine su creación.
      queueMicrotask(() => this.restoreCurrentUser());
    }
  }

  login(credentials: LoginCredentials): Observable<LoginResponse> {
    this.loadingState.set(true);

    return this.http
      .post<LoginResponse>(`${environment.apiUrl}/auth/login`, credentials)
      .pipe(
        tap(({ access_token, user }) => {
          localStorage.setItem(AUTH_TOKEN_KEY, access_token);
          this.tokenState.set(access_token);
          this.userState.set(user);
        }),
        finalize(() => this.loadingState.set(false)),
      );
  }

  register(data: ClientRegistration): Observable<LoginResponse> {
    this.loadingState.set(true);

    return this.http
      .post<LoginResponse>(`${environment.apiUrl}/auth/register`, data)
      .pipe(
        tap(({ access_token, user }) => {
          if (!access_token) return;
          localStorage.setItem(AUTH_TOKEN_KEY, access_token);
          this.tokenState.set(access_token);
          this.userState.set(user);
        }),
        finalize(() => this.loadingState.set(false)),
      );
  }

  logout(): void {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    this.tokenState.set(null);
    this.userState.set(null);
    this.permissionState.set([]);
    this.loadingState.set(false);
  }

  acceptSession(response: LoginResponse): void {
    if (!response.access_token) return;
    localStorage.setItem(AUTH_TOKEN_KEY, response.access_token);
    this.tokenState.set(response.access_token);
    this.userState.set(response.user);
  }

  getAccessToken(): string | null {
    return this.tokenState();
  }

  getCurrentUser(): Observable<AuthUser> {
    return this.http.get<AuthUser>(`${environment.apiUrl}/auth/me`).pipe(
      tap((user) => this.userState.set(user)),
    );
  }

  refreshPermissions(): Observable<UserPermission[]> {
    return this.http.get<UserPermission[]>(`${environment.apiUrl}/auth/me/permisos`).pipe(
      tap(items => this.permissionState.set(items)),
    );
  }

  can(module: string, action: PermissionAction = 'ver'): boolean {
    const item = this.permissionState().find(permission => permission.modulo === module);
    return !!item?.puede_ver && !!item[`puede_${action}`];
  }

  private restoreCurrentUser(): void {
    this.getCurrentUser()
      .pipe(
        catchError((error: unknown) => {
          this.logout();
          return throwError(() => error);
        }),
        finalize(() => this.loadingState.set(false)),
      )
      .subscribe({ error: () => undefined });
  }
}
