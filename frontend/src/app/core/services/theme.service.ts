import { DOCUMENT, isPlatformBrowser } from '@angular/common';
import { Injectable, inject, signal } from '@angular/core';
import { PLATFORM_ID } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs';

type Theme = 'light' | 'dark';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly document = inject(DOCUMENT);
  private readonly platformId = inject(PLATFORM_ID);
  private readonly router = inject(Router);
  readonly dark = signal<boolean>(this.readTheme() === 'dark');

  constructor() {
    const url = isPlatformBrowser(this.platformId) ? this.document.location.pathname : this.router.url;
    this.apply(this.dark(), url);
    this.router.events.pipe(
      filter((event): event is NavigationEnd => event instanceof NavigationEnd),
      takeUntilDestroyed(),
    ).subscribe((event) => this.apply(this.dark(), event.urlAfterRedirects));
  }

  toggle(): void {
    const next = !this.dark();
    this.dark.set(next);
    this.apply(next, this.router.url);
    if (!isPlatformBrowser(this.platformId)) return;
    try {
      window.localStorage.setItem('clinic-theme', next ? 'dark' : 'light');
    } catch {
      // The theme still works when the browser blocks persistent storage.
    }
  }

  private readTheme(): Theme {
    if (!isPlatformBrowser(this.platformId)) return 'light';
    try {
      return window.localStorage.getItem('clinic-theme') === 'dark' ? 'dark' : 'light';
    } catch {
      return 'light';
    }
  }

  private apply(isDark: boolean, url: string): void {
    const isPanel = /^\/(admin|caja|veterinario)([/?#]|$)/.test(url);
    this.document.documentElement.dataset['theme'] = isDark && isPanel ? 'dark' : 'light';
  }
}
