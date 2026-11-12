import datetime as dt
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.clinic import Caja, Mascota, OrdenCobro, Producto, ProcesoAtencion, Servicio, ServicioMedico, ServicioEstetica
from app.models.purchase import PedidoWeb
from app.models.operations import AbonoOrden, AutorizacionDescuento, CompraProveedor, Egreso, LoteInventario, MensajeSalida, Sucursal, UnidadMedida
from app.models.user import TipoUsuario, Usuario
from app.schemas.operations import BranchWrite, ClinicPolicy, DiscountRequest, ExpenseWrite, InstallmentWrite, PendingOrderCreate, Reason, ReceivePurchase, ServiceWrite, TemplateWrite, UnitWrite
from app.security import check_permission, get_current_active_user, require_permission
from app.services.billing_service import BillingService
from app.services.cashier_service import CashierService
from app.services.document_service import receipt_pdf
from app.services.inventory_service import InventoryService
from app.services.messaging_service import MessagingService
from app.services.operation_utils import branch_id, row_data
from app.services.policy_service import PolicyService
from app.services.user_service import UserService
from app.services.sales_service import SalesService

router = APIRouter(tags=["Operaciones clínicas"])
Db = Annotated[Session, Depends(get_db)]
User = Annotated[Usuario, Depends(get_current_active_user)]
Admin = Annotated[Usuario, Depends(require_permission("usuarios"))]
InventoryAdmin = Annotated[Usuario, Depends(require_permission("inventario"))]
SalesAdmin = Annotated[Usuario, Depends(require_permission("ventas"))]


def staff(user, db, module="ventas", action="ver"):
    if user.tipo not in {TipoUsuario.CAJERO, TipoUsuario.VETERINARIO, TipoUsuario.ADMINISTRADOR}:
        raise HTTPException(403, "Esta acción corresponde al personal autorizado")
    check_permission(db, user, module, action)


def save(db, item):
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "El registro está duplicado o tiene datos asociados incompatibles") from exc
    db.refresh(item)
    return row_data(item)


@router.get("/publico/institucional")
def institutional(db: Db):
    return PolicyService(db).get()


@router.get("/publico/sucursales")
def public_branches(db: Db):
    return [row_data(row) for row in db.scalars(select(Sucursal).where(Sucursal.activa).order_by(Sucursal.id)).all()]


@router.get("/admin/operaciones/configuracion")
def configuration(db: Db, _user: Admin):
    return PolicyService(db).get()


@router.put("/admin/operaciones/configuracion")
def update_configuration(data: ClinicPolicy, db: Db, user: Admin):
    check_permission(db, user, "usuarios", "editar")
    return PolicyService(db).save(data)


@router.post("/admin/operaciones/instalaciones")
async def upload_installation(db: Db, user: Admin, archivo: UploadFile = File(...)):
    check_permission(db, user, "usuarios", "editar")
    from app.services.purchase_service import validate_proof
    content = await archivo.read(5 * 1024 * 1024 + 1)
    media, extension = validate_proof(content)
    if media == "application/pdf":
        raise HTTPException(422, "La galería necesita fotografías JPG o PNG")
    directory = Path(__file__).resolve().parents[2] / "uploads" / "instalaciones"
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}.{extension}"
    (directory / filename).write_bytes(content)
    return {"url": f"/uploads/instalaciones/{filename}"}


@router.get("/admin/operaciones/servicios")
def services(db: Db, user: Admin):
    check_permission(db, user, "citas")
    return [{**row_data(row), "tipo": "medica" if row.medico else "estetica", "tipo_medico": row.medico.tipo_atencion_medica if row.medico else None} for row in db.scalars(select(Servicio).order_by(Servicio.nombre)).all()]


