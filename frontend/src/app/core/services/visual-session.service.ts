import { computed, Injectable, signal } from '@angular/core';

const VISUAL_SESSION_KEY = 'clinic_visual_session_v1';

export interface VisualSessionUser {
  email: string;
  nombre: string;
}

@Injectable({ providedIn: 'root' })
export class VisualSessionService {
  private readonly userState = signal<VisualSessionUser | null>(this.readSession());
  readonly user = this.userState.asReadonly();
  readonly isLoggedIn = computed(() => this.userState() !== null);

  login(email: string, nombre = 'Cliente'): void {
    const user = { email, nombre };
    this.userState.set(user);
    sessionStorage.setItem(VISUAL_SESSION_KEY, JSON.stringify(user));
  }

  logout(): void {
    this.userState.set(null);
    sessionStorage.removeItem(VISUAL_SESSION_KEY);
  }

  private readSession(): VisualSessionUser | null {
    try {
      const stored = sessionStorage.getItem(VISUAL_SESSION_KEY);
      if (!stored) return null;
      const value: unknown = JSON.parse(stored);
      if (
        typeof value !== 'object'
        || value === null
        || !('email' in value)
        || !('nombre' in value)
        || typeof value.email !== 'string'
        || typeof value.nombre !== 'string'
      ) {
        sessionStorage.removeItem(VISUAL_SESSION_KEY);
        return null;
      }
      return value as VisualSessionUser;
    } catch {
      sessionStorage.removeItem(VISUAL_SESSION_KEY);
      return null;
    }
  }
}
