import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { toObservable } from '@angular/core/rxjs-interop';
import { filter, map, take } from 'rxjs';
import { AuthService } from '../auth/auth.service';

export const adminGuard: CanActivateFn = (_route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  return toObservable(auth.isLoading).pipe(
    filter((isLoading) => !isLoading),
    take(1),
    map(() => {
      if (!auth.isAuthenticated()) {
        return router.createUrlTree(['/login'], {
          queryParams: { returnUrl: state.url },
        });
      }

      return auth.isAdmin() || router.createUrlTree(['/no-autorizado']);
    }),
  );
};
