import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { AUTH_TOKEN_KEY } from './auth.models';
import { AuthService } from './auth.service';
import { BRANCH_KEY } from '../services/branch.service';
import { environment } from '../../../environments/environment';

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  const auth = inject(AuthService);
  const branch = localStorage.getItem(BRANCH_KEY);
  if (branch && /^[1-9]\d*$/.test(branch) && request.url.startsWith(environment.apiUrl + '/') && !request.url.startsWith(environment.apiUrl + '/auth/')) {
    request = request.clone({ setHeaders: { 'X-Sucursal-ID': branch } });
  }

  if (!token) {
    return next(request);
  }

  return next(
    request.clone({
      setHeaders: { Authorization: `Bearer ${token}` },
    }),
  ).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse && error.status === 401 && !request.url.endsWith('/auth/login')) {
        auth.logout();
      }
      return throwError(() => error);
    }),
  );
};
