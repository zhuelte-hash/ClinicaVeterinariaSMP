import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-contacto',
  standalone: true,
  imports: [FormsModule, CommonModule],
  template: `
    <div class="relative bg-pet-900 text-white py-14 text-center overflow-hidden">
      <img src="https://images.unsplash.com/photo-1548199973-03cce0bbc87b?auto=format&fit=crop&w=1600&q=80" alt="perritos" class="absolute inset-0 w-full h-full object-cover opacity-40" />
      <div class="relative">
        <h1 class="text-4xl font-extrabold">Contacto 🐾</h1>
        <p class="mt-2 text-sm text-sky-100"><a href="/" class="hover:underline">Inicio</a> - Contacto</p>
        <div class="flex justify-center gap-2 mt-4">
          <img src="https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?auto=format&fit=crop&w=200&q=80" class="w-16 h-16 rounded-full object-cover border-2 border-white" alt="perrito" />
          <img src="https://images.unsplash.com/photo-1592194996308-7b43878e84a6?auto=format&fit=crop&w=200&q=80" class="w-16 h-16 rounded-full object-cover border-2 border-white" alt="gatito" />
          <img src="https://images.unsplash.com/photo-1558788353-f76d92427f16?auto=format&fit=crop&w=200&q=80" class="w-16 h-16 rounded-full object-cover border-2 border-white" alt="perro" />
        </div>
      </div>
    </div>

    <div class="max-w-7xl mx-auto px-4 py-12 grid lg:grid-cols-2 gap-10">
      <div>
        <h2 class="text-3xl font-extrabold text-pet-900 mb-4">Contáctanos</h2>
        <div class="space-y-3 text-gray-700 mb-6">
          <p class="flex gap-2 items-center"><span class="w-9 h-9 bg-brand-50 rounded-full flex items-center justify-center">📱</span><span><b>Teléfono:</b> 965 939 522</span></p>
          <p class="flex gap-2 items-center"><span class="w-9 h-9 bg-brand-50 rounded-full flex items-center justify-center">✉️</span><span><b>Correo:</b> vamospetshop@gmail.com</span></p>
          <p class="flex gap-2 items-center"><span class="w-9 h-9 bg-brand-50 rounded-full flex items-center justify-center">📍</span><span><b>Dirección:</b> Jr. Quinua N° 178 – Cercado, Ayacucho</span></p>
          <p class="text-sm text-gray-500">⏰ Cerrado · Abre a las 8 a.m. · Lun-Sáb 8am-8pm</p>
        </div>
        <div class="grid grid-cols-3 gap-3 mb-6">
          <img src="https://veterinariavamospet.pe/wp-content/uploads/2025/12/Diseno-sin-titulo-58.png" alt="mascota 1" class="rounded-2xl object-cover h-32 w-full shadow" />
          <img src="https://veterinariavamospet.pe/wp-content/uploads/2025/12/Diseno-sin-titulo-59.png" alt="mascota 2" class="rounded-2xl object-cover h-32 w-full shadow" />
          <img src="https://veterinariavamospet.pe/wp-content/uploads/2025/12/Diseno-sin-titulo-60.png" alt="mascota 3" class="rounded-2xl object-cover h-32 w-full shadow" />
        </div>
        <iframe
          title="mapa"
          src="https://www.google.com/maps?q=Jr+Quinua+178+Cercado+Ayacucho&output=embed"
          class="w-full h-64 rounded-2xl border shadow-sm"
          loading="lazy"></iframe>
      </div>

      <div class="bg-white rounded-3xl shadow-xl border p-6 sm:p-8">
        <h3 class="text-xl font-bold text-pet-900 mb-1">Déjanos un mensaje</h3>
        <p class="text-sm text-gray-500 mb-5">Te respondemos por WhatsApp en minutos.</p>
        <form (ngSubmit)="enviar()" #f="ngForm" class="space-y-4">
          <div class="grid sm:grid-cols-2 gap-4">
            <input [(ngModel)]="form.nombre" name="nombre" required placeholder="Tu nombre *" class="w-full border rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
            <input [(ngModel)]="form.telefono" name="telefono" required placeholder="Celular / WhatsApp *" class="w-full border rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
          </div>
          <input [(ngModel)]="form.email" name="email" placeholder="Correo electrónico" class="w-full border rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
          <select [(ngModel)]="form.servicio" name="servicio" class="w-full border rounded-xl px-4 py-3 text-sm bg-white">
            <option *ngFor="let s of servicios" [value]="s">{{ s }}</option>
          </select>
          <textarea [(ngModel)]="form.mensaje" name="mensaje" required rows="4" placeholder="¿Cómo podemos ayudarte? *" class="w-full border rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"></textarea>
          <button class="w-full py-3 rounded-xl bg-brand-500 text-white font-bold hover:bg-brand-600 transition">Enviar por WhatsApp 🟢</button>
          <p *ngIf="ok" class="text-green-600 text-sm text-center font-medium">¡Abriendo WhatsApp con tu mensaje...!</p>
        </form>
        <div class="mt-5 flex gap-2 text-xs text-gray-500 justify-center">
          <span class="bg-gray-100 px-3 py-1 rounded-full">⏱ Lun-Sáb 8am-8pm</span>
          <span class="bg-gray-100 px-3 py-1 rounded-full">🚨 Urgencias 24h</span>
        </div>
      </div>
    </div>
  `,
})
export class ContactoComponent {
  servicios = ['Consulta Médica','Consulta a Domicilio','Consulta virtual','Grooming','Hospedaje','Laboratorio','Vacunas','Cirugía','Otro'];
  form = { nombre: '', telefono: '', email: '', servicio: 'Consulta Médica', mensaje: '' };
  ok = false;
  enviar() {
    if (!this.form.nombre || !this.form.telefono || !this.form.mensaje) return;
    const txt = `Hola necesito más información sobre:%0A%0A*Nombre:* ${this.form.nombre}%0A*Servicio:* ${this.form.servicio}%0A*Tel:* ${this.form.telefono}%0A*Msg:* ${this.form.mensaje}`;
    window.open(`https://wa.me/51965939522?text=${txt}`, '_blank');
    this.ok = true;
  }
}
