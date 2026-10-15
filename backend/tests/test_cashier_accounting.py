"""Validaciones y conciliación de pagos sin conectarse a una base de datos."""

from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.cashier import VentaCreate
from app.services.cashier_service import CashierService


def test_mixed_payment_payload_rejects_duplicate_methods():
    with pytest.raises(ValidationError):
        VentaCreate(medio_pago="efectivo", items=[{"producto_id": 1, "cantidad": 1}], pagos=[
            {"medio": "efectivo", "monto": "10.00"},
            {"medio": "efectivo", "monto": "5.00"},
        ])


def test_payment_totals_count_only_confirmed_orders_and_return_correct_change():
    orders = [
        SimpleNamespace(pagos=[{"medio": "efectivo", "monto": "12.00"},
                                {"medio": "yape", "monto": "8.00"}], medio_pago="efectivo", monto_total=Decimal("20.00")),
        SimpleNamespace(pagos=None, medio_pago="tarjeta", monto_total=Decimal("7.50")),
    ]
    db = SimpleNamespace(scalars=lambda statement: SimpleNamespace(all=lambda: orders))
    service = CashierService(db)
    assert service._payment_totals(3) == (Decimal("12.00"), Decimal("15.50"))


def test_closing_register_records_counted_cash_and_difference():
    register = SimpleNamespace(id=3, cajero_id=5, fondo_inicial=Decimal("100.00"), estado_caja="abierta",
                               efectivo_contado=None, diferencia=None, fecha_cierre=None)
    db = SimpleNamespace(scalar=lambda stmt: None if "ordenes_cobro" in str(stmt) else register,
                         commit=lambda: None, refresh=lambda obj: None)
    service = CashierService(db)
    service._payment_totals = lambda register_id: (Decimal("35.00"), Decimal("18.00"))
    closed = service.close_register(5, Decimal("133.50"))
    assert closed.estado_caja == "cerrada"
    assert closed.efectivo_contado == Decimal("133.50")
    assert closed.diferencia == Decimal("-1.50")
    assert closed.fecha_cierre is not None
