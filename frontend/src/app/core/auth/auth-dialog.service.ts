import { Dialog } from '@angular/cdk/dialog';
import { inject, Injectable } from '@angular/core';
import { map, Observable, take } from 'rxjs';
import { AuthLoginDialogComponent } from './auth-login-dialog.component';

@Injectable({ providedIn: 'root' })
export class AuthDialogService {
  private readonly dialog = inject(Dialog);

  open(returnUrl?: string): Observable<boolean> {
    const ref = this.dialog.open<boolean>(AuthLoginDialogComponent, {
      data: { returnUrl },
      ariaLabel: 'Iniciar sesión',
      backdropClass: 'services-dialog-backdrop',
      panelClass: 'services-dialog-panel',
      disableClose: false,
    });
    return ref.closed.pipe(
      take(1),
      map((result) => result === true),
    );
  }
}
