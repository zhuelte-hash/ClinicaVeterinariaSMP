export interface CashRegister {
  id: number;
  cajero_id: number;
  fondo_inicial: string;
  total_ingresos_validados: string;
  estado_caja: 'abierta' | 'cerrada';
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
  cliente_nombre: string;
  cliente_correo: string;
  cajero_nombre: string;
  medio_pago: string;
  subtotal: string;
  igv: string;
  total: string;
  detalles: ReceiptDetail[];
}
