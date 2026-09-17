import { Injectable, signal, computed } from '@angular/core';

export interface CartItem { id: string; nombre: string; precio: number; imagen?: string; cantidad: number; }

@Injectable({ providedIn: 'root' })
export class CartService {
  private _items = signal<CartItem[]>([]);
  items = this._items.asReadonly();
  count = computed(() => this._items().reduce((a, i) => a + i.cantidad, 0));
  total = computed(() => this._items().reduce((a, i) => a + i.cantidad * i.precio, 0));

  add(item: Omit<CartItem, 'cantidad'>, qty = 1) {
    const list = [...this._items()];
    const f = list.find(i => i.id === item.id);
    if (f) f.cantidad += qty; else list.push({ ...item, cantidad: qty });
    this._items.set(list);
  }
  remove(id: string) { this._items.set(this._items().filter(i => i.id !== id)); }
  setQty(id: string, qty: number) {
    if (qty <= 0) return this.remove(id);
    this._items.set(this._items().map(i => i.id === id ? { ...i, cantidad: qty } : i));
  }
  clear() { this._items.set([]); }
}
