import datetime
import hashlib
import secrets
import warnings
from decimal import Decimal
from io import BytesIO
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from PIL import Image
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.models.clinic import Producto
from app.models.purchase import PedidoWeb, DetallePedidoWeb
from app.models.user import TipoUsuario
from app.schemas.cashier import VentaCreate
from app.services.cashier_service import CashierService, CajaNoAbiertaError, ProductoNoDisponibleError, StockInsuficienteError, VentaInvalidaError

MAX_PROOF_BYTES = 5 * 1024 * 1024


def payment_config():
    settings = get_settings()
    methods = {}
    for name in ("yape", "plin"):
        holder = getattr(settings, f"purchase_{name}_holder")
        phone = getattr(settings, f"purchase_{name}_phone")
        qr = getattr(settings, f"purchase_{name}_qr_url")
        methods[name.capitalize()] = {"holder": holder, "phone": phone, "qrUrl": qr,
            "enabled": bool(holder and phone and qr),
            "instructions": "Paga el importe exacto y adjunta el comprobante. Caja verificará la operación."}
    return {"payment": methods, "deliveryCost": settings.purchase_delivery_cost,
            "whatsappNumber": settings.purchase_whatsapp_number,
            "confirmationMessage": "Tu pedido está registrado y pendiente de revisión por caja.",
            "maxProofBytes": MAX_PROOF_BYTES}


def validate_proof(content):
    if not content or len(content) > MAX_PROOF_BYTES:
        raise HTTPException(422, "El comprobante debe contener entre 1 byte y 5 MB")
    try:
        if content.startswith(b"%PDF-"):
            reader = PdfReader(BytesIO(content), strict=True)
            if reader.is_encrypted or not reader.pages:
                raise ValueError("PDF protegido o vacío")
            # No se aceptan documentos con contenido activo o adjuntos ejecutables.
            for value in reader.trailer["/Root"].keys():
                if value in ("/OpenAction", "/AA", "/Names"):
                    raise ValueError("PDF con contenido activo")
            for page in reader.pages:
                if page.get("/AA") or page.get("/Annots"):
                    raise ValueError("PDF con acciones o anotaciones")
            return "application/pdf", "pdf"
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as image:
                if image.format not in ("JPEG", "PNG"):
                    raise ValueError("Formato no admitido")
                image.verify()
                return ("image/jpeg", "jpg") if image.format == "JPEG" else ("image/png", "png")
    except Exception as exc:
        raise HTTPException(422, "Comprobante inválido: utiliza una imagen JPG/PNG o un PDF sin contenido activo") from exc


