import { HttpInterceptorFn } from '@angular/common/http';
import { AUTH_TOKEN_KEY } from './auth.models';

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);

  if (!token) {
    return next(request);
  }

  return next(
    request.clone({
      setHeaders: { Authorization: `Bearer ${token}` },
    }),
  );
};
