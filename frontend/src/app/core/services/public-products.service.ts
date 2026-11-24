import { HttpClient } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { environment } from '../../../environments/environment';
import { Product } from '../models/producto.model';
import { CartService } from '../../services/cart.service';
import { NoticeService } from './notice.service';
import { publicImageUrl } from '../utils/public-image-url';

export interface CatalogProduct {
  id: number;
  nombre: string;
  categoria_nombre: string;
  precio_venta: string | null;
  stock_actual: number;
  imagen_url: string;
  descripcion: string | null;
  especies: string[];
  marca?: string | null;
  presentacion?: string | null;
  subcategoria?: string | null;
  es_demostracion?: boolean;
  catalogo_origen?: { especie?: string | null; tipo_precio_venta?: string; fecha_consulta?: string; fotografia_verificada?: unknown } | null;
}

@Injectable({ providedIn: 'root' })
export class PublicProductsService {
  private readonly http = inject(HttpClient);
  private readonly cart = inject(CartService);
  private readonly notice = inject(NoticeService);
  private readonly productsState = signal<Product[]>([]);
  readonly products = this.productsState.asReadonly();
  readonly loading = signal(false);
  readonly error = signal('');

  load(): void {
    this.loading.set(true);
    this.error.set('');
    this.http.get<CatalogProduct[]>(`${environment.apiUrl}/catalogo/productos`).subscribe({
      next: (items) => {
        const products = items.map((item) => ({
          id: String(item.id), name: item.nombre, category: item.categoria_nombre,
          price: item.precio_venta === null ? null : Number(item.precio_venta), stock: item.stock_actual,
          image: publicImageUrl(item.imagen_url), imageAlt: item.nombre,
          description: item.descripcion || '', species: item.especies,
          brand: item.marca, presentation: item.presentacion, subcategory: item.subcategoria,
          demo: item.es_demostracion, historicalPrice: item.catalogo_origen?.tipo_precio_venta === 'publicado_historico_indexado',
          speciesPending: item.catalogo_origen?.especie === null,
        }));
        this.productsState.set(products);
        if (this.cart.reconcile(products.filter(item => item.price !== null).map((item) => ({
          id: item.id, nombre: item.name, precio: item.price!, stock: item.stock,
          imagen: item.image, imageAlt: item.imageAlt,
        })))) this.notice.show('Tu carrito se actualizó con los precios y existencias actuales.');
        this.loading.set(false);
      },
      error: () => {
        this.error.set('No se pudo cargar el catálogo. Intenta de nuevo.');
        this.loading.set(false);
      },
    });
  }
}
