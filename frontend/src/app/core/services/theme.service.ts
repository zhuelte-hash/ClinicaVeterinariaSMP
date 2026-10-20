import { DOCUMENT, isPlatformBrowser } from '@angular/common';
import { Injectable, inject, signal } from '@angular/core';
import { PLATFORM_ID } from '@angular/core';

type Theme = 'light' | 'dark';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly document = inject(DOCUMENT);
  private readonly platformId = inject(PLATFORM_ID);
  readonly dark = signal<boolean>(this.readTheme() === 'dark');

  constructor() {
    this.apply(this.dark());
  }

  toggle(): void {
    this.dark.update((isDark) => {
      const next = !isDark;
      this.apply(next);
      return next;
    });
  }

  private readTheme(): Theme {
    if (!isPlatformBrowser(this.platformId)) return 'light';
    return window.localStorage.getItem('clinic-theme') === 'dark' ? 'dark' : 'light';
  }

  private apply(isDark: boolean): void {
    const theme = isDark ? 'dark' : 'light';
    this.document.documentElement.dataset['theme'] = theme;
    if (isPlatformBrowser(this.platformId)) window.localStorage.setItem('clinic-theme', theme);
  }
}
