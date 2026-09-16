import { Component, computed, signal } from '@angular/core';
import { NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavbarComponent } from './components/navbar/navbar.component';
import { FooterComponent } from './components/footer/footer.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, NavbarComponent, FooterComponent],
  template: `
    @if (showPublicChrome()) {
      <app-navbar />
    }
    <main class="min-h-screen" [class.bg-[#fffdf8]]="showPublicChrome()">
      <router-outlet />
    </main>
    @if (showPublicChrome()) {
      <app-footer />
      <a href="https://wa.me/51965939522?text=Hola%20necesito%20m%C3%A1s%20informaci%C3%B3n"
         target="_blank" rel="noopener noreferrer"
         class="fixed bottom-5 right-5 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-[#25D366] text-3xl shadow-xl transition hover:scale-105"
         title="Escríbenos por WhatsApp" aria-label="Escríbenos por WhatsApp">💬</a>
    }
  `,
})
export class AppComponent {
  private readonly currentUrl = signal('');
  readonly showPublicChrome = computed(() => {
    const url = this.currentUrl();
    return !url.startsWith('/admin') && !url.startsWith('/login') && !url.startsWith('/no-autorizado');
  });

  constructor(router: Router) {
    this.currentUrl.set(router.url);
    router.events.pipe(
      filter((event): event is NavigationEnd => event instanceof NavigationEnd),
      takeUntilDestroyed(),
    ).subscribe((event) => this.currentUrl.set(event.urlAfterRedirects));
  }
}
