import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { PURCHASE_CONFIG } from '../../core/config/purchase.config';
import { LocalPurchaseService } from '../../core/services/local-purchase.service';

@Component({
  selector: 'app-purchase-confirmation',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './purchase-confirmation.component.html',
  styleUrl: './purchase-confirmation.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PurchaseConfirmationComponent {
  private readonly purchases = inject(LocalPurchaseService);
  readonly order = this.purchases.currentOrder;
  readonly formattedDate = computed(() => {
    const order = this.order();
    if (!order) return '';
    return new Intl.DateTimeFormat('es-PE', {
      dateStyle: 'long',
      timeStyle: 'short',
    }).format(new Date(order.fechaIso));
  });
  readonly whatsappUrl = computed(() => {
    const order = this.order();
    if (!order) return '';
    const address = order.cliente.tipoEntrega === 'Delivery'
      ? order.cliente.direccion
      : 'Recojo en clínica';
    const productLines = order.items.map((item) =>
      `• ${item.name} x${item.cantidad} — S/ ${item.subtotal.toFixed(2)}`,
    );
    const message = [
      '🐾 *NUEVA ORDEN WEB – Clínica Veterinaria San Martín de Porres*',
      '',
      `Código: ${order.codigo}`,
      `Cliente: ${order.cliente.nombreCompleto}`,
      `Celular: ${order.cliente.celular}`,
      `Entrega: ${order.cliente.tipoEntrega}`,
      `Dirección: ${address}`,
      '',
      '*Productos:*',
      ...productLines,
      '',
      `Total: S/ ${order.total.toFixed(2)}`,
      `Método de pago: ${order.metodoPago}`,
      `N.° de operación: ${order.numeroOperacion}`,
      `Estado: ${order.estadoPago}`,
    ].join('\n');
    return `https://wa.me/${PURCHASE_CONFIG.whatsappNumber}?text=${encodeURIComponent(message)}`;
  });

  printSummary(): void {
    window.print();
  }
}
