import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  template: `
    <nav class="bg-white shadow-md border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16 items-center">
          <a routerLink="/" class="flex items-center gap-2 text-xl font-bold text-primary-600">
            <svg class="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            </svg>
            FullStack App
          </a>
          <div class="flex gap-4">
            <a routerLink="/" routerLinkActive="text-primary-600 font-semibold"
               class="px-3 py-2 rounded-md text-sm text-gray-700 hover:text-primary-600 transition-colors">
              Home
            </a>
            <a routerLink="/users" routerLinkActive="text-primary-600 font-semibold"
               class="px-3 py-2 rounded-md text-sm text-gray-700 hover:text-primary-600 transition-colors">
              Users
            </a>
          </div>
        </div>
      </div>
    </nav>
  `,
})
export class NavbarComponent {}
