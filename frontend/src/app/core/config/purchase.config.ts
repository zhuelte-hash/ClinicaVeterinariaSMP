import { MetodoPago } from '../models/purchase.model';

export interface PurchaseConfig {
  whatsappNumber: string;
  deliveryCost: number | string;
  maxProofBytes: number;
  confirmationMessage: string;
  payment: Record<MetodoPago, { holder: string; phone: string; qrUrl: string; enabled: boolean; instructions: string }>;
}

// Datos públicos suministrados por /pedidos-web/configuracion. Configurar PURCHASE_*
// en el backend; nunca colocar credenciales ni datos bancarios ficticios aquí.
export const PURCHASE_CONFIG: PurchaseConfig = {
  whatsappNumber: '', deliveryCost: 0, maxProofBytes: 5 * 1024 * 1024,
  confirmationMessage: 'Tu pedido está registrado y pendiente de revisión por caja.',
  payment: {
    Yape: { holder: '', phone: '', qrUrl: '', enabled: false, instructions: '' },
    Plin: { holder: '', phone: '', qrUrl: '', enabled: false, instructions: '' },
  },
};
