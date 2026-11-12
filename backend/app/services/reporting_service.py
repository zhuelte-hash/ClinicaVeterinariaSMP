import datetime as dt
from collections import Counter, defaultdict
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZIP_DEFLATED

from fastapi import HTTPException
from sqlalchemy import func, select

from app.models.clinic import BloqueoHorario, Caja, Cita, ComprobanteVenta, DetalleOrdenCobro, EstadoCita, EstadoPago, HorarioVeterinario, OrdenCobro, Producto, Servicio
from app.models.operations import AbonoOrden, Egreso, EventoAuditoria, MovimientoCaja, OrdenPendiente
from app.models.purchase import PedidoWeb
from app.models.user import Usuario
from app.services.access_service import aware
from app.services.operation_utils import branch_id, row_data
from app.services.policy_service import PolicyService, ZONE


def bounds(start, end):
    if start > end or (end - start).days > 366:
        raise HTTPException(422, "Selecciona un rango válido de hasta 366 días")
    return dt.datetime.combine(start, dt.time.min, ZONE).astimezone(dt.timezone.utc), dt.datetime.combine(end + dt.timedelta(days=1), dt.time.min, ZONE).astimezone(dt.timezone.utc)


def merge(intervals):
    result = []
    for start, end in sorted(intervals):
        if end <= start:
            continue
        if result and start <= result[-1][1]:
            result[-1] = result[-1][0], max(result[-1][1], end)
        else:
            result.append((start, end))
    return result


def subtract(intervals, blocked):
    for blocked_start, blocked_end in merge(blocked):
        updated = []
        for start, end in intervals:
            if blocked_start > start:
                updated.append((start, min(end, blocked_start)))
            if blocked_end < end:
                updated.append((max(start, blocked_end), end))
        intervals = [(a, b) for a, b in updated if b > a]
    return intervals


