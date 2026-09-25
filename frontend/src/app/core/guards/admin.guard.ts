import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { toObservable } from '@angular/core/rxjs-interop';
import { filter, map, of, switchMap, take } from 'rxjs';
import { AuthDialogService } from '../auth/auth-dialog.service';
import { AuthService } from '../auth/auth.service';

export const adminGuard: CanActivateFn = (_route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const authDialog = inject(AuthDialogService);

  return toObservable(auth.isLoading).pipe(
    filter((isLoading) => !isLoading),
    take(1),
    switchMap(() => auth.isAuthenticated() ? of(true) : authDialog.open(state.url)),
    map((authenticated) => {
      if (!authenticated) return false;
      return auth.isAdmin() || router.createUrlTree(['/no-autorizado']);
    }),
  );
};