class PurchaseService:
    def __init__(self, db):
        self.db = db

    def get(self, order_id, user, lock=False):
        stmt = select(PedidoWeb).where(PedidoWeb.id == order_id)
        if user.tipo == TipoUsuario.CLIENTE:
            stmt = stmt.where(PedidoWeb.cliente_id == user.id)
        order = self.db.scalar(stmt.with_for_update().execution_options(populate_existing=True) if lock else stmt)
        if order is None:
            raise HTTPException(404, "Pedido no encontrado")
        return order

    def list(self, user, estado=None, codigo=None, fecha=None, pagina=1):
        stmt = select(PedidoWeb)
        if user.tipo == TipoUsuario.CLIENTE:
            stmt = stmt.where(PedidoWeb.cliente_id == user.id)
        if estado:
            stmt = stmt.where(PedidoWeb.estado_pedido == estado)
        if codigo:
            stmt = stmt.where(PedidoWeb.codigo_pedido.ilike(f"%{codigo}%"))
        if fecha:
            start = datetime.datetime.combine(fecha, datetime.time.min, ZoneInfo("America/Lima"))
            stmt = stmt.where(PedidoWeb.fecha_pedido >= start, PedidoWeb.fecha_pedido < start + datetime.timedelta(days=1))
        return [self.serialize(order) for order in self.db.scalars(stmt.order_by(PedidoWeb.id.desc()).offset((pagina - 1) * 20).limit(20)).all()]

    def create(self, user, data, content):
        mime, extension = validate_proof(content)
        fingerprint = hashlib.sha256(data.model_dump_json().encode() + content).hexdigest()
        key = str(data.clave_idempotencia)

        def existing():
            previous = self.db.scalar(select(PedidoWeb).where(PedidoWeb.clave_idempotencia == key))
            if previous and (previous.cliente_id != user.id or previous.solicitud_hash != fingerprint):
                raise HTTPException(409, "La clave de solicitud ya fue utilizada con otros datos")
            return previous

        previous = existing()
        if previous:
            return self.serialize(previous)
        if not payment_config()["payment"][data.metodo_pago.capitalize()]["enabled"]:
            raise HTTPException(409, "Este método de pago todavía no está configurado por la clínica")
        quantities = {}
        for item in data.items:
            quantities[item.producto_id] = quantities.get(item.producto_id, 0) + item.cantidad
        products = self.db.scalars(select(Producto).where(Producto.id.in_(quantities), Producto.activo).order_by(Producto.id)).all()
        if len(products) != len(quantities):
            raise HTTPException(409, "Uno de los productos ya no está disponible")
        details = []
        for product in products:
            quantity = quantities[product.id]
            if quantity > 100 or product.stock_actual < quantity:
                raise HTTPException(409, f"Stock insuficiente para {product.nombre}")
            details.append(DetallePedidoWeb(producto_id=product.id, nombre_producto=product.nombre,
                imagen_url=product.imagen_url, cantidad=quantity, precio_unitario=product.precio_venta,
                subtotal=product.precio_venta * quantity))
        subtotal = sum((d.subtotal for d in details), Decimal("0.00"))
        shipping = get_settings().purchase_delivery_cost if data.cliente.tipoEntrega == "Delivery" else Decimal("0.00")
        total = subtotal + shipping
        if total != data.total_esperado:
            raise HTTPException(409, "Los importes cambiaron. Actualiza el carrito y comprueba el importe antes de pagar")
        order = PedidoWeb(codigo_pedido=f"PED-{secrets.token_hex(8).upper()}", cliente_id=user.id,
            subtotal=subtotal, total=total, costo_delivery=shipping, metodo_pago=data.metodo_pago,
            datos_cliente=data.cliente.model_dump(), numero_operacion=data.numero_operacion,
            observaciones=data.observaciones, comprobante_pago=f"comprobante-{secrets.token_hex(12)}.{extension}",
            comprobante_tipo=mime, comprobante_contenido=content, clave_idempotencia=key,
            solicitud_hash=fingerprint, detalles=details)
        try:
            self.db.add(order)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            previous = existing()
            if previous:
                return self.serialize(previous)
            raise
        return self.serialize(order)

    def review(self, user, order_id, data):
        try:
            order = self.get(order_id, user, lock=True)
            if order.estado_pedido != "PENDIENTE":
                raise HTTPException(409, "El pedido ya fue revisado o cancelado")
            if data.accion == "RECHAZAR":
                order.estado_pedido = "RECHAZADO"
                order.estado_pago = "RECHAZADO"
                order.motivo_rechazo = data.motivo
            else:
                # Caja bloquea primero su registro y después los productos en orden
                # estable; también revalida los precios bajo esos mismos bloqueos.
                sale = CashierService(self.db)._create_sale(user, VentaCreate(
                    cliente_id=order.cliente_id, cliente_dni=order.datos_cliente.get("dni") or None,
                    medio_pago=order.metodo_pago, clave_idempotencia=f"pedido-web-{order.id}",
                    items=[{"producto_id": d.producto_id, "cantidad": d.cantidad} for d in order.detalles]),
                    commit=False, costo_delivery=order.costo_delivery,
                    expected_prices={d.producto_id: d.precio_unitario for d in order.detalles})
                if sale.total != order.total:
                    raise HTTPException(409, "El importe de la venta no coincide con el pedido")
                order.venta_id = sale.orden_id
                order.estado_pedido = "APROBADO"
                order.estado_pago = "VALIDADO"
            order.fecha_revision = datetime.datetime.now(datetime.timezone.utc)
            order.usuario_revisor_id = user.id
            self.db.commit()
            return self.serialize(order)
        except CajaNoAbiertaError as exc:
            self.db.rollback()
            raise HTTPException(409, "Debes abrir una caja para aprobar el pedido") from exc
        except (ProductoNoDisponibleError, StockInsuficienteError, VentaInvalidaError) as exc:
            self.db.rollback()
            raise HTTPException(409, str(exc) or "No se puede registrar la venta: comprueba productos y stock suficiente") from exc
        except Exception:
            self.db.rollback()
            raise

    @staticmethod
    def serialize(order):
        fields = ("id", "codigo_pedido", "cliente_id", "fecha_pedido", "subtotal", "descuento", "costo_delivery", "total",
            "metodo_pago", "estado_pedido", "estado_pago", "datos_cliente", "numero_operacion", "observaciones",
            "comprobante_pago", "comprobante_tipo", "fecha_revision", "usuario_revisor_id", "motivo_rechazo", "venta_id")
        result = {field: getattr(order, field) for field in fields}
        result["detalles"] = [{field: getattr(d, field) for field in ("producto_id", "nombre_producto", "imagen_url", "cantidad", "precio_unitario", "subtotal")} for d in order.detalles]
        return result
