import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.clinic import Caja, ComprobanteVenta, DetalleOrdenCobro, EstadoPago, OrdenCobro, Producto
from app.models.user import Cajero, Cliente, Usuario

ZONE = ZoneInfo("America/Lima")


class SalesService:
    def __init__(self, db: Session):
        self.db = db

    def filtered(self, fecha_inicial=None, fecha_final=None, numero_venta=None, estado=None,
                 metodo_pago=None, cajero_id=None, producto_id=None):
        stmt = select(OrdenCobro).join(OrdenCobro.comprobante_venta)
        if fecha_inicial:
            stmt = stmt.where(ComprobanteVenta.fecha_emision >= datetime.datetime.combine(fecha_inicial, datetime.time.min, ZONE))
        if fecha_final:
            stmt = stmt.where(ComprobanteVenta.fecha_emision < datetime.datetime.combine(fecha_final + datetime.timedelta(days=1), datetime.time.min, ZONE))
        if numero_venta:
            stmt = stmt.where(OrdenCobro.codigo_orden.ilike(f"%{numero_venta}%"))
        if estado:
            stmt = stmt.where(OrdenCobro.estado_pago == {
                "PAGADA": EstadoPago.VALIDADO_CONFIRMADO,
                "ANULADA": EstadoPago.ANULADO,
                "PENDIENTE": EstadoPago.PENDIENTE,
            }[estado])
        if metodo_pago:
            stmt = stmt.where(OrdenCobro.medio_pago == metodo_pago)
        if cajero_id:
            stmt = stmt.where(OrdenCobro.cajero_id == cajero_id)
        if producto_id:
            stmt = stmt.where(OrdenCobro.detalles.any(DetalleOrdenCobro.producto_id == producto_id))
        return stmt

    def list(self, page=1, page_size=20, **filters):
        stmt = self.filtered(**filters)
        count = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        orders = self.db.scalars(stmt.options(
            selectinload(OrdenCobro.comprobante_venta),
            selectinload(OrdenCobro.cajero).selectinload(Cajero.usuario),
            selectinload(OrdenCobro.cliente).selectinload(Cliente.usuario),
        ).order_by(ComprobanteVenta.fecha_emision.desc(), OrdenCobro.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
        return {"total": count, "pagina": page, "tamano_pagina": page_size,
                "ventas": [self.serialize(order) for order in orders]}

    def summary(self, **filters):
        stmt = self.filtered(**filters).where(OrdenCobro.estado_pago == EstadoPago.VALIDADO_CONFIRMADO)
        ids = stmt.with_only_columns(OrdenCobro.id).subquery()
        count, total = self.db.execute(select(func.count(), func.coalesce(func.sum(OrdenCobro.monto_total), 0))
            .where(OrdenCobro.id.in_(select(ids.c.id)))).one()
        products = self.db.scalar(select(func.coalesce(func.sum(DetalleOrdenCobro.cantidad), 0))
            .where(DetalleOrdenCobro.orden_cobro_id.in_(select(ids.c.id)), DetalleOrdenCobro.producto_id.is_not(None)))
        return {"cantidad_ventas": count, "total_ventas": total,
                "ticket_promedio": (total / count).quantize(Decimal("0.01")) if count else Decimal("0.00"),
                "productos_vendidos": products or 0}

    def get(self, order_id):
        order = self.db.scalar(select(OrdenCobro).where(OrdenCobro.id == order_id)
            .join(OrdenCobro.comprobante_venta).options(
                selectinload(OrdenCobro.comprobante_venta),
                selectinload(OrdenCobro.cajero).selectinload(Cajero.usuario),
                selectinload(OrdenCobro.cliente).selectinload(Cliente.usuario),
                selectinload(OrdenCobro.detalles).selectinload(DetalleOrdenCobro.producto),
                selectinload(OrdenCobro.detalles).selectinload(DetalleOrdenCobro.servicio)))
        if order is None:
            raise LookupError("Venta no encontrada")
        return self.serialize(order, details=True)

    def void(self, order_id):
        try:
            order = self.db.scalar(select(OrdenCobro).where(OrdenCobro.id == order_id).with_for_update())
            if order is None or order.comprobante_venta is None:
                raise LookupError("Venta no encontrada")
            if order.estado_pago != EstadoPago.VALIDADO_CONFIRMADO:
                raise ValueError("Solo se puede anular una venta pagada")
            register = self.db.scalar(select(Caja).where(Caja.id == order.caja_id).with_for_update())
            for detail in sorted(order.detalles, key=lambda item: item.producto_id or 0):
                if detail.producto_id is not None:
                    product = self.db.scalar(select(Producto).where(Producto.id == detail.producto_id).with_for_update())
                    product.stock_actual += detail.cantidad
            register.total_ingresos_validados -= order.monto_total
            order.estado_pago = EstadoPago.ANULADO
            self.db.commit()
            return self.get(order_id)
        except Exception:
            self.db.rollback()
            raise

    @staticmethod
    def serialize(order, details=False):
        result = {"id": order.id, "codigo_orden": order.codigo_orden,
                  "fecha_emision": order.comprobante_venta.fecha_emision,
                  "cajero_id": order.cajero_id, "cajero_nombre": order.cajero.usuario.nombre,
                  "cliente_nombre": order.cliente.usuario.nombre if order.cliente else None,
                  "medio_pago": order.medio_pago, "subtotal": order.subtotal,
                  "descuento": order.descuento, "impuesto": order.impuesto,
                  "total": order.monto_total,
                  "estado": {EstadoPago.VALIDADO_CONFIRMADO: "PAGADA", EstadoPago.ANULADO: "ANULADA"}.get(order.estado_pago, "PENDIENTE")}
        if details:
            result["detalles"] = [{"producto_id": d.producto_id, "servicio_id": d.servicio_id,
                                    "nombre": d.producto.nombre if d.producto else d.servicio.nombre,
                                    "cantidad": d.cantidad, "precio_unitario": d.precio_unitario,
                                    "subtotal": d.subtotal} for d in order.detalles]
        return result
