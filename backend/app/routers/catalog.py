from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.clinic import Producto
from app.schemas.admin import AdminProductRead
from app.services.admin_service import AdminService

router = APIRouter(prefix="/catalogo", tags=["Catálogo público"])


@router.get("/productos", response_model=list[AdminProductRead])
def get_public_products(db: Session = Depends(get_db)):
    products = db.scalars(
        select(Producto)
        .where(Producto.activo)
        .options(selectinload(Producto.categoria))
        .order_by(Producto.nombre)
    ).all()
    return [AdminService._product_read(product) for product in products]
