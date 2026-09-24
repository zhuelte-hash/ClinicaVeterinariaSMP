import { computed, Injectable, signal } from '@angular/core';

const CART_KEY = 'clinic_cart_v1';
const PENDING_CART_ITEM_KEY = 'clinic_pending_cart_item_v1';

export interface CartItem {
  id: string;
  nombre: string;
  precio: number;
  imagen: string;
  imageAlt: string;
  stock: number;
  cantidad: number;
}

type NewCartItem = Omit<CartItem, 'cantidad'>;

@Injectable({ providedIn: 'root' })
export class CartService {
  private readonly itemsState = signal<CartItem[]>(this.readItems(CART_KEY));

  readonly items = this.itemsState.asReadonly();
  readonly count = computed(() => this.itemsState().reduce((total, item) => total + item.cantidad, 0));
  readonly total = computed(() => this.itemsState().reduce(
    (total, item) => total + item.cantidad * item.precio,
    0,
  ));

  add(item: NewCartItem, quantity = 1): void {
    const items = this.itemsState().map((current) => ({ ...current }));
    const existing = items.find((current) => current.id === item.id);
    if (existing) {
      existing.cantidad = Math.min(existing.stock, existing.cantidad + quantity);
    } else if (item.stock > 0) {
      items.push({ ...item, cantidad: Math.min(item.stock, Math.max(1, quantity)) });
    }
    this.update(items);
  }

  queuePending(item: NewCartItem): void {
    sessionStorage.setItem(PENDING_CART_ITEM_KEY, JSON.stringify(item));
  }

  addPending(): boolean {
    const pending = this.readPending();
    sessionStorage.removeItem(PENDING_CART_ITEM_KEY);
    if (!pending) return false;
    this.add(pending);
    return true;
  }

  remove(id: string): void {
    this.update(this.itemsState().filter((item) => item.id !== id));
  }

  setQty(id: string, quantity: number): void {
    if (quantity <= 0) {
      this.remove(id);
      return;
    }
    this.update(this.itemsState().map((item) =>
      item.id === id ? { ...item, cantidad: Math.min(item.stock, quantity) } : item,
    ));
  }

  clear(): void {
    this.update([]);
  }

  private update(items: CartItem[]): void {
    this.itemsState.set(items);
    sessionStorage.setItem(CART_KEY, JSON.stringify(items));
  }

  private readPending(): NewCartItem | null {
    try {
      const value: unknown = JSON.parse(sessionStorage.getItem(PENDING_CART_ITEM_KEY) ?? 'null');
      return this.isNewItem(value) ? value : null;
    } catch {
      return null;
    }
  }

  private readItems(key: string): CartItem[] {
    try {
      const value: unknown = JSON.parse(sessionStorage.getItem(key) ?? '[]');
      return Array.isArray(value) ? value.filter((item): item is CartItem =>
        this.isNewItem(item)
        && 'cantidad' in item
        && typeof item.cantidad === 'number'
        && item.cantidad >= 1
        && item.cantidad <= item.stock) : [];
    } catch {
      sessionStorage.removeItem(key);
      return [];
    }
  }

  private isNewItem(value: unknown): value is NewCartItem {
    if (typeof value !== 'object' || value === null) return false;
    const item = value as Record<string, unknown>;
    return typeof item['id'] === 'string'
      && typeof item['nombre'] === 'string'
      && typeof item['precio'] === 'number'
      && typeof item['imagen'] === 'string'
      && typeof item['imageAlt'] === 'string'
      && typeof item['stock'] === 'number'
      && item['stock'] > 0;
  }
}
