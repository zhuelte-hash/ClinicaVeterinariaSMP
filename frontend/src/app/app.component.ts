import { Component, computed, signal } from '@angular/core';
import { NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavbarComponent } from './components/navbar/navbar.component';
import { FooterComponent } from './components/footer/footer.component';
import { NoticeComponent } from './shared/notice/notice.component';
import { WhatsappButtonComponent } from './shared/whatsapp-button/whatsapp-button.component';

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
    <app-notice />
    @if (showPublicChrome()) {
      <app-footer />
      <app-whatsapp-button />
    }
  `,
})
export class AppComponent {
  private readonly currentUrl = signal('');
  readonly showPublicChrome = computed(() => {
    const url = this.currentUrl();
    return !url.startsWith('/admin') && !url.startsWith('/caja') && !url.startsWith('/veterinario') && !url.startsWith('/login') && !url.startsWith('/registro') && !url.startsWith('/no-autorizado');
  });

  constructor(router: Router) {
    this.currentUrl.set(router.url);
    router.events.pipe(
      filter((event): event is NavigationEnd => event instanceof NavigationEnd),
      takeUntilDestroyed(),
    ).subscribe((event) => this.currentUrl.set(event.urlAfterRedirects));
  }
}
