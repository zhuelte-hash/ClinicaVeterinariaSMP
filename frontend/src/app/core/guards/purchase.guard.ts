import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { VisualSessionService } from '../services/visual-session.service';

export const purchaseGuard: CanActivateFn = (_route, state) => {
  const session = inject(VisualSessionService);
  const router = inject(Router);

  return session.isLoggedIn() || router.createUrlTree(['/login'], {
    queryParams: { returnUrl: state.url },
  });
};
