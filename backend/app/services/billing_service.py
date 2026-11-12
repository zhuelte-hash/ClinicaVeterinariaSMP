from collections import defaultdict
from decimal import Decimal
from uuid import uuid4
from hashlib import sha256
import datetime as dt

from fastapi import HTTPException
from sqlalchemy import func, select

from app.models.clinic import Caja, EstadoPago, OrdenCobro, Producto, ProcesoAtencion, Servicio
from app.models.operations import AbonoOrden, AutorizacionDescuento, EventoAuditoria, MovimientoCaja, OrdenPendiente
from app.models.user import Cliente, TipoUsuario, Usuario
from app.schemas.cashier import VentaCreate
from app.schemas.operations import OrderItem, PendingOrderCreate
from app.services.cashier_service import CashierService, ProductoNoDisponibleError, StockInsuficienteError, VentaInvalidaError
from app.services.document_service import receipt_pdf, make_pdf
from app.services.messaging_service import MessagingService
from app.services.operation_utils import branch_id, row_data
from app.services.purchase_service import validate_proof
from app.services.policy_service import ZONE


class BillingService:
    def __init__(self, db):
        self.db = db

    def get(self, order_id, user, lock=False):
        statement = select(OrdenPendiente).where(OrdenPendiente.id == order_id)
        if user.tipo == TipoUsuario.CLIENTE:
            statement = statement.where(OrdenPendiente.cliente_id == user.id)
        else:
            statement = statement.where(OrdenPendiente.sucursal_id == branch_id(self.db))
        order = self.db.scalar(statement.with_for_update().execution_options(populate_existing=True) if lock else statement)
        if order is None:
            raise HTTPException(404, "Orden no encontrada")
        return order

    def serialize(self, order, history=False):
        payments = self.db.scalars(select(AbonoOrden).where(AbonoOrden.orden_id == order.id).order_by(AbonoOrden.id)).all()
        paid = sum((payment.monto for payment in payments if payment.estado == "validado"), Decimal(0))
        sale = self.db.scalar(select(OrdenCobro).where(OrdenCobro.preorden_id == order.id))
        client = self.db.get(Usuario, order.cliente_id)
        result = {**row_data(order), "cliente_nombre": client.nombre, "creador_nombre": self.db.get(Usuario, order.creador_id).nombre,
                  "abonado": paid, "saldo": order.total - paid, "venta_id": sale.id if sale else None,
                  "sin_comprobante": not any(p.comprobante and p.estado != "rechazado" for p in payments),
                  "abonos": [{**row_data(p), "registrado_por_nombre": self.db.get(Usuario, p.registrado_por).nombre,
                               "validado_por_nombre": self.db.get(Usuario, p.validado_por).nombre if p.validado_por else None,
                               "tiene_comprobante": bool(p.comprobante)} for p in payments]}
        if history:
            events = self.db.scalars(select(EventoAuditoria).where(EventoAuditoria.entidad == "ordenes_pendientes", EventoAuditoria.registro_id == str(order.id)).order_by(EventoAuditoria.id)).all()
            result["historial"] = [{**row_data(event), "autor": self.db.get(Usuario, event.usuario_id).nombre if event.usuario_id else "Sistema"} for event in events]
        return result

    def list(self, user, start=None, end=None, state=None, without_proof=False):
        statement = select(OrdenPendiente)
        statement = statement.where(OrdenPendiente.cliente_id == user.id) if user.tipo == TipoUsuario.CLIENTE else statement.where(OrdenPendiente.sucursal_id == branch_id(self.db))
        if start:
            statement = statement.where(OrdenPendiente.fecha >= dt.datetime.combine(start, dt.time.min, ZONE).astimezone(dt.timezone.utc))
        if end:
            statement = statement.where(OrdenPendiente.fecha < dt.datetime.combine(end + dt.timedelta(days=1), dt.time.min, ZONE).astimezone(dt.timezone.utc))
        if state:
            statement = statement.where(OrdenPendiente.estado == state)
        rows = [self.serialize(order) for order in self.db.scalars(statement.order_by(OrdenPendiente.id.desc())).all()]
        return [row for row in rows if row["sin_comprobante"] and row["estado"] not in {"pagada", "anulada"}] if without_proof else rows

    def create(self, user, data, commit=True):
        self.db.info["actor_id"] = user.id
        def signature(items):
            quantities = defaultdict(lambda: Decimal(0))
            for item in items:
                quantities[(item.get("producto_id"), item.get("servicio_id"))] += Decimal(str(item["cantidad"]))
            return quantities
        previous = self.db.scalar(select(OrdenPendiente).where(OrdenPendiente.clave_idempotencia == data.clave_idempotencia))
        if previous:
            if (previous.creador_id != user.id or previous.cliente_id != data.cliente_id or previous.proceso_id != data.proceso_id
                    or previous.autorizacion_id != data.autorizacion_id or signature(previous.detalles) != signature([item.model_dump() for item in data.detalles])):
                raise HTTPException(409, "La clave ya corresponde a otra orden")
            return previous
        if self.db.get(Cliente, data.cliente_id) is None or (user.tipo == TipoUsuario.CLIENTE and user.id != data.cliente_id):
            raise HTTPException(422, "Cliente no válido")
        if data.proceso_id:
            process = self.db.get(ProcesoAtencion, data.proceso_id)
            if not process or process.mascota.cliente_id != data.cliente_id or (user.tipo == TipoUsuario.VETERINARIO and (not process.proceso_medico or process.proceso_medico.veterinario_id != user.id)):
                raise HTTPException(403, "La atención no está asignada a este profesional y cliente")
            if self.db.scalar(select(OrdenPendiente.id).where(OrdenPendiente.proceso_id == data.proceso_id)) or self.db.scalar(select(OrdenCobro.id).where(OrdenCobro.proceso_atencion_id == data.proceso_id, OrdenCobro.estado_pago == EstadoPago.VALIDADO_CONFIRMADO)):
                raise HTTPException(409, "Esta atención ya tiene una orden de cobro o una venta pagada")
        details, total = [], Decimal(0)
        for (product_id, service_id), quantity in signature([item.model_dump() for item in data.detalles]).items():
            item = OrderItem(producto_id=product_id, servicio_id=service_id, cantidad=quantity)
            product = self.db.get(Producto, item.producto_id) if item.producto_id else None
            service = self.db.get(Servicio, item.servicio_id) if item.servicio_id else None
            target = product or service
            if target is None or not target.activo or (product and product.sucursal_id != branch_id(self.db)):
                raise HTTPException(422, "El artículo no está disponible en esta sede")
            if (product and not product.fraccionable or service) and item.cantidad != item.cantidad.to_integral_value():
                raise HTTPException(422, "El artículo no admite cantidades fraccionarias")
            if product and product.stock_actual < item.cantidad:
                raise HTTPException(409, f"Stock insuficiente para {product.nombre}")
            price = product.precio_venta if product else service.precio_referencial
            amount = (price * item.cantidad).quantize(Decimal("0.01"))
            total += amount
            details.append({"producto_id": item.producto_id, "servicio_id": item.servicio_id, "cantidad": str(item.cantidad), "nombre": target.nombre, "precio_unitario": str(price), "subtotal": str(amount)})
        discount = Decimal(0)
        if data.autorizacion_id:
            authorization = self.db.scalar(select(AutorizacionDescuento).where(AutorizacionDescuento.id == data.autorizacion_id).with_for_update())
            if not authorization or authorization.usada or authorization.estado != "aprobada" or authorization.solicitante_id != user.id or authorization.cliente_id != data.cliente_id:
                raise HTTPException(409, "Descuento no autorizado para esta orden")
            discount = authorization.monto
            authorization.usada = True
        if total <= discount:
            raise HTTPException(422, "El total debe ser positivo")
        order = OrdenPendiente(codigo=f"OC-{uuid4().hex[:12].upper()}", cliente_id=data.cliente_id, creador_id=user.id, sucursal_id=branch_id(self.db), proceso_id=data.proceso_id, detalles=details, total=total - discount, descuento=discount, autorizacion_id=data.autorizacion_id, clave_idempotencia=data.clave_idempotencia)
        self.db.add(order); self.db.flush()
        client = self.db.get(Usuario, order.cliente_id)
        MessagingService(self.db).to_user(client, "orden_creada", f"orden:{order.id}", {"nombre": client.nombre, "codigo": order.codigo, "total": order.total}, entity_id=order.id)
        if commit:
            self.db.commit()
        return order

    def from_attention(self, user, process):
        existing = self.db.scalar(select(OrdenPendiente).where(OrdenPendiente.proceso_id == process.id))
        if existing:
            return existing
        if not process.cita:
            return None
        items = [OrderItem(servicio_id=process.cita.servicio_id, cantidad=1)]
        if process.receta:
            items += [OrderItem(producto_id=item.producto_id, cantidad=item.cantidad_producto) for item in process.receta.detalles if item.producto_id and item.cantidad_producto]
        order = self.create(user, PendingOrderCreate(cliente_id=process.mascota.cliente_id, proceso_id=process.id, detalles=items, clave_idempotencia=f"atencion-{process.id}"), commit=False)
        if process.receta:
            client = process.mascota.cliente.usuario
            document = make_pdf("Receta veterinaria", [f"Paciente: {process.mascota.nombre}", f"Profesional: {user.nombre}", process.receta.indicaciones_generales or ""], [["Medicamento", "Dosis", "Vía", "Frecuencia", "Duración"]] + [[item.medicamento, item.dosis + " " + item.unidad, item.via, item.frecuencia, item.duracion] for item in process.receta.detalles])
            MessagingService(self.db).to_user(client, "receta", f"receta:{process.receta.id}", {"nombre": client.nombre, "mascota": process.mascota.nombre, "codigo": order.codigo}, document, "receta.pdf")
        return order

    def add_payment(self, user, order_id, data, content=None, commit=True):
        self.db.info["actor_id"] = user.id
        order = self.get(order_id, user, lock=True)
        existing = self.db.scalar(select(AbonoOrden).where(AbonoOrden.clave_idempotencia == data.clave_idempotencia))
        if existing:
            if (existing.orden_id != order_id or existing.monto != data.monto or existing.medio != data.medio
                    or existing.codigo_operacion != data.codigo_operacion or existing.canal != data.canal
                    or sha256(existing.comprobante or b"").digest() != sha256(content or b"").digest()):
                raise HTTPException(409, "La clave ya corresponde a otro abono")
            return self.serialize(order)
        if order.estado in {"anulada", "pagada"}:
            raise HTTPException(409, "La orden está finalizada")
        if data.monto > self.serialize(order)["saldo"]:
            raise HTTPException(422, "El abono supera el saldo pendiente")
        if user.tipo == TipoUsuario.CLIENTE and (not content or data.medio == "efectivo"):
            raise HTTPException(422, "Adjunta el comprobante de un pago digital")
        if (data.canal in {"web", "whatsapp"} and not content) or (content and data.medio == "efectivo"):
            raise HTTPException(422, "Los comprobantes corresponden a pagos digitales y requieren un archivo")
        media_type = validate_proof(content)[0] if content else None
        payment = AbonoOrden(orden_id=order.id, registrado_por=user.id, monto=data.monto, medio=data.medio, canal=data.canal, codigo_operacion=data.codigo_operacion, comprobante=content, comprobante_tipo=media_type, clave_idempotencia=data.clave_idempotencia)
        self.db.add(payment); self.db.flush()
        if user.tipo in {TipoUsuario.CAJERO, TipoUsuario.ADMINISTRADOR} and data.canal == "caja" and not content:
            self.validate_payment(user, payment.id, commit=False)
        if commit:
            self.db.commit()
        return self.serialize(order)

    def validate_payment(self, user, payment_id, commit=True):
        if user.tipo not in {TipoUsuario.CAJERO, TipoUsuario.ADMINISTRADOR}:
            raise HTTPException(403, "Solo caja o administración puede validar un pago")
        self.db.info["actor_id"] = user.id
        payment = self.db.scalar(select(AbonoOrden).where(AbonoOrden.id == payment_id).with_for_update())
        if payment is None:
            raise HTTPException(404, "Abono no encontrado")
        order = self.get(payment.orden_id, user, lock=True)
        if payment.estado == "validado":
            return self.serialize(order)
        if payment.estado != "enviado" or order.estado in {"anulada", "pagada"}:
            raise HTTPException(409, "Este abono no puede validarse")
        register = CashierService(self.db).get_open_register(user.id)
        if register is None:
            raise HTTPException(409, "Abre una caja en esta sede para registrar el ingreso")
        if payment.monto > self.serialize(order)["saldo"]:
            raise HTTPException(409, "El abono supera el saldo actualizado")
        payment.estado, payment.validado_por, payment.caja_id = "validado", user.id, register.id
        self.db.add(MovimientoCaja(caja_id=register.id, abono_id=payment.id, usuario_id=user.id, monto=payment.monto, medio=payment.medio, motivo=f"Abono de {order.codigo}"))
        register.total_ingresos_validados += payment.monto
        self.db.flush()
        balance = self.serialize(order)["saldo"]
        order.estado = "parcial" if balance else "pagada"
        if balance == 0:
            payments = self.db.scalars(select(AbonoOrden).where(AbonoOrden.orden_id == order.id, AbonoOrden.estado == "validado")).all()
            methods = defaultdict(lambda: Decimal(0))
            for row in payments:
                methods[row.medio] += row.monto
            payload = VentaCreate(cliente_id=order.cliente_id, items=[{"producto_id": row["producto_id"], "servicio_id": row["servicio_id"], "cantidad": row["cantidad"]} for row in order.detalles], descuento=order.descuento, autorizacion_descuento_id=order.autorizacion_id, medio_pago=next(iter(methods)), pagos=[{"medio": method, "monto": value} for method, value in methods.items()], proceso_atencion_id=order.proceso_id, clave_idempotencia=f"orden-pagada-{order.id}")
            try:
                receipt = CashierService(self.db)._create_sale(user, payload, commit=False, pre_order=order)
            except (ProductoNoDisponibleError, StockInsuficienteError, VentaInvalidaError) as exc:
                raise HTTPException(409, str(exc) or "El producto no está disponible o su stock es insuficiente; el pago no fue validado") from exc
            register.total_ingresos_validados -= order.total
            client = self.db.get(Usuario, order.cliente_id)
            MessagingService(self.db).to_user(client, "pago_validado", f"pago:{order.id}", {"nombre": client.nombre, "codigo": order.codigo}, receipt_pdf(receipt), f"{receipt.serie_correlativo}.pdf")
        if commit:
            self.db.commit()
        return self.serialize(order)

    def cancel(self, user, order_id, reason):
        self.db.info["actor_id"] = user.id
        order = self.get(order_id, user, lock=True)
        if order.estado == "anulada":
            return self.serialize(order)
        if self.serialize(order)["abonado"] > 0:
            raise HTTPException(409, "La orden tiene abonos; debe resolverse el reembolso antes de anularla")
        order.estado, order.motivo_anulacion = "anulada", reason
        for payment in self.db.scalars(select(AbonoOrden).where(AbonoOrden.orden_id == order.id, AbonoOrden.estado == "enviado")).all():
            payment.estado, payment.motivo, payment.validado_por = "rechazado", f"Orden anulada: {reason}"[:500], user.id
        self.db.commit()
        return self.serialize(order)
