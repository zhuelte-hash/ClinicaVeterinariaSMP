import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  computed,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { AbstractControl, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { PURCHASE_CONFIG } from '../../core/config/purchase.config';
import { DatosCliente, MetodoPago, PedidoTemporal } from '../../core/models/purchase.model';
import { LocalPurchaseService } from '../../core/services/local-purchase.service';
import { VisualSessionService } from '../../core/services/visual-session.service';
import { CartService } from '../../services/cart.service';

type DeliveryOption = 'pickup' | 'delivery';
type ReceiptOption = 'boleta' | 'factura';

@Component({
  selector: 'app-purchase-checkout',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './purchase-checkout.component.html',
  host: { class: 'block' },
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PurchaseCheckoutComponent {
  private readonly formBuilder = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly purchases = inject(LocalPurchaseService);
  private readonly session = inject(VisualSessionService);
  readonly cart = inject(CartService);
  private readonly proofInput = viewChild<ElementRef<HTMLInputElement>>('proofInput');

  readonly items = this.cart.items;
  readonly deliveryType = signal<DeliveryOption>('pickup');
  readonly receiptType = signal<ReceiptOption>('boleta');
  readonly paymentMethod = signal<MetodoPago | null>(null);
  readonly paymentMethods: MetodoPago[] = ['Yape', 'Plin'];
  readonly paymentConfig = computed(() => {
    const method = this.paymentMethod();
    return method ? PURCHASE_CONFIG.payment[method] : null;
  });
  readonly proofFile = signal<File | null>(null);
  readonly proofPreview = signal<string | null>(null);
  readonly fileError = signal('');
  readonly submitted = signal(false);
  readonly subtotal = this.cart.total;
  readonly deliveryCost = computed(() =>
    this.deliveryType() === 'delivery' ? PURCHASE_CONFIG.deliveryCost : 0,
  );
  readonly total = computed(() => this.subtotal() + this.deliveryCost());

  readonly checkoutForm = this.formBuilder.nonNullable.group({
    fullName: [
      this.session.user()?.nombre === 'Cliente' ? '' : (this.session.user()?.nombre ?? ''),
      [Validators.required, Validators.minLength(3), Validators.pattern(/\S/)],
    ],
    phone: ['', [Validators.required, Validators.pattern(/^\d{9,15}$/)]],
    email: [this.session.user()?.email ?? '', Validators.email],
    delivery: ['pickup' as DeliveryOption, Validators.required],
    address: [''],
    reference: [''],
    receipt: ['boleta' as ReceiptOption, Validators.required],
    dni: ['', [Validators.required, Validators.pattern(/^\d{8}$/)]],
    ruc: [''],
    businessName: [''],
    operationNumber: ['', [Validators.required, Validators.pattern(/^\d{4,}$/)]],
  });

  changeDelivery(event: Event): void {
    const value = (event.target as HTMLInputElement).value as DeliveryOption;
    this.deliveryType.set(value);
    const address = this.checkoutForm.controls.address;
    if (value === 'delivery') {
      address.setValidators([Validators.required, Validators.minLength(5), Validators.pattern(/\S/)]);
    } else {
      address.clearValidators();
      address.setValue('');
    }
    address.updateValueAndValidity();
  }

  changeReceipt(event: Event): void {
    const value = (event.target as HTMLInputElement).value as ReceiptOption;
    this.receiptType.set(value);
    const dni = this.checkoutForm.controls.dni;
    const ruc = this.checkoutForm.controls.ruc;
    const businessName = this.checkoutForm.controls.businessName;

    if (value === 'factura') {
      dni.clearValidators();
      dni.setValue('');
      ruc.setValidators([Validators.required, Validators.pattern(/^\d{11}$/)]);
      businessName.setValidators([Validators.required, Validators.minLength(3), Validators.pattern(/\S/)]);
    } else {
      ruc.clearValidators();
      businessName.clearValidators();
      ruc.setValue('');
      businessName.setValue('');
      dni.setValidators([Validators.required, Validators.pattern(/^\d{8}$/)]);
    }
    dni.updateValueAndValidity();
    ruc.updateValueAndValidity();
    businessName.updateValueAndValidity();
  }

  selectPayment(method: MetodoPago): void {
    this.paymentMethod.set(method);
  }

  selectProof(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;

    const allowedTypes = ['image/jpeg', 'image/png', 'application/pdf'];
    if (!allowedTypes.includes(file.type)) {
      this.fileError.set('Selecciona un archivo JPG, PNG o PDF.');
      this.removeProof();
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      this.fileError.set('El archivo no debe superar los 5 MB.');
      this.removeProof();
      return;
    }

    this.fileError.set('');
    this.proofFile.set(file);
    this.proofPreview.set(null);
    if (file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = () => {
        if (this.proofFile() === file) this.proofPreview.set(String(reader.result));
      };
      reader.readAsDataURL(file);
    }
  }

  removeProof(): void {
    this.proofFile.set(null);
    this.proofPreview.set(null);
    const input = this.proofInput()?.nativeElement;
    if (input) input.value = '';
  }

  hasError(control: AbstractControl): boolean {
    return control.invalid && (control.touched || this.submitted());
  }

  submitOrder(): void {
    this.submitted.set(true);
    this.checkoutForm.markAllAsTouched();
    const items = this.items();
    const hasInvalidQuantity = items.some((item) =>
      item.cantidad < 1 || item.cantidad > item.stock,
    );
    if (
      this.checkoutForm.invalid
      || !this.paymentMethod()
      || !this.proofFile()
      || items.length === 0
      || hasInvalidQuantity
    ) {
      return;
    }

    const values = this.checkoutForm.getRawValue();
    const customer: DatosCliente = {
      nombreCompleto: values.fullName.trim(),
      celular: values.phone.trim(),
      correo: values.email.trim(),
      tipoEntrega: values.delivery === 'delivery' ? 'Delivery' : 'Recojo en clínica',
      direccion: values.address.trim(),
      referencia: values.reference.trim(),
      tipoComprobante: values.receipt === 'factura' ? 'Factura' : 'Boleta',
      dni: values.dni.trim(),
      ruc: values.ruc.trim(),
      razonSocial: values.businessName.trim(),
    };
    const order: PedidoTemporal = {
      codigo: this.purchases.createOrderCode(),
      fechaIso: new Date().toISOString(),
      cliente: customer,
      items: items.map((item) => ({
        id: item.id,
        name: item.nombre,
        price: item.precio,
        stock: item.stock,
        image: item.imagen,
        imageAlt: item.imageAlt,
        cantidad: item.cantidad,
        subtotal: item.precio * item.cantidad,
      })),
      subtotal: this.subtotal(),
      costoDelivery: this.deliveryCost(),
      total: this.total(),
      metodoPago: this.paymentMethod()!,
      numeroOperacion: values.operationNumber.trim(),
      comprobanteNombre: this.proofFile()!.name,
      estadoPago: 'Pago pendiente de validación',
    };
    this.purchases.saveOrder(order);
    this.cart.clear();
    void this.router.navigate(['/compra/confirmacion']);
  }
}
