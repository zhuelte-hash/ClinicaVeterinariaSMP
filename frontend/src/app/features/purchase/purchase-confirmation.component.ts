import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { PURCHASE_CONFIG } from '../../core/config/purchase.config';
import { LocalPurchaseService, WebOrder } from '../../core/services/local-purchase.service';

@Component({
  selector: 'app-purchase-confirmation', standalone: true, imports: [RouterLink, CommonModule],
  templateUrl: './purchase-confirmation.component.html',
  styleUrl: './purchase-confirmation.component.css', changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PurchaseConfirmationComponent {
  private readonly purchases = inject(LocalPurchaseService);
  private readonly route = inject(ActivatedRoute);
  readonly order = signal<WebOrder | null>(null);
  readonly error = signal('');
  readonly config = signal(PURCHASE_CONFIG);
  readonly whatsappUrl = computed(() => {
    const order = this.order();
    const number = this.config().whatsappNumber;
    if (!order || !/^[1-9]\d{7,14}$/.test(number)) return '';
    const message = `Hola, he realizado el pedido N.° ${order.codigo_pedido} en la Clínica Veterinaria San Martín de Porres. Quisiera consultar sobre el estado de mi compra.`;
    return `https://wa.me/${number}?text=${encodeURIComponent(message)}`;
  });
  constructor() {
    const id = Number(this.route.snapshot.queryParamMap.get('pedido'));
    if (id) this.purchases.get(id).subscribe({ next: order => this.order.set(order), error: () => this.error.set('No se pudo consultar el pedido.') });
    this.purchases.configuration().subscribe({ next: config => this.config.set(config) });
  }
  printSummary() { window.print(); }
}
