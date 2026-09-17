import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [RouterLink],
  template: `
    <footer class="bg-pet-900 text-gray-200 mt-0">
      <div class="max-w-7xl mx-auto px-4 py-12 grid md:grid-cols-4 gap-8">
        <div>
          <div class="flex items-center gap-2 mb-4">
            <img src="/logo.png" alt="logo" class="w-12 h-12 rounded-full object-cover border-2 border-white/20" />
            <span class="text-white font-extrabold text-lg">San Martín de Porres</span>
          </div>
          <p class="text-sm text-gray-300">Clínica veterinaria integral en Ayacucho. Cuidado, amor y salud para tu mejor amigo.</p>
          <div class="flex gap-3 mt-4 text-xl">
            <a href="https://www.facebook.com/vamospetveterinaria" target="_blank" class="hover:text-white">📘</a>
            <a href="https://www.instagram.com/vamospetveterinaria/" target="_blank" class="hover:text-white">📸</a>
            <a href="https://www.tiktok.com/@vamos_pet_veterinaria" target="_blank" class="hover:text-white">🎵</a>
          </div>
        </div>
        <div>
          <h4 class="text-white font-bold mb-3">Links</h4>
          <ul class="space-y-2 text-sm">
            <li><a routerLink="/inicio" class="hover:text-brand-500">Inicio</a></li>
            <li><a routerLink="/inicio" class="hover:text-brand-500">Sobre Nosotros</a></li>
            <li><a routerLink="/servicios" class="hover:text-brand-500">Nuestros Servicios</a></li>
            <li><a routerLink="/servicios" class="hover:text-brand-500">Laboratorio</a></li>
            <li><a routerLink="/productos" class="hover:text-brand-500">Tienda y farmacia</a></li>
            <li><a routerLink="/blog" class="hover:text-brand-500">Nuestro Blog</a></li>
          </ul>
        </div>
        <div>
          <h4 class="text-white font-bold mb-3">Empresa</h4>
          <ul class="space-y-2 text-sm">
            <li><a routerLink="/" class="hover:text-brand-500">Preguntas Frecuentes</a></li>
            <li><a routerLink="/" class="hover:text-brand-500">Políticas de Privacidad</a></li>
            <li><a routerLink="/" class="hover:text-brand-500">Términos y Condiciones</a></li>
            <li><a routerLink="/contacto" class="hover:text-brand-500">Contacto</a></li>
            <li><a routerLink="/" class="hover:text-brand-500">Libro de Reclamaciones</a></li>
          </ul>
        </div>
        <div>
          <h4 class="text-white font-bold mb-3">Contacto</h4>
          <ul class="space-y-2 text-sm">
            <li><b>Celular:</b> 965 939 522</li>
            <li><b>Correo:</b> vamospetshop@gmail.com</li>
            <li><b>Dirección:</b> Jr. Quinua N° 178 - Cercado, Ayacucho</li>
            <li class="pt-2 text-xs text-gray-400">Lun - Sáb: 8am - 8pm<br/>Dom: 9am - 2pm</li>
          </ul>
        </div>
      </div>
      <div class="border-t border-white/10">
        <div class="max-w-7xl mx-auto px-4 py-4 flex flex-col sm:flex-row justify-between text-xs text-gray-400">
          <span>Todos los derechos © 2026 / Clínica Veterinaria San Martín de Porres - Ayacucho</span>
          <span>Hecho con 💚 para las mascotas</span>
        </div>
      </div>
    </footer>
  `,
})
export class FooterComponent {}
