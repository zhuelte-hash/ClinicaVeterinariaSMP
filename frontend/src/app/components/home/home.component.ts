import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { NoticeService } from '../../core/services/notice.service';
import { CartService } from '../../services/cart.service';
import { PRODUCTS } from '../../core/data/productos.mock';
import { ProductCardComponent } from '../../shared/product-card/product-card.component';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [RouterLink, ProductCardComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="relative isolate overflow-hidden bg-pet-900 text-white">
      <img src="https://images.unsplash.com/photo-1548199973-03cce0bbc87b?auto=format&fit=crop&w=1600&q=80" alt="" class="absolute inset-0 -z-20 h-full w-full object-cover opacity-45" />
      <div class="absolute inset-0 -z-10 bg-[#0B1B6D]/65"></div>
      <div class="relative mx-auto max-w-7xl px-4 py-14 text-center sm:px-6 sm:py-16 lg:py-20">
        <p class="mb-3 text-xs font-bold uppercase tracking-[0.18em] text-[#aee5e9] sm:text-sm">Atención veterinaria en Ayacucho</p>
        <h1 class="mx-auto max-w-4xl text-3xl font-extrabold leading-tight tracking-tight sm:text-5xl">Clínica Veterinaria San Martín de Porres</h1>
        <p class="mx-auto mt-4 max-w-2xl text-base leading-7 text-white/90 sm:text-lg">Cuidado, amor y salud para tus mejores amigos. Atención cercana y profesional para tu mascota.</p>
        <p class="mt-3 text-sm text-white/80">Jr. Quinua N° 178 – Cercado, Ayacucho · 965 939 522</p>
        <div class="mt-7 flex flex-col justify-center gap-3 sm:flex-row">
          <a routerLink="/reservar-cita" class="inline-flex min-h-12 items-center justify-center rounded-full bg-[#E0A71A] px-6 py-3 text-sm font-bold text-[#1A1E27] transition hover:bg-[#f2c957]">Reservar cita</a>
          <a routerLink="/contacto" class="inline-flex min-h-12 items-center justify-center rounded-full border border-white/75 bg-white/10 px-6 py-3 text-sm font-bold text-white transition hover:bg-white hover:text-[#0B1B6D]">Contáctanos</a>
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

          <div class="mt-8 flex flex-wrap gap-3">
            <a routerLink="/servicios" class="site-button">Explorar servicios <span aria-hidden="true">→</span></a>
            <a routerLink="/productos" class="inline-flex min-h-11 items-center justify-center rounded-full border border-[#0B1B6D]/25 bg-white px-6 py-3 text-sm font-bold text-[#0B1B6D] transition hover:border-[#1A98A2] hover:bg-brand-50">Ver productos</a>
          </div>
        </div>

        <div class="order-1 lg:order-2">
          <div class="relative mx-auto max-w-xl">
             <div class="absolute -inset-2 translate-x-2 translate-y-2 rounded-[1.5rem] bg-[#0799AE] sm:-inset-3"></div>
             <div class="relative overflow-hidden rounded-[1.4rem] border-4 border-white bg-[#0799AE] shadow-[0_16px_36px_rgba(7,153,174,0.16)]">
               <img src="https://images.unsplash.com/photo-1518717758536-85ae29035b6d?auto=format&fit=crop&w=1200&q=88" alt="Perro descansando" loading="lazy" class="h-[280px] w-full object-cover object-center sm:h-[390px] lg:h-[440px]" />
            </div>
            <span class="absolute -bottom-4 -left-3 grid h-16 w-16 place-items-center rounded-2xl bg-[#F4C430] text-[#0B1B6D] shadow-lg sm:h-20 sm:w-20" aria-hidden="true"><svg class="h-9 w-9 sm:h-11 sm:w-11" viewBox="0 0 24 24" fill="currentColor"><circle cx="6" cy="8" r="2"/><circle cx="10" cy="5" r="2"/><circle cx="14" cy="5" r="2"/><circle cx="18" cy="8" r="2"/><path d="M12 10c-3.5 0-6 2.5-6 5.4C6 18.3 8.6 20 12 20s6-1.7 6-4.6c0-2.9-2.5-5.4-6-5.4Z"/></svg></span>
          </div>
        </div>
      </div>
    </section>

    <div class="max-w-7xl mx-auto px-4 py-12 sm:px-6 lg:px-8 lg:py-16">
       <h2 class="text-2xl font-extrabold text-pet-900 text-center mb-6">El bienestar de las mascotas nos inspira</h2>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4 mb-12">
        <img src="https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?auto=format&fit=crop&w=400&q=80" class="h-48 w-full object-cover rounded-2xl shadow" alt="perrito" />
        <img src="https://images.unsplash.com/photo-1592194996308-7b43878e84a6?auto=format&fit=crop&w=400&q=80" class="h-48 w-full object-cover rounded-2xl shadow" alt="gatito" />
        <img src="https://images.unsplash.com/photo-1601758228041-f3b2795255f1?auto=format&fit=crop&w=400&q=80" class="h-48 w-full object-cover rounded-2xl shadow" alt="perro familia" />
        <img src="https://images.unsplash.com/photo-1558788353-f76d92427f16?auto=format&fit=crop&w=400&q=80" class="h-48 w-full object-cover rounded-2xl shadow" alt="perro feliz" />
      </div>

      <div class="grid md:grid-cols-3 gap-6 text-left">
        <div class="site-card flex flex-col p-5 sm:p-6">
          <img src="https://images.unsplash.com/photo-1576201836106-db1758fd1c97?auto=format&fit=crop&w=600&q=80" class="h-36 w-full object-cover rounded-xl mb-4" alt="consulta" />
          <h3 class="font-bold text-pet-900 mb-1">Consulta Médica - S/ 50</h3>
          <p class="text-sm text-gray-600">Atención integral para perros, gatos y más.</p>
          <button type="button" (click)="add('c1','Consulta Médica',50)" class="site-button mt-auto w-full">Agregar al carrito</button>
        </div>
        <div class="site-card flex flex-col p-5 sm:p-6">
          <img src="https://images.unsplash.com/photo-1516734212186-a967f81ad0d7?auto=format&fit=crop&w=600&q=80" class="h-36 w-full object-cover rounded-xl mb-4" alt="grooming" />
          <h3 class="font-bold text-pet-900 mb-1">Grooming y Baño - S/ 60</h3>
          <p class="text-sm text-gray-600">Belleza y higiene con amor.</p>
          <button type="button" (click)="add('g1','Grooming y Baño',60)" class="site-button mt-auto w-full">Agregar al carrito</button>
        </div>
        <div class="site-card flex flex-col p-5 sm:p-6">
          <img src="https://images.unsplash.com/photo-1629909613654-28e377c37b09?auto=format&fit=crop&w=600&q=80" class="h-36 w-full object-cover rounded-xl mb-4" alt="vacunas" />
          <h3 class="font-bold text-pet-900 mb-1">Vacunas - S/ 45</h3>
          <p class="text-sm text-gray-600">Prevención y cuidado seguro.</p>
          <button type="button" (click)="add('v1','Vacuna',45)" class="site-button mt-auto w-full">Agregar al carrito</button>
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
           <div><p class="text-sm font-bold uppercase tracking-[0.18em] text-[#147d87]">Tienda para mascotas</p><h2 class="mt-2 text-3xl font-extrabold text-[#0B1B6D] sm:text-4xl">Productos destacados</h2><p class="mt-3 text-slate-600">Encuentra lo mejor para el cuidado y felicidad de tu mascota.</p></div>
           <a routerLink="/productos" class="inline-flex min-h-11 items-center font-bold text-[#0B1B6D] hover:text-[#147d87]">Ver todo el catálogo →</a>
        </div>
        <div class="mt-9 grid gap-6 lg:grid-cols-[250px_1fr]">
          <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
            <a routerLink="/productos" class="relative min-h-44 overflow-hidden rounded-3xl bg-[#0B1B6D] p-6 text-white"><div class="absolute -bottom-10 -right-8 h-32 w-32 rounded-full bg-sky-400/30"></div><p class="text-xs font-bold uppercase tracking-wider text-sky-300">Selección del mes</p><h3 class="mt-3 text-2xl font-black">Ofertas especiales</h3><span class="mt-5 inline-block text-sm font-bold">Descubrir productos →</span></a>
             <a routerLink="/productos" class="relative min-h-44 overflow-hidden rounded-2xl bg-[#f8ecd2] p-6 text-[#0B1B6D] transition hover:bg-[#f5e4bf]"><div class="absolute -right-6 -top-8 h-28 w-28 rounded-full bg-[#E0A71A]/15"></div><p class="text-xs font-bold uppercase tracking-wider text-[#725409]">Recién llegados</p><h3 class="mt-3 text-2xl font-extrabold">Nuevos productos</h3><span class="mt-5 inline-block text-sm font-bold">Ver novedades →</span></a>
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
  private readonly notice = inject(NoticeService);
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
    this.cart.add(item);
    this.notice.show('Producto añadido al carrito');
  }
}
