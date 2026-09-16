import { HttpClient } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { catchError, finalize, Observable, tap, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  AUTH_TOKEN_KEY,
  AuthUser,
  LoginCredentials,
  LoginResponse,
} from './auth.models';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly userState = signal<AuthUser | null>(null);
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
    if (!user) {
      return false;
    }

    const role = (user.role ?? user.rol)?.trim().toUpperCase();
    return (
      user.is_superuser === true ||
      user.es_admin === true ||
      role === 'ADMIN' ||
      role === 'ADMINISTRADOR'
    );
  });
  readonly isLoading = computed(() => this.loadingState());

  constructor() {
    if (this.tokenState()) {
      this.restoreCurrentUser();
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

  logout(): void {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    this.tokenState.set(null);
    this.userState.set(null);
    this.loadingState.set(false);
  }

  getAccessToken(): string | null {
    return this.tokenState();
  }

  getCurrentUser(): Observable<AuthUser> {
    return this.http.get<AuthUser>(`${environment.apiUrl}/auth/me`).pipe(
      tap((user) => this.userState.set(user)),
    );
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
