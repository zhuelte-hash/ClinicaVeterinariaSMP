import datetime as dt
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.operations import Egreso, EventoAuditoria
from app.models.clinic import OrdenCobro
from app.models.user import Usuario
from app.schemas.operations import ExpenseWrite
from app.security import require_permission, check_permission
from app.services.admin_service import AdminService
from app.services.backup_service import create_backup, verify_restore
from app.services.operation_utils import branch_id, row_data
from app.services.reporting_service import ReportingService, bounds, db_user_name, xlsx
from app.services.sales_service import SalesService

router = APIRouter(prefix="/admin/operaciones", tags=["Reportes y protección de datos"])
Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[Usuario, Depends(require_permission("usuarios"))]
from app.security import get_current_admin_user
SalesAdmin = Annotated[Usuario, Depends(require_permission("ventas"))]


@router.get("/dashboard")
def dashboard(desde: dt.date, hasta: dt.date, db: Db, _user: SalesAdmin):
    return ReportingService(db).dashboard(desde, hasta)


@router.get("/cierres")
def closures(desde: dt.date, hasta: dt.date, db: Db, _user: SalesAdmin):
    return ReportingService(db).closures(desde, hasta)


@router.get("/ocupacion")
def occupancy(desde: dt.date, hasta: dt.date, db: Db, _user: Admin, veterinario_id: int | None = None):
    return ReportingService(db).occupancy(desde, hasta, veterinario_id)


@router.get("/auditoria")
def audit(db: Db, _user: Admin, desde: dt.date | None = None, hasta: dt.date | None = None, usuario_id: int | None = None, entidad: str | None = None):
    statement = select(EventoAuditoria)
    if desde and hasta:
        initial, final = bounds(desde, hasta)
        statement = statement.where(EventoAuditoria.fecha >= initial, EventoAuditoria.fecha < final)
    if usuario_id:
        statement = statement.where(EventoAuditoria.usuario_id == usuario_id)
    if entidad:
        statement = statement.where(EventoAuditoria.entidad == entidad)
    return [{**row_data(row), "autor": db_user_name(db, row.usuario_id) if row.usuario_id else "Sistema"} for row in db.scalars(statement.order_by(EventoAuditoria.id.desc()).limit(2000)).all()]


@router.get("/egresos")
def expenses(desde: dt.date, hasta: dt.date, db: Db, _user: SalesAdmin):
    bounds(desde, hasta)
    return [row_data(row) for row in db.scalars(select(Egreso).where(Egreso.fecha >= desde, Egreso.fecha <= hasta).order_by(Egreso.fecha.desc())).all()]


@router.post("/egresos", status_code=201)
def record_expense(data: ExpenseWrite, db: Db, user: SalesAdmin):
    check_permission(db, user, "ventas", "crear")
    item = Egreso(usuario_id=user.id, sucursal_id=branch_id(db), **data.model_dump())
    db.add(item); db.commit()
    return row_data(item)


@router.get("/exportar/{report}")
def export_report(report: Literal["ventas", "citas", "inventario"], desde: dt.date, hasta: dt.date, db: Db, user: Annotated[Usuario, Depends(get_current_admin_user)], estado: str | None = None,
                  metodo_pago: Literal["efectivo", "yape", "plin", "tarjeta", "transferencia"] | None = None, cajero_id: int | None = None, producto_id: int | None = None, numero_venta: str | None = None):
    bounds(desde, hasta)
    if report == "ventas":
        check_permission(db, user, "ventas")
        if estado and estado not in {"PAGADA", "ANULADA", "PENDIENTE"}:
            raise HTTPException(422, "Estado de venta no válido")
        orders = db.scalars(SalesService(db).filtered(fecha_inicial=desde, fecha_final=hasta, estado=estado, metodo_pago=metodo_pago, cajero_id=cajero_id, producto_id=producto_id, numero_venta=numero_venta).order_by(OrdenCobro.id)).all()
        headers = ["Código", "Fecha", "Cajero", "Cliente", "Método", "Total", "Estado"]
        rows = [[order.codigo_orden, order.comprobante_venta.fecha_emision, order.cajero.usuario.nombre, order.cliente.usuario.nombre if order.cliente else "", order.medio_pago, order.monto_total, order.estado_pago.value] for order in orders]
    elif report == "citas":
        check_permission(db, user, "citas")
        from app.models.clinic import EstadoCita
        if estado and estado not in {value.value for value in EstadoCita}:
            raise HTTPException(422, "Estado de cita no válido")
        headers = ["Cita", "Fecha", "Paciente", "Propietario", "Veterinario", "Servicio", "Estado", "Urgente"]
        rows = [[row.id, row.fecha_hora_programada, row.mascota_nombre, row.cliente_nombre, row.veterinario_nombre, row.servicio_nombre, row.estado, row.es_urgente] for row in AdminService(db).get_appointments(status=estado, start_date=desde, end_date=hasta)]
    else:
        check_permission(db, user, "inventario")
        headers = ["SKU", "Producto", "Unidad", "Cantidad", "Mínimo", "Costo unitario", "Valor al costo"]
        rows = [[row.sku, row.nombre, row.unidad_medida, row.stock_actual, row.stock_minimo, row.costo_unitario, Decimal(str(row.stock_actual)) * row.costo_unitario] for row in AdminService(db).get_products()]
    return Response(xlsx(headers, rows), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{report}-{desde}-{hasta}.xlsx"'})


@router.get("/respaldo")
def backup(db: Db, user: Admin):
    check_permission(db, user, "usuarios", "editar")
    return Response(create_backup(db), media_type="application/zip", headers={"Content-Disposition": 'attachment; filename="respaldo-clinica.zip"', "Cache-Control": "private, no-store"})


@router.post("/respaldo/verificar")
async def restore_check(user: Admin, db: Db, archivo: UploadFile = File(...)):
    check_permission(db, user, "usuarios", "editar")
    content = await archivo.read(50 * 1024 * 1024 + 1)
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(413, "El respaldo comprimido supera 50 MB")
    return verify_restore(content)
