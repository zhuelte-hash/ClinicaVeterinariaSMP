import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { VisualSessionService } from '../../core/services/visual-session.service';
import { CartService } from '../../services/cart.service';
import { PRODUCTS } from '../../core/data/productos.mock';
import { ProductCardComponent } from '../../shared/product-card/product-card.component';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [RouterLink, ProductCardComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="relative bg-pet-900 text-white overflow-hidden">
      <img src="https://images.unsplash.com/photo-1548199973-03cce0bbc87b?auto=format&fit=crop&w=1600&q=80" alt="perritos felices" class="absolute inset-0 w-full h-full object-cover opacity-40" />
      <div class="relative max-w-7xl mx-auto px-4 py-20 text-center">
        <img src="/logo.png" alt="logo" class="w-20 h-20 mx-auto rounded-full border-4 border-white/40 shadow-lg mb-4 bg-white" />
        <h1 class="text-4xl sm:text-5xl font-extrabold mb-3">Clínica Veterinaria<br/>San Martín de Porres</h1>
        <p class="text-lg text-sky-100 mb-2">Jr. Quinua N° 178 – Cercado, Ayacucho | 965 939 522</p>
        <p class="text-sky-100 mb-8">Cuidado, amor y salud para tus mejores amigos 🐶🐱</p>
        <div class="flex justify-center gap-3 flex-wrap">
          <a routerLink="/contacto" class="px-6 py-3 bg-brand-500 rounded-full font-bold hover:bg-brand-600 shadow-lg">Reservar Cita</a>
          <a routerLink="/contacto" class="px-6 py-3 bg-white text-pet-900 rounded-full font-bold hover:bg-sky-100">Contáctanos</a>
        </div>
      </div>
    </div>

    <section class="bg-[#FFF9F4] py-14 sm:py-20 lg:py-24" aria-labelledby="about-title">
      <div class="mx-auto grid max-w-7xl items-center gap-10 px-4 sm:px-6 lg:grid-cols-[1.02fr_.98fr] lg:gap-16 lg:px-8">
        <div class="order-2 lg:order-1">
          <div class="mb-5 flex items-center gap-3">
            <span class="grid h-10 w-10 place-items-center rounded-full bg-[#F4C430]/20 text-[#F4C430]" aria-hidden="true">
              <svg class="h-6 w-6" viewBox="0 0 24 24" fill="currentColor"><circle cx="6" cy="8" r="2"/><circle cx="10" cy="5" r="2"/><circle cx="14" cy="5" r="2"/><circle cx="18" cy="8" r="2"/><path d="M12 10c-3.5 0-6 2.5-6 5.4C6 18.3 8.6 20 12 20s6-1.7 6-4.6c0-2.9-2.5-5.4-6-5.4Z"/></svg>
            </span>
            <p class="text-sm font-extrabold uppercase tracking-[0.2em] text-[#0799AE]">Nosotros</p>
          </div>
          <h2 id="about-title" class="max-w-xl text-3xl font-black leading-tight tracking-tight text-[#0B1B6D] sm:text-4xl lg:text-5xl">Cuidamos la salud de quienes más amas</h2>
          <p class="mt-5 max-w-xl text-base leading-7 text-slate-600 sm:text-lg sm:leading-8">En la Clínica Veterinaria San Martín de Porres acompañamos a tu mascota con atención cercana, experiencia y un cuidado responsable en cada etapa de su vida.</p>
          <p class="mt-4 max-w-xl text-sm leading-7 text-slate-500 sm:text-base">Nuestro equipo trabaja para que cada visita sea tranquila y para que encuentres orientación, servicios y productos pensados para su bienestar.</p>

          <form class="mt-8 flex max-w-xl flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-2 shadow-[0_10px_35px_rgba(11,27,109,0.07)] sm:flex-row" (submit)="$event.preventDefault()">
            <label class="relative min-w-0 flex-1">
              <span class="sr-only">Buscar servicios o productos</span>
              <svg class="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-[#0799AE]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
              <input type="search" placeholder="¿Qué necesitas para tu mascota?" class="w-full rounded-xl border border-transparent bg-slate-50 py-3 pl-12 pr-4 text-sm text-slate-700 outline-none transition focus:border-[#0799AE] focus:bg-white focus:ring-2 focus:ring-[#0799AE]/15" />
            </label>
            <a routerLink="/servicios" class="inline-flex items-center justify-center rounded-xl bg-[#0B1B6D] px-6 py-3 text-sm font-bold text-white transition hover:bg-[#0799AE] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0799AE]">Buscar</a>
          </form>
        </div>

        <div class="order-1 lg:order-2">
          <div class="relative mx-auto max-w-xl">
            <div class="absolute -inset-3 translate-x-3 translate-y-3 rounded-[2rem] bg-[#0799AE] sm:-inset-4"></div>
            <div class="relative overflow-hidden rounded-[1.75rem] border-4 border-white bg-[#0799AE] shadow-[0_22px_60px_rgba(7,153,174,0.22)]">
              <img src="https://images.unsplash.com/photo-1518717758536-85ae29035b6d?auto=format&fit=crop&w=1200&q=88" alt="Perrito negro de la Clínica Veterinaria San Martín de Porres" class="h-[320px] w-full object-cover object-center sm:h-[440px] lg:h-[500px]" />
            </div>
            <span class="absolute -bottom-4 -left-3 grid h-16 w-16 place-items-center rounded-2xl bg-[#F4C430] text-[#0B1B6D] shadow-lg sm:h-20 sm:w-20" aria-hidden="true"><svg class="h-9 w-9 sm:h-11 sm:w-11" viewBox="0 0 24 24" fill="currentColor"><circle cx="6" cy="8" r="2"/><circle cx="10" cy="5" r="2"/><circle cx="14" cy="5" r="2"/><circle cx="18" cy="8" r="2"/><path d="M12 10c-3.5 0-6 2.5-6 5.4C6 18.3 8.6 20 12 20s6-1.7 6-4.6c0-2.9-2.5-5.4-6-5.4Z"/></svg></span>
          </div>
        </div>
      </div>
    </section>

    <div class="max-w-7xl mx-auto px-4 py-10">
      <h2 class="text-2xl font-extrabold text-pet-900 text-center mb-6">Nuestros pacientes felices</h2>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
        <img src="https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?auto=format&fit=crop&w=400&q=80" class="h-48 w-full object-cover rounded-2xl shadow" alt="perrito" />
        <img src="https://images.unsplash.com/photo-1592194996308-7b43878e84a6?auto=format&fit=crop&w=400&q=80" class="h-48 w-full object-cover rounded-2xl shadow" alt="gatito" />
        <img src="https://images.unsplash.com/photo-1601758228041-f3b2795255f1?auto=format&fit=crop&w=400&q=80" class="h-48 w-full object-cover rounded-2xl shadow" alt="perro familia" />
        <img src="https://images.unsplash.com/photo-1558788353-f76d92427f16?auto=format&fit=crop&w=400&q=80" class="h-48 w-full object-cover rounded-2xl shadow" alt="perro feliz" />
      </div>

      <div class="grid md:grid-cols-3 gap-6 text-left">
        <div class="bg-white p-6 rounded-2xl shadow-sm border">
          <img src="https://images.unsplash.com/photo-1576201836106-db1758fd1c97?auto=format&fit=crop&w=600&q=80" class="h-36 w-full object-cover rounded-xl mb-4" alt="consulta" />
          <h3 class="font-bold text-pet-900 mb-1">Consulta Médica - S/ 50</h3>
          <p class="text-sm text-gray-600">Atención integral para perros, gatos y más.</p>
          <button (click)="add('c1','Consulta Médica',50)" class="mt-3 w-full py-2 bg-pet-700 text-white rounded-full text-sm font-bold hover:bg-pet-900">Agregar 🛒</button>
        </div>
        <div class="bg-white p-6 rounded-2xl shadow-sm border">
          <img src="https://images.unsplash.com/photo-1516734212186-a967f81ad0d7?auto=format&fit=crop&w=600&q=80" class="h-36 w-full object-cover rounded-xl mb-4" alt="grooming" />
          <h3 class="font-bold text-pet-900 mb-1">Grooming y Baño - S/ 60</h3>
          <p class="text-sm text-gray-600">Belleza y higiene con amor.</p>
          <button (click)="add('g1','Grooming y Baño',60)" class="mt-3 w-full py-2 bg-pet-700 text-white rounded-full text-sm font-bold hover:bg-pet-900">Agregar 🛒</button>
        </div>
        <div class="bg-white p-6 rounded-2xl shadow-sm border">
          <img src="https://images.unsplash.com/photo-1629909613654-28e377c37b09?auto=format&fit=crop&w=600&q=80" class="h-36 w-full object-cover rounded-xl mb-4" alt="vacunas" />
          <h3 class="font-bold text-pet-900 mb-1">Vacunas - S/ 45</h3>
          <p class="text-sm text-gray-600">Prevención y cuidado seguro.</p>
          <button (click)="add('v1','Vacuna',45)" class="mt-3 w-full py-2 bg-pet-700 text-white rounded-full text-sm font-bold hover:bg-pet-900">Agregar 🛒</button>
        </div>
      </div>
      <div class="mt-8 text-center">
        <a routerLink="/servicios" class="inline-flex items-center gap-2 rounded-full bg-[#1A1E27] px-7 py-3 font-bold text-white transition hover:-translate-y-0.5 hover:bg-[#1A98A2] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1A98A2]">
          Conocer todos los servicios
          <svg class="h-4 w-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 10h12m-5-5 5 5-5 5"/></svg>
        </a>
      </div>
    </div>

    <section class="bg-[#FFF9F4] py-16">
      <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div><p class="text-sm font-bold uppercase tracking-[0.18em] text-sky-600">Tienda para mascotas</p><h2 class="mt-2 text-3xl font-black text-[#0B1B6D] sm:text-4xl">Productos destacados</h2><p class="mt-3 text-slate-600">Encuentra lo mejor para el cuidado y felicidad de tu mascota.</p></div>
          <a routerLink="/productos" class="font-bold text-[#0B1B6D] hover:text-sky-600">Ver todo el catálogo →</a>
        </div>
        <div class="mt-9 grid gap-6 lg:grid-cols-[250px_1fr]">
          <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
            <a routerLink="/productos" class="relative min-h-44 overflow-hidden rounded-3xl bg-[#0B1B6D] p-6 text-white"><div class="absolute -bottom-10 -right-8 h-32 w-32 rounded-full bg-sky-400/30"></div><p class="text-xs font-bold uppercase tracking-wider text-sky-300">Selección del mes</p><h3 class="mt-3 text-2xl font-black">Ofertas especiales</h3><span class="mt-5 inline-block text-sm font-bold">Descubrir productos →</span></a>
            <a routerLink="/productos" class="relative min-h-44 overflow-hidden rounded-3xl bg-orange-100 p-6 text-[#0B1B6D]"><div class="absolute -right-6 -top-8 h-28 w-28 rounded-full bg-[#FF6B35]/15"></div><p class="text-xs font-bold uppercase tracking-wider text-[#FF6B35]">Recién llegados</p><h3 class="mt-3 text-2xl font-black">Nuevos productos</h3><span class="mt-5 inline-block text-sm font-bold">Ver novedades →</span></a>
          </div>
          <div class="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">@for (product of featuredProducts; track product.id) { <app-product-card [item]="product" /> }</div>
        </div>
      </div>
    </section>

    <section class="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <div class="text-center"><h2 class="text-3xl font-black text-[#0B1B6D]">Categorías favoritas</h2><p class="mt-3 text-slate-600">Todo lo que tu compañero necesita, en un solo lugar.</p></div>
      <div class="mt-9 grid gap-6 md:grid-cols-3">
        @for (category of favoriteCategories; track category.title) {
          <article class="group relative min-h-72 overflow-hidden rounded-3xl"><img [src]="category.image" [alt]="category.alt" loading="lazy" class="absolute inset-0 h-full w-full object-cover transition duration-500 group-hover:scale-105" /><div class="absolute inset-0 bg-gradient-to-t from-[#0B1B6D]/95 via-[#0B1B6D]/45 to-transparent"></div><div class="absolute inset-x-0 bottom-0 p-6 text-white"><h3 class="text-2xl font-black">{{ category.title }}</h3><p class="mt-2 text-sm text-sky-50">{{ category.text }}</p><a routerLink="/productos" [queryParams]="{ categoria: category.filter }" class="mt-5 inline-flex rounded-full bg-white px-4 py-2 text-sm font-bold text-[#0B1B6D]">Ver productos</a></div></article>
        }
      </div>
    </section>
  `,
})
export class HomeComponent {
  private readonly cart = inject(CartService);
  private readonly session = inject(VisualSessionService);
  private readonly router = inject(Router);
  readonly featuredProducts = PRODUCTS.filter((product) => product.featured).slice(0, 3);
  readonly favoriteCategories = [
    { title: 'Alimentos para mascotas', text: 'Opciones para acompañar su nutrición diaria.', filter: 'Alimentos', image: 'https://images.unsplash.com/photo-1589924691995-400dc9ecc119?auto=format&fit=crop&w=900&q=85', alt: 'Alimentos para mascotas' },
    { title: 'Accesorios para paseo', text: 'Paseos cómodos, seguros y llenos de aventura.', filter: 'Accesorios', image: 'https://images.unsplash.com/photo-1601758124510-52d02ddb7cbd?auto=format&fit=crop&w=900&q=85', alt: 'Perro disfrutando un paseo' },
    { title: 'Descanso y comodidad', text: 'Espacios suaves para recuperar energía.', filter: 'Descanso y dormitorio', image: 'https://images.unsplash.com/photo-1591946614720-90a587da4a36?auto=format&fit=crop&w=900&q=85', alt: 'Mascota descansando cómodamente' },
  ];

  add(id: string, nombre: string, precio: number): void {
    const item = {
      id,
      nombre,
      precio,
      imagen: '/logo.png',
      imageAlt: nombre,
      stock: 99,
    };
    if (!this.session.isLoggedIn()) {
      this.cart.queuePending(item);
      void this.router.navigate(['/login'], { queryParams: { returnUrl: '/carrito' } });
      return;
    }
    this.cart.add(item);
  }
}
