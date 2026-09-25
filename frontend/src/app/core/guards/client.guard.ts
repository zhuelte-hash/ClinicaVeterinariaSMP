import { inject } from '@angular/core';
import { toObservable } from '@angular/core/rxjs-interop';
import { CanActivateFn, Router } from '@angular/router';
import { filter, map, of, switchMap, take } from 'rxjs';
import { AuthDialogService } from '../auth/auth-dialog.service';
import { AuthService } from '../auth/auth.service';

export const clientGuard: CanActivateFn = (_route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const authDialog = inject(AuthDialogService);

  return toObservable(auth.isLoading).pipe(
    filter((isLoading) => !isLoading),
    take(1),
    switchMap(() => auth.isAuthenticated() ? of(true) : authDialog.open(state.url)),
    map((authenticated) => {
      if (!authenticated) return false;
      return auth.currentUser()?.tipo === 'cliente'
        || router.createUrlTree(['/no-autorizado']);
    }),
  );
};
