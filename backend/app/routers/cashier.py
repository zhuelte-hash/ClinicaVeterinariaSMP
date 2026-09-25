from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import Usuario
from app.schemas.cashier import (
    BoletaRead,
    CajaAbrir,
    CajaRead,
    CajaResumen,
    CategoriaCajaRead,
    ClienteCajaRead,
    ProductoCajaRead,
    ServicioCajaRead,
    VentaCreate,
)
from app.security import get_current_cashier_user
from app.services.cashier_service import (
    CajaNoAbiertaError,
    CajaYaAbiertaError,
    CashierService,
    ClienteNoEncontradoError,
    ProductoNoDisponibleError,
    StockInsuficienteError,
    VentaNoEncontradaError,
)

router = APIRouter(prefix="/caja", tags=["Caja"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentCashier = Annotated[Usuario, Depends(get_current_cashier_user)]


@router.get("/resumen", response_model=CajaResumen)
def get_summary(db: DbSession, cashier: CurrentCashier):
    return CashierService(db).get_summary(cashier.id)


@router.post("/abrir", response_model=CajaRead, status_code=status.HTTP_201_CREATED)
def open_register(data: CajaAbrir, db: DbSession, cashier: CurrentCashier):
    try:
        return CashierService(db).open_register(cashier, data)
    except CajaYaAbiertaError as exc:
        raise HTTPException(status_code=409, detail="Ya tienes una caja abierta") from exc


@router.post("/cerrar", response_model=CajaRead)
def close_register(db: DbSession, cashier: CurrentCashier):
    try:
        return CashierService(db).close_register(cashier.id)
    except CajaNoAbiertaError as exc:
        raise HTTPException(status_code=409, detail="No tienes una caja abierta") from exc


@router.get("/categorias", response_model=list[CategoriaCajaRead])
def get_categories(db: DbSession, _cashier: CurrentCashier):
    return CashierService(db).get_categories()


@router.get("/productos", response_model=list[ProductoCajaRead])
def get_products(
    db: DbSession,
    _cashier: CurrentCashier,
    q: Annotated[str | None, Query(max_length=100)] = None,
    categoria_id: int | None = None,
):
    return CashierService(db).get_products(q, categoria_id)


@router.get("/clientes", response_model=list[ClienteCajaRead])
def get_clients(
    db: DbSession,
    _cashier: CurrentCashier,
    q: Annotated[str | None, Query(max_length=100)] = None,
):
    return CashierService(db).get_clients(q)


@router.get("/servicios", response_model=list[ServicioCajaRead])
def get_services(
    db: DbSession,
    _cashier: CurrentCashier,
    q: Annotated[str | None, Query(max_length=100)] = None,
):
    return CashierService(db).get_services(q)


@router.post("/ventas", response_model=BoletaRead, status_code=status.HTTP_201_CREATED)
def create_sale(data: VentaCreate, db: DbSession, cashier: CurrentCashier):
    try:
        return CashierService(db).create_sale(cashier, data)
    except CajaNoAbiertaError as exc:
        raise HTTPException(status_code=409, detail="Debes abrir una caja") from exc
    except ClienteNoEncontradoError as exc:
        raise HTTPException(status_code=404, detail="Cliente no encontrado") from exc
    except ProductoNoDisponibleError as exc:
        raise HTTPException(status_code=404, detail="Uno de los productos no existe") from exc
    except StockInsuficienteError as exc:
        raise HTTPException(status_code=409, detail="Stock insuficiente") from exc


@router.get("/ventas/{order_id}/boleta", response_model=BoletaRead)
def get_receipt(order_id: int, db: DbSession, cashier: CurrentCashier):
    try:
        return CashierService(db).get_receipt(cashier.id, order_id)
    except VentaNoEncontradaError as exc:
        raise HTTPException(status_code=404, detail="Boleta no encontrada") from exc
