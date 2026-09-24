export type MetodoPago = 'Yape' | 'Plin';
export type TipoEntrega = 'Recojo en clínica' | 'Delivery';
export type TipoComprobante = 'Boleta' | 'Factura';

export interface PurchaseProduct {
  id: string;
  name: string;
  price: number;
  stock: number;
  image: string;
  imageAlt: string;
}

export interface DatosCliente {
  nombreCompleto: string;
  celular: string;
  correo: string;
  tipoEntrega: TipoEntrega;
  direccion: string;
  referencia: string;
  tipoComprobante: TipoComprobante;
  dni: string;
  ruc: string;
  razonSocial: string;
}

export interface PurchaseOrderItem extends PurchaseProduct {
  cantidad: number;
  subtotal: number;
}

export interface PedidoTemporal {
  codigo: string;
  fechaIso: string;
  cliente: DatosCliente;
  items: PurchaseOrderItem[];
  subtotal: number;
  costoDelivery: number;
  total: number;
  metodoPago: MetodoPago;
  numeroOperacion: string;
  comprobanteNombre: string;
  estadoPago: 'Pago pendiente de validación';
}
