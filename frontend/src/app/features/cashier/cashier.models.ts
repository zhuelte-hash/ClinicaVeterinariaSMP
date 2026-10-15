export interface CashRegister {
  id: number;
  cajero_id: number;
  fondo_inicial: string;
  total_ingresos_validados: string;
  estado_caja: 'abierta' | 'cerrada';
  fecha_apertura: string;
  fecha_cierre: string | null;
  efectivo_contado: string | null;
  diferencia: string | null;
}

export interface CashierOrder {
  id: number;
  codigo_orden: string;
  monto_total: string;
  estado_pago: 'pendiente' | 'pago_enviado' | 'validado_confirmado' | 'anulado';
}

export interface CashierSummary {
  caja: CashRegister | null;
  ordenes_pendientes: number;
  ordenes_validadas: number;
  ordenes_recientes: CashierOrder[];
  ingresos_efectivo: string;
  ingresos_digitales: string;
  efectivo_esperado: string;
}

export interface CashierCategory {
  id: number;
  nombre: string;
}

export interface CashierProduct {
  id: number;
  sku: string;
  nombre: string;
  precio_venta: string;
  stock_actual: number;
  categoria: CashierCategory;
}

export interface CashierClient {
  id: number;
  nombre: string;
  correo: string;
  telefono: string | null;
}

export interface CashierService {
  id: number;
  codigo: string;
  nombre: string;
  descripcion: string | null;
  precio_referencial: string;
  duracion_estimada_min: number;
}

export interface ReceiptDetail {
  producto_id: number | null;
  servicio_id: number | null;
  codigo: string;
  tipo: 'producto' | 'servicio';
  nombre: string;
  cantidad: number;
  precio_unitario: string;
  subtotal: string;
}

export interface Receipt {
  orden_id: number;
  codigo_orden: string;
  serie_correlativo: string;
  fecha_emision: string;
  cliente_nombre: string | null;
  cliente_correo: string | null;
  cajero_nombre: string;
  medio_pago: string;
  subtotal: string;
  igv: string;
  total: string;
  descuento: string;
  estado: 'PAGADA' | 'ANULADA';
  detalles: ReceiptDetail[];
  pagos: { medio: string; monto: string }[];
  efectivo_recibido: string | null;
  vuelto: string;
  proceso_atencion_id: number | null;
}

export interface CashierPendingPayment extends CashierOrder {
  captura_imagen: string | null;
  codigo_operacion: string | null;
}

export interface CashierAttention {
  id: number;
  mascota_nombre: string;
  servicio_nombre: string;
  cliente_id: number;
}
