import { Component, computed, inject, signal } from '@angular/core';
import { NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavbarComponent } from './components/navbar/navbar.component';
import { FooterComponent } from './components/footer/footer.component';
import { NoticeComponent } from './shared/notice/notice.component';
import { WhatsappButtonComponent } from './shared/whatsapp-button/whatsapp-button.component';
import { ThemeService } from './core/services/theme.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, NavbarComponent, FooterComponent, NoticeComponent, WhatsappButtonComponent],
  template: `
    @if (showPublicChrome()) {
      <app-navbar />
    }
    <div class="min-h-screen" [class.bg-[#fffdf8]]="showPublicChrome()">
      <router-outlet />
    </div>
    @if (showPanel()) {
      <button class="panel-theme-toggle" type="button" (click)="theme.toggle()" [attr.aria-label]="theme.dark() ? 'Activar modo claro' : 'Activar modo oscuro'" [attr.title]="theme.dark() ? 'Modo claro' : 'Modo oscuro'">
        @if (theme.dark()) { <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.65 17.65l1.42 1.42M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.65 6.35l1.42-1.42"/></svg> } @else { <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12.8A8.5 8.5 0 1 1 11.2 3 6.6 6.6 0 0 0 21 12.8Z"/></svg> }
      </button>
    }
    <app-notice />
    @if (showPublicChrome()) {
      <app-footer />
      <app-whatsapp-button />
    }
  `,
})
export class AppComponent {
  readonly theme = inject(ThemeService);
  private readonly currentUrl = signal('');
  readonly showPublicChrome = computed(() => {
    const url = this.currentUrl();
    return !url.startsWith('/admin') && !url.startsWith('/caja') && !url.startsWith('/veterinario') && !url.startsWith('/login') && !url.startsWith('/registro') && !url.startsWith('/no-autorizado');
  });
  readonly showPanel = computed(() => ['/admin', '/caja', '/veterinario'].some((path) => this.currentUrl().startsWith(path)));

  constructor(router: Router) {
    this.currentUrl.set(router.url);
    router.events.pipe(
      filter((event): event is NavigationEnd => event instanceof NavigationEnd),
      takeUntilDestroyed(),
    ).subscribe((event) => this.currentUrl.set(event.urlAfterRedirects));
  }
}