class ReportingService:
    def __init__(self, db):
        self.db = db

    def dashboard(self, start, end):
        initial, final = bounds(start, end)
        paid = select(OrdenCobro).join(ComprobanteVenta).where(OrdenCobro.estado_pago == EstadoPago.VALIDADO_CONFIRMADO, ComprobanteVenta.fecha_emision >= initial, ComprobanteVenta.fecha_emision < final)
        sales = self.db.scalars(paid).all()
        appointments = self.db.scalars(select(Cita).where(Cita.fecha_hora_programada >= initial, Cita.fecha_hora_programada < final)).all()
        states = {state.value: 0 for state in EstadoCita}
        for item in appointments:
            states[item.estado.value] += 1
        pending = self.db.scalars(select(OrdenPendiente).where(OrdenPendiente.estado.in_(["pendiente", "parcial"]))).all()
        web_pending = self.db.scalar(select(func.count(PedidoWeb.id)).where(PedidoWeb.estado_pedido == "PENDIENTE")) or 0
        product_totals, service_totals = defaultdict(lambda: Decimal(0)), Counter()
        for sale in sales:
            for detail in sale.detalles:
                if detail.producto_id:
                    product_totals[detail.producto.nombre] += detail.cantidad
        for appointment in appointments:
            if appointment.estado == EstadoCita.ATENDIDA:
                service_totals[appointment.servicio.nombre] += 1
        low = self.db.scalars(select(Producto).where(Producto.activo, Producto.stock_actual <= Producto.stock_minimo)).all()
        cash = self.db.scalar(select(func.coalesce(func.sum(MovimientoCaja.monto), 0)).join(Caja, Caja.id == MovimientoCaja.caja_id).where(MovimientoCaja.fecha >= initial, MovimientoCaja.fecha < final)) or Decimal(0)
        direct = sum((sale.monto_total for sale in sales if sale.preorden_id is None), Decimal(0))
        expenses = self.db.scalar(select(func.coalesce(func.sum(Egreso.monto), 0)).where(Egreso.fecha >= start, Egreso.fecha <= end)) or Decimal(0)
        awaiting = self.db.scalar(select(func.count(AbonoOrden.id)).join(OrdenPendiente, OrdenPendiente.id == AbonoOrden.orden_id).where(AbonoOrden.estado == "enviado")) or 0
        return {"desde": start, "hasta": end, "sucursal_id": branch_id(self.db), "ventas": sum((sale.monto_total for sale in sales), Decimal(0)), "citas_por_estado": states, "ordenes_pendientes": len(pending), "pagos_web_por_validar": web_pending, "pagos_por_validar": awaiting, "stock_bajo": [{"id": p.id, "nombre": p.nombre, "stock": p.stock_actual, "minimo": p.stock_minimo} for p in low], "productos_mas_vendidos": [{"nombre": name, "cantidad": qty} for name, qty in sorted(product_totals.items(), key=lambda row: row[1], reverse=True)[:10]], "servicios_mas_atendidos": [{"nombre": name, "cantidad": qty} for name, qty in service_totals.most_common(10)], "finanzas": {"cobros": cash + direct, "egresos": expenses, "resultado": cash + direct - expenses, "criterio": "Cobros efectivos del período, incluidos abonos; egresos y recepciones de mercadería registrados"}}

    def closures(self, start, end):
        initial, final = bounds(start, end)
        from app.services.cashier_service import CashierService
        registers = self.db.scalars(select(Caja).where(Caja.estado_caja == "cerrada", Caja.fecha_cierre >= initial, Caja.fecha_cierre < final).order_by(Caja.fecha_cierre.desc())).all()
        rows = []
        for register in registers:
            cash, digital = CashierService(self.db)._payment_totals(register.id)
            rows.append({**row_data(register), "cajero": db_user_name(self.db, register.cajero_id), "ingresos_efectivo": cash, "ingresos_digitales": digital, "efectivo_esperado": register.fondo_inicial + cash})
        return {"cierres": rows, "cantidad": len(rows), "diferencia_total": sum((row["diferencia"] or 0 for row in rows), Decimal(0))}

    def occupancy(self, start, end, veterinarian=None):
        initial, final = bounds(start, end)
        schedules = self.db.scalars(select(HorarioVeterinario).where(HorarioVeterinario.activo)).all()
        blocks = self.db.scalars(select(BloqueoHorario).where(BloqueoHorario.fecha_hora_inicio < final, BloqueoHorario.fecha_hora_fin > initial)).all()
        appointments = self.db.scalars(select(Cita).where(Cita.fecha_hora_programada < final, Cita.fecha_hora_fin_programada > initial, Cita.estado.not_in([EstadoCita.CANCELADA, EstadoCita.NO_ASISTIO]))).all()
        policy = PolicyService(self.db)
        rows = []
        day = start
        while day <= end:
            hours = policy.hours(day)
            for vet in sorted({row.veterinario_id for row in schedules}):
                if veterinarian and vet != veterinarian:
                    continue
                ranges = []
                for schedule in schedules:
                    if schedule.veterinario_id != vet or schedule.dia_semana != day.weekday() or hours.cerrado:
                        continue
                    a = dt.datetime.combine(day, max(schedule.hora_inicio, hours.inicio), ZONE)
                    b = dt.datetime.combine(day, min(schedule.hora_fin, hours.fin), ZONE)
                    if b > a:
                        ranges.append((a, b))
                forbidden = [(aware(row.fecha_hora_inicio).astimezone(ZONE), aware(row.fecha_hora_fin).astimezone(ZONE)) for row in blocks if row.veterinario_id == vet]
                if hours.descanso_inicio:
                    forbidden.append((dt.datetime.combine(day, hours.descanso_inicio, ZONE), dt.datetime.combine(day, hours.descanso_fin, ZONE)))
                available = subtract(merge(ranges), forbidden)
                capacity = sum((b - a).total_seconds() / 60 for a, b in available)
                busy = []
                for appointment in appointments:
                    if appointment.veterinario_id == vet:
                        for a, b in available:
                            busy.append((max(a, aware(appointment.fecha_hora_programada).astimezone(ZONE)), min(b, aware(appointment.fecha_hora_fin_programada).astimezone(ZONE))))
                occupied = sum((b - a).total_seconds() / 60 for a, b in merge(busy))
                rows.append({"fecha": day, "veterinario_id": vet, "veterinario": db_user_name(self.db, vet), "capacidad_minutos": capacity, "ocupados_minutos": occupied, "porcentaje": round(occupied / capacity * 100, 2) if capacity else 0})
            day += dt.timedelta(days=1)
        capacity, occupied = sum(row["capacidad_minutos"] for row in rows), sum(row["ocupados_minutos"] for row in rows)
        return {"capacidad_minutos": capacity, "ocupados_minutos": occupied, "porcentaje": round(occupied / capacity * 100, 2) if capacity else 0, "detalle": rows}


def db_user_name(db, user_id):
    user = db.get(Usuario, user_id)
    return user.nombre if user else "Sistema"


def xlsx(headers, rows):
    def column(index):
        value = ""
        while index:
            index, digit = divmod(index - 1, 26)
            value = chr(65 + digit) + value
        return value
    data = []
    for number, row in enumerate([headers] + rows, 1):
        cells = []
        for index, value in enumerate(row, 1):
            reference = f"{column(index)}{number}"
            if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
                cells.append(f'<c r="{reference}"><v>{value}</v></c>')
            else:
                cells.append(f'<c r="{reference}" t="inlineStr"><is><t xml:space="preserve">{escape(str(value if value is not None else ""))}</t></is></c>')
        data.append(f'<row r="{number}">{"".join(cells)}</row>')
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        archive.writestr('_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        archive.writestr('xl/workbook.xml', '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Reporte" sheetId="1" r:id="rId1"/></sheets></workbook>')
        archive.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        archive.writestr('xl/worksheets/sheet1.xml', f'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{"".join(data)}</sheetData></worksheet>')
    return output.getvalue()