@router.post("/admin/operaciones/servicios", status_code=201)
@router.put("/admin/operaciones/servicios/{service_id}")
def write_service(data: ServiceWrite, db: Db, user: Admin, service_id: int | None = None):
    check_permission(db, user, "citas", "editar" if service_id else "crear")
    item = db.get(Servicio, service_id) if service_id else Servicio()
    if item is None:
        raise HTTPException(404, "Servicio no encontrado")
    if service_id and bool(item.medico) != (data.tipo == "medica"):
        raise HTTPException(409, "Conserva el tipo de un servicio existente; crea otro para cambiarlo")
    for key, value in data.model_dump(exclude={"tipo", "tipo_medico"}).items():
        setattr(item, key, value)
    if not service_id:
        if data.tipo == "medica":
            item.medico = ServicioMedico(tipo_atencion_medica=data.tipo_medico)
        else:
            item.estetica = ServicioEstetica(tipo_estetica="bano_simple")
    elif item.medico:
        item.medico.tipo_atencion_medica = data.tipo_medico
    return save(db, item)


@router.get("/admin/operaciones/sucursales")
def branches(db: Db, _user: Admin):
    return [row_data(row) for row in db.scalars(select(Sucursal).order_by(Sucursal.id)).all()]


@router.post("/admin/operaciones/sucursales", status_code=201)
@router.put("/admin/operaciones/sucursales/{location_id}")
def write_branch(data: BranchWrite, db: Db, user: Admin, location_id: int | None = None):
    check_permission(db, user, "usuarios", "editar")
    item = db.get(Sucursal, location_id) if location_id else Sucursal()
    if item is None:
        raise HTTPException(404, "Sucursal no encontrada")
    if item.id == user.sucursal_id and not data.activa:
        raise HTTPException(409, "No desactives la sede en la que estás asignado")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    return save(db, item)


@router.get("/admin/operaciones/unidades")
def units(db: Db, _user: InventoryAdmin):
    return [row_data(row) for row in db.scalars(select(UnidadMedida).order_by(UnidadMedida.codigo)).all()]


@router.post("/admin/operaciones/unidades", status_code=201)
def write_unit(data: UnitWrite, db: Db, user: InventoryAdmin):
    check_permission(db, user, "inventario", "crear")
    if db.get(UnidadMedida, data.codigo):
        raise HTTPException(409, "El código de unidad ya existe")
    return save(db, UnidadMedida(**data.model_dump()))


@router.get("/admin/operaciones/lotes")
def lots(db: Db, _user: InventoryAdmin, producto_id: int | None = None, por_vencer: bool = False):
    statement = select(LoteInventario, Producto.nombre).join(Producto, Producto.id == LoteInventario.producto_id)
    if producto_id:
        statement = statement.where(LoteInventario.producto_id == producto_id)
    if por_vencer:
        statement = statement.where(LoteInventario.cantidad > 0, LoteInventario.vencimiento <= dt.date.today() + dt.timedelta(days=PolicyService(db).get().dias_alerta_vencimiento))
    return [{**row_data(row), "producto_nombre": name} for row, name in db.execute(statement.order_by(LoteInventario.vencimiento.asc().nulls_last())).all()]


@router.get("/admin/operaciones/kardex/{product_id}")
def kardex(product_id: int, db: Db, _user: InventoryAdmin):
    return InventoryService(db).kardex(product_id)


@router.get("/admin/operaciones/valorizacion")
def inventory_value(db: Db, _user: InventoryAdmin):
    return InventoryService(db).valuation()


@router.get("/admin/operaciones/compras")
def purchases(db: Db, _user: InventoryAdmin):
    return [{**row_data(row), "documento": row.documento} for row in db.scalars(select(CompraProveedor).order_by(CompraProveedor.id.desc())).all()]


@router.post("/admin/operaciones/compras", status_code=201)
def receive_purchase(data: ReceivePurchase, db: Db, user: InventoryAdmin):
    check_permission(db, user, "inventario", "crear")
    try:
        return InventoryService(db).receive(user, data)
    except Exception:
        db.rollback()
        raise


