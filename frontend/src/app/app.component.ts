import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { NavbarComponent } from './components/navbar/navbar.component';
import { FooterComponent } from './components/footer/footer.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, NavbarComponent, FooterComponent],
  template: `
    <app-navbar />
    <main class="min-h-screen bg-[#fffdf8]">
      <router-outlet />
    </main>
    <app-footer />
    <a href="https://wa.me/51965939522?text=Hola%20necesito%20m%C3%A1s%20informaci%C3%B3n"
       target="_blank"
       class="fixed bottom-5 right-5 z-50 w-14 h-14 bg-[#25D366] rounded-full flex items-center justify-center text-3xl shadow-xl hover:scale-105 transition"
       title="¡Hola! dejanos un mensaje para ayudarte...">💬</a>
  `,
})
export class AppComponent {}
