import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class VisualSessionService {
  readonly isLoggedIn = signal(false);

  login(): void {
    this.isLoggedIn.set(true);
  }

  logout(): void {
    this.isLoggedIn.set(false);
  }
}
