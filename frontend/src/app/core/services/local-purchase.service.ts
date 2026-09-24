import { Injectable, signal } from '@angular/core';
import { PedidoTemporal, PurchaseOrderItem, PurchaseProduct } from '../models/purchase.model';

const TEMPORARY_ORDER_KEY = 'clinic_temporary_order_v1';
const ORDER_SEQUENCE_KEY = 'clinic_order_sequence_v1';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isPurchaseProduct(value: unknown): value is PurchaseProduct {
  return isRecord(value)
    && typeof value['id'] === 'string'
    && typeof value['name'] === 'string'
    && typeof value['price'] === 'number'
    && typeof value['stock'] === 'number'
    && typeof value['image'] === 'string'
    && typeof value['imageAlt'] === 'string';
}

function isOrderItem(value: unknown): value is PurchaseOrderItem {
  if (!isRecord(value) || !isPurchaseProduct(value)) return false;
  return typeof value['cantidad'] === 'number' && typeof value['subtotal'] === 'number';
}

function isOrder(value: unknown): value is PedidoTemporal {
  return isRecord(value)
    && typeof value['codigo'] === 'string'
    && typeof value['fechaIso'] === 'string'
    && isRecord(value['cliente'])
    && typeof value['cliente']['nombreCompleto'] === 'string'
    && Array.isArray(value['items'])
    && value['items'].length > 0
    && value['items'].every(isOrderItem)
    && typeof value['total'] === 'number'
    && (value['metodoPago'] === 'Yape' || value['metodoPago'] === 'Plin')
    && typeof value['numeroOperacion'] === 'string';
}

@Injectable({ providedIn: 'root' })
export class LocalPurchaseService {
  private readonly orderState = signal<PedidoTemporal | null>(
    this.read(TEMPORARY_ORDER_KEY, isOrder),
  );

  readonly currentOrder = this.orderState.asReadonly();

  saveOrder(order: PedidoTemporal): void {
    this.orderState.set(order);
    sessionStorage.setItem(TEMPORARY_ORDER_KEY, JSON.stringify(order));
  }

  createOrderCode(date = new Date()): string {
    const datePart = [date.getFullYear(), date.getMonth() + 1, date.getDate()]
      .map((part, index) => index === 0 ? String(part) : String(part).padStart(2, '0'))
      .join('');
    const stored = this.read(
      ORDER_SEQUENCE_KEY,
      (value): value is { date: string; sequence: number } =>
        isRecord(value)
        && typeof value['date'] === 'string'
        && typeof value['sequence'] === 'number',
    );
    const sequence = stored?.date === datePart ? stored.sequence + 1 : 1;
    sessionStorage.setItem(ORDER_SEQUENCE_KEY, JSON.stringify({ date: datePart, sequence }));
    return `VET-${datePart}-${String(sequence).padStart(3, '0')}`;
  }

  private read<T>(key: string, isValid: (value: unknown) => value is T): T | null {
    try {
      const value = sessionStorage.getItem(key);
      if (!value) return null;
      const parsed: unknown = JSON.parse(value);
      if (!isValid(parsed)) {
        sessionStorage.removeItem(key);
        return null;
      }
      return parsed;
    } catch {
      sessionStorage.removeItem(key);
      return null;
    }
  }

}
