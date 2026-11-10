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
import { DatosCliente, MetodoPago } from '../../core/models/purchase.model';
import { LocalPurchaseService } from '../../core/services/local-purchase.service';
import { AuthService } from '../../core/auth/auth.service';
import { finalize } from 'rxjs';
import { CartService } from '../../services/cart.service';
import { PublicProductsService } from '../../core/services/public-products.service';

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
  private readonly session = inject(AuthService);
  readonly cart = inject(CartService);
  readonly catalog = inject(PublicProductsService);
  constructor() {
    this.catalog.load();
    this.purchases.configuration().subscribe({
      next: config => { this.config.set(config); this.configLoaded.set(true); },
      error: () => this.fileError.set('No se pudo cargar la configuración de pagos. Recarga la página.'),
    });
  }
  private readonly proofInput = viewChild<ElementRef<HTMLInputElement>>('proofInput');

  readonly items = this.cart.items;
  readonly deliveryType = signal<DeliveryOption>('pickup');
  readonly receiptType = signal<ReceiptOption>('boleta');
  readonly paymentMethod = signal<MetodoPago | null>(null);
  readonly paymentMethods: MetodoPago[] = ['Yape', 'Plin'];
  readonly config = signal(PURCHASE_CONFIG);
  readonly configLoaded = signal(false);
  readonly sending = signal(false);
  private requestKey: string = crypto.randomUUID();
  private requestHash = '';
  readonly paymentConfig = computed(() => {
    const method = this.paymentMethod();
    return method ? this.config().payment[method] : null;
  });
  readonly proofFile = signal<File | null>(null);
  readonly proofPreview = signal<string | null>(null);
  readonly fileError = signal('');
  readonly submitted = signal(false);
  readonly subtotal = this.cart.total;
  readonly deliveryCost = computed(() =>
    this.deliveryType() === 'delivery' ? Number(this.config().deliveryCost) : 0,
  );
  readonly total = computed(() => this.subtotal() + this.deliveryCost());

  readonly checkoutForm = this.formBuilder.nonNullable.group({
    fullName: [
      this.session.currentUser()?.nombre ?? '',
      [Validators.required, Validators.minLength(3), Validators.pattern(/\S/)],
    ],
    phone: [this.session.currentUser()?.telefono ?? '', [Validators.required, Validators.pattern(/^\d{9,15}$/)]],
    email: [this.session.currentUser()?.correo ?? '', Validators.email],
    observations: [''],
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
    if (!this.config().payment[method].enabled) return;
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
    if (file.size > this.config().maxProofBytes) {
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

  async submitOrder(): Promise<void> {
    if (this.sending()) return;
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
      || this.catalog.loading()
      || !!this.catalog.error()
      || !this.configLoaded()
      || !this.paymentConfig()?.enabled
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
    const order = {
      clave_idempotencia: this.requestKey,
      cliente: customer,
      items: items.map((item) => ({
        producto_id: Number(item.id),
        cantidad: item.cantidad,
      })),
      total_esperado: this.total().toFixed(2),
      metodo_pago: this.paymentMethod()!.toLowerCase(),
      numero_operacion: values.operationNumber.trim(),
      observaciones: values.observations.trim(),
    };
    const file = this.proofFile()!;
    this.sending.set(true);
    this.fileError.set('');
    // Solo se conserva la clave de reintento y una huella, nunca el pedido ni el
    // archivo. Así un error de red o una recarga no duplica una solicitud idéntica.
    try {
      const fileHash = await crypto.subtle.digest('SHA-256', await file.arrayBuffer());
      const bytes = new TextEncoder().encode(JSON.stringify({ ...order, clave_idempotencia: '',
        user: this.session.currentUser()?.id, proof: Array.from(new Uint8Array(fileHash)) }));
      const digest = await crypto.subtle.digest('SHA-256', bytes);
      const hash = Array.from(new Uint8Array(digest)).map(value => value.toString(16).padStart(2, '0')).join('');
      if (this.requestHash !== hash) this.requestKey = crypto.randomUUID();
      this.requestHash = hash;
      const storageKey = `purchase_retry_${hash}`;
      try {
        this.requestKey = sessionStorage.getItem(storageKey) || this.requestKey;
        sessionStorage.setItem(storageKey, this.requestKey);
      } catch { /* La API sigue protegiendo los reintentos de esta sesión. */ }
      order.clave_idempotencia = this.requestKey;
    } catch {
      this.sending.set(false);
      this.fileError.set('No se pudo preparar el comprobante. Utiliza HTTPS o localhost y vuelve a intentarlo.');
      return;
    }
    this.purchases.create(order, file).pipe(finalize(() => this.sending.set(false))).subscribe({
      next: saved => {
        this.cart.clear();
        void this.router.navigate(['/compra/confirmacion'], { queryParams: { pedido: saved.id } });
      },
      error: error => this.fileError.set(typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudo registrar el pedido. Puedes reintentar sin duplicarlo.'),
    });
  }
}
