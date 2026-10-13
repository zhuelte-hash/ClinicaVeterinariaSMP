import { HttpClient } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { environment } from '../../../environments/environment';
import { Product } from '../models/producto.model';
import { CartService } from '../../services/cart.service';
import { NoticeService } from './notice.service';

interface CatalogProduct {
  id: number;
  nombre: string;
  categoria_nombre: string;
  precio_venta: string;
  stock_actual: number;
  imagen_url: string;
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
          price: Number(item.precio_venta), stock: item.stock_actual,
          image: item.imagen_url || '/logo.png', imageAlt: item.nombre,
        }));
        this.productsState.set(products);
        if (this.cart.reconcile(products.map((item) => ({
          id: item.id, nombre: item.name, precio: item.price, stock: item.stock,
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
