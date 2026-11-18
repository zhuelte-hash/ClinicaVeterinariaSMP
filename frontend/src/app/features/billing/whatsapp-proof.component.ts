import { HttpClient } from '@angular/common/http';
import { Component, effect, inject, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { environment } from '../../../environments/environment';
import { apiError } from './billing-api.service';

interface ProofInstructions { whatsapp_url: string; leyenda: string; telefono_remitente: string; instrucciones: string; }

@Component({ selector: 'app-whatsapp-proof', standalone: true, imports: [FormsModule], styleUrl: '../admin/shared/admin-ui.css', template: `
  <section class="grid gap-3 rounded-xl border border-teal-200 p-4" aria-labelledby="whatsapp-proof-title">
    <h3 id="whatsapp-proof-title" class="font-bold">Enviar comprobante por WhatsApp</h3>
    <p class="text-sm">Prepara la leyenda para asociar el archivo a esta orden. Debes adjuntar el comprobante en WhatsApp; abrir el enlace no envía el archivo ni confirma el pago.</p>
    @if (error()) { <p role="alert" class="text-rose-700">{{ error() }}</p> }
    <form class="grid gap-3 sm:grid-cols-2" #form="ngForm" (ngSubmit)="form.valid && prepare()">
      <label>Monto para WhatsApp (S/)<input class="admin-input" type="number" min="0.01" step="0.01" [max]="balance()" required name="amount" [(ngModel)]="amount" (ngModelChange)="invalidate()" [disabled]="busy()"></label>
      <label>Medio para WhatsApp<select class="admin-input" name="method" [(ngModel)]="method" (ngModelChange)="invalidate()" [disabled]="busy()"><option value="yape">Yape</option><option value="plin">Plin</option><option value="transferencia">Transferencia</option><option value="tarjeta">Tarjeta</option></select></label>
      <label>Código de operación para WhatsApp<input class="admin-input" name="operation" maxlength="100" pattern="[A-Za-z0-9-]*" [(ngModel)]="operation" (ngModelChange)="invalidate()" [disabled]="busy()"></label>
      <button class="admin-secondary self-end" [disabled]="busy() || form.invalid">Preparar envío de comprobante</button>
    </form>
    @if (result(); as data) {
      <p class="text-sm">Envía desde el teléfono de tu perfil: <b>{{ data.telefono_remitente }}</b>.</p>
      <label>Leyenda para pegar en el archivo<textarea class="admin-input" rows="3" readonly [value]="data.leyenda"></textarea></label>
      <p class="text-sm">{{ data.instrucciones }}</p>
      <a class="font-bold text-teal-700" [href]="data.whatsapp_url" target="_blank" rel="noopener noreferrer">Abrir WhatsApp para adjuntar comprobante</a>
    }
  </section>
` })
export class WhatsAppProofComponent {
  readonly orderId = input.required<number>(); readonly balance = input.required<number>();
  private readonly http = inject(HttpClient);
  readonly result = signal<ProofInstructions | null>(null); readonly error = signal(''); readonly busy = signal(false);
  amount = ''; method = 'yape'; operation = ''; private version = 0;
  constructor() { effect(() => { this.orderId(); const balance = this.balance(); this.amount = Number(balance).toFixed(2); this.result.set(null); this.error.set(''); this.version++; }); }
  invalidate() { this.version++; this.result.set(null); }
  prepare() {
    if (this.busy()) return;
    const version = this.version;
    this.busy.set(true); this.error.set(''); this.result.set(null);
    this.http.post<ProofInstructions>(`${environment.apiUrl}/operaciones/ordenes/${this.orderId()}/preparar-whatsapp`, { monto: this.amount, medio: this.method, codigo_operacion: this.operation.trim() || null }).pipe(finalize(() => this.busy.set(false))).subscribe({ next: data => { if (version === this.version) this.result.set(data); }, error: error => { if (version === this.version) this.error.set(apiError(error)); } });
  }
}
