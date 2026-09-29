import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import TipoUsuario, Usuario
from app.schemas.cashier import BoletaRead, VentaCreate
from app.security import get_current_active_user, get_current_admin_user
from app.services.cashier_service import (CashierService, CajaNoAbiertaError,
    ClienteNoEncontradoError, ProductoNoDisponibleError, StockInsuficienteError, VentaDuplicadaError)
from app.services.sales_service import SalesService

router = APIRouter(tags=["Ventas"])
Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[Usuario, Depends(get_current_admin_user)]


@router.post("/api/ventas", response_model=BoletaRead, status_code=status.HTTP_201_CREATED)
def create(data: VentaCreate, db: Db, user: Annotated[Usuario, Depends(get_current_active_user)]):
    if user.tipo not in (TipoUsuario.CAJERO, TipoUsuario.ADMINISTRADOR):
        raise HTTPException(403, "Se requiere rol de cajero o administrador")
    try:
        return CashierService(db).create_sale(user, data)
    except CajaNoAbiertaError as exc:
        raise HTTPException(409, "Debes abrir una caja") from exc
    except ClienteNoEncontradoError as exc:
        raise HTTPException(404, "Cliente no encontrado") from exc
    except ProductoNoDisponibleError as exc:
        raise HTTPException(404, "Un producto o servicio no existe") from exc
    except StockInsuficienteError as exc:
        raise HTTPException(409, "Stock insuficiente") from exc
    except VentaDuplicadaError as exc:
        raise HTTPException(409, "Clave de venta ya utilizada con otros datos") from exc


@router.get("/api/admin/ventas/resumen")
def summary(db: Db, _admin: Admin, fecha_inicial: datetime.date | None = None,
            fecha_final: datetime.date | None = None, numero_venta: str | None = None,
            estado: Literal["PAGADA", "ANULADA", "PENDIENTE"] | None = None,
            metodo_pago: Literal["efectivo", "yape", "plin", "tarjeta"] | None = None,
            cajero_id: int | None = None, producto_id: int | None = None):
    return SalesService(db).summary(fecha_inicial=fecha_inicial, fecha_final=fecha_final,
        numero_venta=numero_venta, estado=estado, metodo_pago=metodo_pago,
        cajero_id=cajero_id, producto_id=producto_id)


@router.get("/api/admin/ventas")
def list_sales(db: Db, _admin: Admin, fecha_inicial: datetime.date | None = None,
               fecha_final: datetime.date | None = None, numero_venta: str | None = Query(default=None, max_length=50),
               estado: Literal["PAGADA", "ANULADA", "PENDIENTE"] | None = None,
               metodo_pago: Literal["efectivo", "yape", "plin", "tarjeta"] | None = None,
               cajero_id: int | None = None, producto_id: int | None = None,
               pagina: int = Query(default=1, ge=1), tamano_pagina: int = Query(default=20, ge=1, le=100)):
    if fecha_inicial and fecha_final and fecha_inicial > fecha_final:
        raise HTTPException(422, "La fecha inicial debe ser anterior a la fecha final")
    return SalesService(db).list(page=pagina, page_size=tamano_pagina,
        fecha_inicial=fecha_inicial, fecha_final=fecha_final, numero_venta=numero_venta,
        estado=estado, metodo_pago=metodo_pago, cajero_id=cajero_id, producto_id=producto_id)


@router.get("/api/admin/ventas/{order_id}")
def detail(order_id: int, db: Db, _admin: Admin):
    try:
        return SalesService(db).get(order_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/api/admin/ventas/{order_id}/anular")
def void(order_id: int, db: Db, _admin: Admin):
    try:
        return SalesService(db).void(order_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