@router.get("/operaciones/ordenes")
def pending_orders(db: Db, user: User, fecha_inicial: dt.date | None = None, fecha_final: dt.date | None = None, estado: Literal["pendiente", "parcial", "pagada", "anulada"] | None = None, sin_comprobante: bool = False):
    if fecha_inicial and fecha_final and fecha_inicial > fecha_final:
        raise HTTPException(422, "Rango de fechas inválido")
    return BillingService(db).list(user, fecha_inicial, fecha_final, estado, sin_comprobante)


@router.get("/operaciones/ordenes/{order_id}")
def order_detail(order_id: int, db: Db, user: User):
    service = BillingService(db)
    return service.serialize(service.get(order_id, user), history=user.tipo != TipoUsuario.CLIENTE)


@router.get("/operaciones/atenciones")
def attention_orders(cliente_id: int, db: Db, user: User):
    staff(user, db)
    statement = select(ProcesoAtencion).join(Mascota).where(Mascota.cliente_id == cliente_id)
    if user.tipo == TipoUsuario.VETERINARIO:
        statement = statement.where(ProcesoAtencion.proceso_medico.has(veterinario_id=user.id))
    return [{"id": row.id, "mascota": row.mascota.nombre, "servicio": row.cita.servicio.nombre if row.cita else "Ficha inicial",
             "detalles": ([{"servicio_id": row.cita.servicio_id, "cantidad": 1}] if row.cita else []) +
                         ([{"producto_id": item.producto_id, "cantidad": item.cantidad_producto} for item in row.receta.detalles if item.producto_id and item.cantidad_producto] if row.receta else [])}
            for row in db.scalars(statement.order_by(ProcesoAtencion.id.desc())).all()]


@router.get("/operaciones/catalogo")
def billing_catalog(db: Db, user: User):
    staff(user, db)
    return {"clientes": [{"id": row.id, "nombre": row.nombre} for row in UserService(db).get_clients(limit=None)], "productos": [{"id": row.id, "nombre": row.nombre, "precio": row.precio_venta, "stock": row.stock_actual, "unidad": row.unidad_medida, "fraccionable": row.fraccionable} for row in CashierService(db).get_products()], "servicios": [{"id": row.id, "nombre": row.nombre, "precio": row.precio_referencial} for row in CashierService(db).get_services()]}


@router.get("/operaciones/ventas")
def staff_sales(db: Db, user: User):
    staff(user, db)
    statement = select(OrdenCobro).order_by(OrdenCobro.id.desc()).limit(100)
    if user.tipo != TipoUsuario.ADMINISTRADOR:
        statement = statement.where(OrdenCobro.cajero_id == user.id)
    return [{"id": row.id, "codigo_orden": row.codigo_orden, "monto_total": row.monto_total, "estado_pago": row.estado_pago,
             "motivo_anulacion": row.motivo_anulacion, "anulado_por": row.anulado_por,
             "anulado_por_nombre": db.get(Usuario, row.anulado_por).nombre if row.anulado_por else None} for row in db.scalars(statement).all()]


@router.post("/operaciones/ventas/{sale_id}/anular")
def void_staff_sale(sale_id: int, data: Reason, db: Db, user: User):
    staff(user, db, action="eliminar")
    sale = db.get(OrdenCobro, sale_id)
    if sale is None or (user.tipo != TipoUsuario.ADMINISTRADOR and sale.cajero_id != user.id):
        raise HTTPException(404, "Venta no encontrada o no pertenece a tu caja")
    try:
        return SalesService(db).void(sale_id, data.motivo, user.id)
    except (ValueError, LookupError) as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/operaciones/ordenes", status_code=201)
def create_order(data: PendingOrderCreate, db: Db, user: User):
    staff(user, db, action="crear")
    try:
        return BillingService(db).serialize(BillingService(db).create(user, data))
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Ya existe una orden para esta atención o clave; actualiza el listado") from exc


@router.post("/operaciones/ordenes/{order_id}/anular")
def cancel_order(order_id: int, data: Reason, db: Db, user: User):
    staff(user, db, action="eliminar")
    return BillingService(db).cancel(user, order_id, data.motivo)


