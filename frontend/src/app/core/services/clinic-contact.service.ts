import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { environment } from '../../../environments/environment';

interface ClinicContact { telefono: string; telefono_mostrado: string; internacional: string; whatsapp: string; modo_whatsapp?: 'manual' | 'meta' | 'twilio'; }

@Injectable({ providedIn: 'root' })
export class ClinicContactService {
  private readonly http = inject(HttpClient);
  readonly contact = signal<ClinicContact>({ telefono: '938304590', telefono_mostrado: '938 304 590', internacional: '51938304590', whatsapp: '51938304590', modo_whatsapp: 'manual' });
  readonly displayPhone = computed(() => this.contact().telefono_mostrado);
  readonly telUrl = computed(() => this.contact().internacional ? `tel:+${this.contact().internacional}` : '');
  constructor() { this.refresh(); }
  refresh(): void {
    this.http.get<ClinicContact>(`${environment.apiUrl}/publico/contacto`).subscribe({ next: contact => { if (contact && typeof contact.telefono === 'string') this.contact.set(contact); }, error: () => {} });
  }
  whatsappUrl(message: string): string { const phone = this.contact().whatsapp; return phone ? `https://wa.me/${phone}?text=${encodeURIComponent(message)}` : ''; }
}
