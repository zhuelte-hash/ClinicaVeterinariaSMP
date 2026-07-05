import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="max-w-7xl mx-auto px-4 py-12">
      <div class="text-center">
        <h1 class="text-5xl font-extrabold text-gray-900 mb-4">
          FullStack App
        </h1>
        <p class="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
          Aplicación moderna con Angular 21 + Tailwind CSS en el Frontend
          y FastAPI + PostgreSQL en el Backend.
        </p>

        <div class="flex justify-center gap-4 mb-16">
          <a routerLink="/users"
             class="inline-flex items-center px-6 py-3 bg-primary-600 text-white font-medium rounded-lg
                    hover:bg-primary-700 transition-colors shadow-md">
            Ver Usuarios
            <svg class="ml-2 w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </a>
          <a href="http://localhost:8000/docs" target="_blank"
             class="inline-flex items-center px-6 py-3 border-2 border-gray-300 text-gray-700 font-medium
                    rounded-lg hover:border-primary-500 hover:text-primary-600 transition-colors">
            API Docs (Swagger)
          </a>
        </div>

        <div class="grid md:grid-cols-3 gap-8 text-left">
          <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
            <div class="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
              <svg class="w-6 h-6 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <h3 class="text-lg font-semibold text-gray-900 mb-2">Frontend</h3>
            <p class="text-gray-600 text-sm">
              Angular 21 con componentes standalone, routing lazy-loaded y Tailwind CSS
              para diseño responsivo moderno.
            </p>
          </div>

          <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
            <div class="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
              <svg class="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
              </svg>
            </div>
            <h3 class="text-lg font-semibold text-gray-900 mb-2">Backend API</h3>
            <p class="text-gray-600 text-sm">
              FastAPI asíncrono con validación Pydantic, documentación Swagger/OpenAPI
              y SQLAlchemy como ORM.
            </p>
          </div>

          <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
            <div class="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
              <svg class="w-6 h-6 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
              </svg>
            </div>
            <h3 class="text-lg font-semibold text-gray-900 mb-2">Base de Datos</h3>
            <p class="text-gray-600 text-sm">
              PostgreSQL con modelo relacional, migraciones Alembic y gestión
              mediante DBeaver.
            </p>
          </div>
        </div>
      </div>
    </div>
  `,
})
export class HomeComponent {}