@router.post("/operaciones/ordenes/{order_id}/abonos", status_code=201)
def register_installment(order_id: int, data: InstallmentWrite, db: Db, user: User):
    staff(user, db, action="crear")
    try:
        return BillingService(db).add_payment(user, order_id, data)
    except Exception:
        db.rollback()
        raise


@router.post("/operaciones/ordenes/{order_id}/comprobantes", status_code=201)
async def attach_proof(order_id: int, db: Db, user: User, datos: str = Form(...), archivo: UploadFile = File(...)):
    if user.tipo != TipoUsuario.CLIENTE:
        staff(user, db, action="crear")
    try:
        data = InstallmentWrite.model_validate_json(datos)
    except ValueError as exc:
        raise HTTPException(422, "Datos del abono inválidos") from exc
    try:
        return BillingService(db).add_payment(user, order_id, data, await archivo.read(5 * 1024 * 1024 + 1))
    except Exception:
        db.rollback()
        raise


@router.get("/operaciones/pagos/{payment_id}/comprobante")
def installment_proof(payment_id: int, db: Db, user: User):
    payment = db.get(AbonoOrden, payment_id)
    if payment is None or not payment.comprobante:
        raise HTTPException(404, "Comprobante no encontrado")
    BillingService(db).get(payment.orden_id, user)
    return Response(payment.comprobante, media_type=payment.comprobante_tipo, headers={"Cache-Control": "private, no-store"})


@router.post("/operaciones/pagos/{payment_id}/validar")
def validate_payment(payment_id: int, db: Db, user: User):
    staff(user, db, action="aprobar")
    try:
        return BillingService(db).validate_payment(user, payment_id)
    except Exception:
        db.rollback()
        raise


@router.post("/operaciones/pagos/{payment_id}/rechazar")
def reject_payment(payment_id: int, data: Reason, db: Db, user: User):
    staff(user, db, action="aprobar")
    payment = db.get(AbonoOrden, payment_id)
    if payment is None:
        raise HTTPException(404, "Abono no encontrado")
    BillingService(db).get(payment.orden_id, user, lock=True)
    if payment.estado != "enviado":
        raise HTTPException(409, "El abono ya fue revisado")
    payment.estado, payment.motivo, payment.validado_por = "rechazado", data.motivo, user.id
    return save(db, payment)


@router.get("/operaciones/descuentos")
def discounts(db: Db, user: User):
    staff(user, db)
    statement = select(AutorizacionDescuento)
    if user.tipo != TipoUsuario.ADMINISTRADOR:
        statement = statement.where(AutorizacionDescuento.solicitante_id == user.id)
    return [{**row_data(row), "solicitante_nombre": db.get(Usuario, row.solicitante_id).nombre,
             "cliente_nombre": db.get(Usuario, row.cliente_id).nombre if row.cliente_id else "Venta sin cliente",
             "aprobador_nombre": db.get(Usuario, row.aprobador_id).nombre if row.aprobador_id else None}
            for row in db.scalars(statement.order_by(AutorizacionDescuento.id.desc())).all()]


@router.post("/operaciones/descuentos", status_code=201)
def request_discount(data: DiscountRequest, db: Db, user: User):
    staff(user, db, action="crear")
    if data.cliente_id and (db.get(Usuario, data.cliente_id) is None or db.get(Usuario, data.cliente_id).tipo != TipoUsuario.CLIENTE):
        raise HTTPException(422, "Selecciona un cliente válido")
    db.info["actor_id"] = user.id
    return save(db, AutorizacionDescuento(solicitante_id=user.id, **data.model_dump()))


@router.post("/operaciones/descuentos/{discount_id}/aprobar")
def approve_discount(discount_id: int, db: Db, user: SalesAdmin):
    check_permission(db, user, "ventas", "aprobar")
    item = db.scalar(select(AutorizacionDescuento).where(AutorizacionDescuento.id == discount_id).with_for_update())
    if item is None or item.estado != "pendiente":
        raise HTTPException(409, "La solicitud no está pendiente")
    item.estado, item.aprobador_id = "aprobada", user.id
    return save(db, item)


