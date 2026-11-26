import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ClinicContactService } from '../../core/services/clinic-contact.service';

@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [RouterLink],
  template: `
     <footer class="mt-0 border-t-4 border-brand-500 bg-pet-900 text-slate-200">
       <div class="mx-auto grid max-w-7xl gap-9 px-4 py-12 sm:grid-cols-2 sm:px-6 lg:grid-cols-4 lg:px-8">
        <div>
          <div class="flex items-center gap-2 mb-4">
             <img src="/logo.png" alt="" class="h-12 w-12 rounded-full border border-white/20 object-contain" />
            <span class="text-white font-extrabold text-lg">San Martín de Porres</span>
          </div>
            <p class="text-sm leading-6 text-slate-200">Clínica veterinaria integral en Ayacucho. Cuidado, amor y salud para tu mejor amigo.</p>
            <section class="mt-5 overflow-hidden rounded-2xl border border-white/20 bg-white/5" aria-labelledby="footer-location-title">
              <h2 id="footer-location-title" class="px-4 py-3 text-sm font-bold text-white">Nuestra ubicación</h2>
              <iframe title="Ubicación de la Clínica Veterinaria San Martín de Porres en Google Maps"
                src="https://www.google.com/maps?q=Jr+Quinua+178+Cercado+Ayacucho&output=embed"
                class="block h-48 w-full border-0 bg-slate-100" loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe>
              <a href="https://www.google.com/maps/search/?api=1&query=Jr+Quinua+178+Cercado+Ayacucho" target="_blank" rel="noopener noreferrer" class="block px-4 py-3 text-xs font-semibold text-brand-200 hover:text-white">Jr. Quinua N° 178, Ayacucho · Cómo llegar →</a>
            </section>
           <div class="mt-4 flex gap-2 text-lg">
             <a href="https://www.facebook.com/vamospetveterinaria" target="_blank" rel="noopener noreferrer" aria-label="Facebook de la clínica" class="grid h-11 w-11 place-items-center rounded-full border border-white/20 transition hover:border-brand-300 hover:text-white">📘</a>
             <a href="https://www.instagram.com/vamospetveterinaria/" target="_blank" rel="noopener noreferrer" aria-label="Instagram de la clínica" class="grid h-11 w-11 place-items-center rounded-full border border-white/20 transition hover:border-brand-300 hover:text-white">📸</a>
             <a href="https://www.tiktok.com/@vamos_pet_veterinaria" target="_blank" rel="noopener noreferrer" aria-label="TikTok de la clínica" class="grid h-11 w-11 place-items-center rounded-full border border-white/20 transition hover:border-brand-300 hover:text-white">🎵</a>
          </div>
        </div>
        <div>
             <h2 class="mb-3 font-bold text-brand-200">Enlaces</h2>
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
             <h2 class="mb-3 font-bold text-brand-200">Empresa</h2>
           <ul class="space-y-2 text-sm">
             <li><a routerLink="/contacto" class="hover:text-brand-500">Preguntas frecuentes</a></li>
             <li><a routerLink="/contacto" class="hover:text-brand-500">Políticas y condiciones</a></li>
             <li><a routerLink="/contacto" class="hover:text-brand-500">Contacto y reclamos</a></li>
           </ul>
         </div>
        <div>
           <h2 class="mb-3 font-bold text-brand-200">Contacto</h2>
          <ul class="space-y-2 text-sm">
            <li><b>Celular:</b> <a [href]="contact.telUrl()" class="hover:text-brand-300">{{ contact.displayPhone() }}</a></li>
           <li><b>Correo:</b> <a href="mailto:vamospetshop@gmail.com" class="break-all hover:text-brand-300">vamospetshop@gmail.com</a></li>
            <li><b>Dirección:</b> Jr. Quinua N° 178 - Cercado, Ayacucho</li>
            <li class="pt-2 text-xs text-gray-400">Lun - Sáb: 8am - 8pm<br/>Dom: 9am - 2pm</li>
          </ul>
        </div>
      </div>
      <div class="border-t border-white/10">
         <div class="mx-auto flex max-w-7xl flex-col justify-between gap-2 px-4 py-4 text-xs text-slate-300 sm:flex-row sm:px-6 lg:px-8">
          <span>Todos los derechos © 2026 / Clínica Veterinaria San Martín de Porres - Ayacucho</span>
          <span>Hecho con 💚 para las mascotas</span>
        </div>
      </div>
    </footer>
  `,
})
export class FooterComponent { readonly contact = inject(ClinicContactService); }
