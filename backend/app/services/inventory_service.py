import datetime as dt
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select

from app.models.clinic import ConfiguracionClinica, Notificacion, Producto, Proveedor
from app.models.operations import CompraProveedor, Egreso, LoteInventario, MovimientoInventario, UnidadMedida
from app.models.user import TipoUsuario, Usuario
from app.services.operation_utils import branch_id, row_data
from app.services.messaging_service import MessagingService


class InventoryService:
    def __init__(self, db):
        self.db = db

    def product(self, product_id):
        item = self.db.scalar(select(Producto).where(Producto.id == product_id, Producto.sucursal_id == branch_id(self.db)).with_for_update())
        if item is None:
            raise HTTPException(404, "Producto no encontrado en esta sede")
        return item

    @staticmethod
    def validate_quantity(product, quantity):
        quantity = Decimal(str(quantity))
        if quantity <= 0 or (not product.fraccionable and quantity != quantity.to_integral_value()):
            raise HTTPException(422, "La cantidad debe ser positiva y respetar la unidad del producto")
        return quantity

    def initialize_lots(self, product):
        if product.stock_actual > 0 and self.db.scalar(select(LoteInventario.id).where(LoteInventario.producto_id == product.id).limit(1)) is None:
            self.db.add(LoteInventario(producto_id=product.id, codigo="SALDO-INICIAL", cantidad=product.stock_actual, costo_unitario=product.costo_unitario))
            self.db.flush()

    def movement(self, product, quantity, previous, kind, reason, reference=None, lot=None, cost=None, actor=None):
        self.db.add(MovimientoInventario(producto_id=product.id, lote_id=lot.id if lot else None, usuario_id=actor or self.db.info.get("actor_id"), tipo=kind, cantidad=quantity, saldo_anterior=previous, saldo_nuevo=previous + quantity, costo_unitario=cost if cost is not None else product.costo_unitario, motivo=reason, referencia=reference))

    def consume(self, product, quantity, reference, *, physical_adjustment=False, reason="Venta", actor=None):
        quantity = self.validate_quantity(product, quantity)
        self.initialize_lots(product)
        lots_query = select(LoteInventario).where(LoteInventario.producto_id == product.id, LoteInventario.cantidad > 0)
        if not physical_adjustment:
            lots_query = lots_query.where((LoteInventario.vencimiento.is_(None)) | (LoteInventario.vencimiento >= dt.date.today()))
        lots = list(self.db.scalars(lots_query.order_by(LoteInventario.vencimiento.asc().nulls_last(), LoteInventario.id).with_for_update()).all())
        if sum((lot.cantidad for lot in lots), Decimal(0)) < quantity:
            raise HTTPException(409, "No hay stock vendible suficiente; revisa lotes vencidos y disponibilidad")
        remaining = quantity
        for lot in lots:
            taken = min(lot.cantidad, remaining)
            before = product.stock_actual
            product.stock_actual -= taken
            lot.cantidad -= taken
            self.movement(product, -taken, before, "ajuste" if physical_adjustment else "venta", reason, reference, lot, lot.costo_unitario, actor)
            remaining -= taken
            if remaining == 0:
                break
        self.stock_alert(product)

    def increase(self, product, quantity, reason, kind="ajuste", lot_code=None, expiry=None, cost=None, reference=None, actor=None):
        quantity = self.validate_quantity(product, quantity)
        self.initialize_lots(product)
        code = lot_code or f"AJUSTE-{uuid4().hex[:12]}"
        lot = self.db.scalar(select(LoteInventario).where(LoteInventario.producto_id == product.id, LoteInventario.codigo == code).with_for_update())
        price = Decimal(str(cost if cost is not None else product.costo_unitario))
        if lot and (lot.vencimiento != expiry or lot.costo_unitario != price):
            raise HTTPException(409, "El lote existente tiene un vencimiento o costo diferente")
        if lot is None:
            lot = LoteInventario(producto_id=product.id, codigo=code, cantidad=0, costo_unitario=price, vencimiento=expiry)
            self.db.add(lot); self.db.flush()
        before = product.stock_actual
        product.costo_unitario = ((before * product.costo_unitario + quantity * price) / (before + quantity)).quantize(Decimal("0.0001"))
        product.stock_actual += quantity
        lot.cantidad += quantity
        self.movement(product, quantity, before, kind, reason, reference, lot, price, actor)
        self.stock_alert(product)

    def receive(self, user, data):
        if self.db.get(Proveedor, data.proveedor_id) is None:
            raise HTTPException(422, "Proveedor no encontrado")
        if self.db.scalar(select(CompraProveedor.id).where(CompraProveedor.proveedor_id == data.proveedor_id, CompraProveedor.documento == data.documento)):
            raise HTTPException(409, "Este documento del proveedor ya fue recibido")
        total = Decimal(0)
        for line in sorted(data.detalles, key=lambda item: item.producto_id):
            product = self.product(line.producto_id)
            if not product.activo or (line.vencimiento and line.vencimiento < dt.date.today()):
                raise HTTPException(422, "No recibas productos inactivos ni lotes vencidos")
            quantity = line.cantidad
            cost = line.costo_unitario
            if line.unidad and line.unidad != product.unidad_medida:
                source, target = self.db.get(UnidadMedida, line.unidad), self.db.get(UnidadMedida, product.unidad_medida)
                if source is None or target is None or source.dimension != target.dimension:
                    raise HTTPException(422, "Las unidades no son compatibles")
                factor = source.factor_base / target.factor_base
                quantity, cost = quantity * factor, cost / factor
            if quantity != quantity.quantize(Decimal("0.001")):
                raise HTTPException(422, "La conversión requiere más de tres decimales")
            self.increase(product, quantity, f"Recepción {data.documento}", "compra", line.lote, line.vencimiento, cost, data.documento, user.id)
            total += line.cantidad * line.costo_unitario
        purchase = CompraProveedor(proveedor_id=data.proveedor_id, usuario_id=user.id, sucursal_id=branch_id(self.db), documento=data.documento, total=total.quantize(Decimal("0.01")), detalles=data.model_dump(mode="json")["detalles"])
        self.db.add(purchase); self.db.flush()
        if total > 0:
            self.db.add(Egreso(usuario_id=user.id, sucursal_id=branch_id(self.db), categoria="Mercadería", concepto=f"Compra {data.documento}", monto=purchase.total, fecha=dt.date.today(), compra_id=purchase.id))
        self.db.commit()
        return {**row_data(purchase), "documento": purchase.documento}

    def reverse_sale(self, order, actor):
        for detail in order.detalles:
            if detail.producto_id is None:
                continue
            product = self.product(detail.producto_id)
            movements = self.db.scalars(select(MovimientoInventario).where(MovimientoInventario.producto_id == product.id, MovimientoInventario.referencia == order.codigo_orden, MovimientoInventario.tipo == "venta")).all()
            if not movements:
                self.increase(product, detail.cantidad, "Anulación de venta histórica", "devolucion", reference=order.codigo_orden, actor=actor)
            for movement in movements:
                lot = self.db.get(LoteInventario, movement.lote_id)
                previous = product.stock_actual
                product.stock_actual -= movement.cantidad
                lot.cantidad -= movement.cantidad
                self.movement(product, -movement.cantidad, previous, "devolucion", order.motivo_anulacion or "Anulación", order.codigo_orden, lot, movement.costo_unitario, actor)
            self.stock_alert(product)

    def stock_alert(self, product):
        low = product.stock_actual <= product.stock_minimo
        if not low:
            product.alerta_stock_activa = False
            return
        if product.alerta_stock_activa:
            return
        settings = self.db.scalar(select(ConfiguracionClinica).order_by(ConfiguracionClinica.id))
        if settings and not settings.alertas_stock:
            return
        product.alerta_stock_activa = True
        for admin in self.db.scalars(select(Usuario).where(Usuario.tipo == TipoUsuario.ADMINISTRADOR, Usuario.activo)).all():
            self.db.add(Notificacion(usuario_id=admin.id, tipo="stock_bajo", titulo="Reabastecimiento necesario", mensaje=f"{product.nombre}: stock {product.stock_actual}; mínimo {product.stock_minimo}."))
            MessagingService(self.db).to_user(admin, "stock_bajo", f"stock:{product.id}:{uuid4().hex}:{admin.id}", {"producto": product.nombre, "cantidad": product.stock_actual, "minimo": product.stock_minimo})

    def kardex(self, product_id):
        self.product(product_id)
        return [row_data(row) for row in self.db.scalars(select(MovimientoInventario).where(MovimientoInventario.producto_id == product_id).order_by(MovimientoInventario.id.desc())).all()]

    def valuation(self):
        products = self.db.scalars(select(Producto).where(Producto.sucursal_id == branch_id(self.db), Producto.activo)).all()
        rows = [{"id": p.id, "producto": p.nombre, "cantidad": p.stock_actual, "unidad": p.unidad_medida, "costo": p.costo_unitario, "valor": (p.stock_actual * p.costo_unitario).quantize(Decimal("0.01")), "costo_pendiente": p.costo_unitario == 0 and p.stock_actual > 0} for p in products]
        return {"metodo": "Costo promedio ponderado móvil", "total": sum((row["valor"] for row in rows), Decimal(0)), "productos": rows}