@router.post("/operaciones/descuentos/{discount_id}/rechazar")
def reject_discount(discount_id: int, db: Db, user: SalesAdmin):
    check_permission(db, user, "ventas", "aprobar")
    item = db.scalar(select(AutorizacionDescuento).where(AutorizacionDescuento.id == discount_id).with_for_update())
    if item is None or item.estado != "pendiente":
        raise HTTPException(409, "La solicitud no está pendiente")
    item.estado, item.aprobador_id = "rechazada", user.id
    return save(db, item)


@router.get("/operaciones/ventas/{sale_id}/boleta")
def own_receipt(sale_id: int, db: Db, user: User):
    if user.tipo != TipoUsuario.CLIENTE:
        staff(user, db)
    sale = db.get(OrdenCobro, sale_id)
    if sale is None or (user.tipo == TipoUsuario.CLIENTE and sale.cliente_id != user.id):
        raise HTTPException(404, "Venta no encontrada")
    receipt = CashierService(db).get_receipt(sale.cajero_id, sale.id)
    return Response(receipt_pdf(receipt), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{receipt.serie_correlativo}.pdf"'})


@router.get("/operaciones/mis-pagos")
def own_payments(db: Db, user: User):
    if user.tipo != TipoUsuario.CLIENTE:
        raise HTTPException(403, "Este historial corresponde al cliente")
    orders = BillingService(db).list(user)
    sales = db.scalars(select(OrdenCobro).where(OrdenCobro.cliente_id == user.id).order_by(OrdenCobro.id.desc())).all()
    web = db.scalars(select(PedidoWeb).where(PedidoWeb.cliente_id == user.id).order_by(PedidoWeb.id.desc())).all()
    web_sales = {row.venta_id for row in web if row.venta_id}
    return {"ordenes": orders, "ventas": [{"id": row.id, "codigo": row.codigo_orden, "total": row.monto_total, "estado": row.estado_pago,
             "origen": "web" if row.id in web_sales else "orden" if row.preorden_id else "tienda / servicio",
             "fecha": row.comprobante_venta.fecha_emision if row.comprobante_venta else None, "boleta": f"/operaciones/ventas/{row.id}/boleta" if row.comprobante_venta else None} for row in sales],
            "pedidos_web": [{"id": row.id, "codigo": row.codigo_pedido, "total": row.total, "estado": row.estado_pedido, "estado_pago": row.estado_pago,
                             "fecha": row.fecha_pedido, "venta_id": row.venta_id, "motivo_rechazo": row.motivo_rechazo,
                             "comprobante": f"/pedidos-web/{row.id}/comprobante"} for row in web]}


@router.get("/admin/operaciones/plantillas")
def message_templates(db: Db, _user: Admin):
    return MessagingService(db).templates()


@router.put("/admin/operaciones/plantillas/{event}")
def write_template(event: str, data: TemplateWrite, db: Db, user: Admin):
    check_permission(db, user, "usuarios", "editar")
    return MessagingService(db).save_template(event, data)


@router.get("/admin/operaciones/mensajes")
def message_log(db: Db, _user: Admin):
    return [row_data(row, exclude={"contenido", "parametros"} if row.canal == "correo" else ()) for row in db.scalars(select(MensajeSalida).order_by(MensajeSalida.id.desc()).limit(200)).all()]


@router.post("/admin/operaciones/mensajes/{message_id}/reintentar")
def retry_message(message_id: int, db: Db, user: Admin):
    check_permission(db, user, "usuarios", "editar")
    item = db.get(MensajeSalida, message_id)
    if item is None or item.estado in {"enviado", "entregado", "leido"}:
        raise HTTPException(409, "El mensaje no puede reintentarse")
    item.estado, item.intentos, item.proximo_intento = "pendiente", 0, None
    db.commit()
    return {"estado": "pendiente"}
