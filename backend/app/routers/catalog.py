from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.clinic import Producto
from app.schemas.admin import AdminProductRead
from app.services.admin_service import AdminService

router = APIRouter(prefix="/catalogo", tags=["Catálogo público"])


@router.get("/productos", response_model=list[AdminProductRead])
def get_public_products(
    db: Session = Depends(get_db), categoria_id: int | None = None,
    especie: str | None = None, precio_min: Decimal | None = Query(default=None, ge=0),
    precio_max: Decimal | None = Query(default=None, ge=0),
    x_sucursal_id: int = Header(default=1, ge=1),
):
    if precio_min is not None and precio_max is not None and precio_min > precio_max:
        raise HTTPException(status_code=422, detail="El precio mínimo no puede superar al máximo")
    products = db.scalars(
        select(Producto)
        .where(Producto.activo, Producto.sucursal_id == x_sucursal_id)
        .options(selectinload(Producto.categoria))
        .order_by(Producto.nombre)
    ).all()
    return [AdminService._product_read(product) for product in products
            if (categoria_id is None or product.categoria_id == categoria_id)
            and (precio_min is None or product.precio_venta >= precio_min)
            and (precio_max is None or product.precio_venta <= precio_max)
            and (not especie or not product.especies or especie.casefold() in [value.casefold() for value in product.especies])]


@router.get("/productos/{product_id}", response_model=AdminProductRead)
def get_public_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Producto, product_id)
    if product is None or not product.activo:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return AdminService._product_read(product)
