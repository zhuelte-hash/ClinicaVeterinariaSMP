import datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import TipoUsuario, Usuario
from app.schemas.admin import (
    AdminAppointmentRead, AdminProductCatalog, AdminProductCreate, AdminProductRead, AdminProductUpdate, AdminSalesDayRead,
    RolePermissionRead, RolePermissionUpdate,
)
from app.security import get_current_admin_user, require_permission
from app.services.admin_service import AdminConflictError, AdminNotFoundError, AdminService

router = APIRouter(prefix="/admin", tags=["Administración"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentAdmin = Annotated[Usuario, Depends(get_current_admin_user)]
PRODUCT_IMAGES_DIR = Path(__file__).resolve().parents[2] / "uploads" / "products"
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


@router.get("/productos", response_model=list[AdminProductRead])
def get_products(db: DbSession, _user: Annotated[Usuario, Depends(require_permission("productos"))], include_inactive: bool = False):
    return AdminService(db).get_products(include_inactive)


@router.patch("/productos/{product_id}", response_model=AdminProductRead)
def update_product(product_id: int, data: AdminProductUpdate, db: DbSession, _user: Annotated[Usuario, Depends(require_permission("productos", "editar"))]):
    try:
        return AdminService(db).update_product(product_id, data)
    except AdminNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Producto no encontrado") from exc
    except AdminConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/productos", response_model=AdminProductRead, status_code=status.HTTP_201_CREATED)
def create_product(data: AdminProductCreate, db: DbSession, _user: Annotated[Usuario, Depends(require_permission("productos", "crear"))]):
    try:
        return AdminService(db).create_product(data)
    except AdminNotFoundError as exc:
        raise HTTPException(status_code=422, detail="Categoría o proveedor no encontrado") from exc
    except AdminConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/productos/catalogo", response_model=AdminProductCatalog)
def get_product_catalog(db: DbSession, _user: Annotated[Usuario, Depends(require_permission("productos"))]):
    return AdminService(db).get_product_catalog()


@router.post("/productos/imagen")
async def upload_product_image(
    request: Request,
    image: UploadFile = File(...),
    _user: Annotated[Usuario, Depends(require_permission("productos", "crear"))] = None,
):
    extension = ALLOWED_IMAGE_TYPES.get(image.content_type or "")
    if extension is None:
        raise HTTPException(status_code=422, detail="La imagen debe ser JPG, PNG o WEBP")
    content = await image.read()
    if not content or len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=422, detail="La imagen debe pesar entre 1 byte y 5 MB")
    PRODUCT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{extension}"
    (PRODUCT_IMAGES_DIR / filename).write_bytes(content)
    return {"url": f"{str(request.base_url).rstrip('/')}/uploads/products/{filename}"}


@router.delete("/productos/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_product(product_id: int, db: DbSession, _user: Annotated[Usuario, Depends(require_permission("productos", "eliminar"))]):
    try:
        AdminService(db).deactivate_product(product_id)
    except AdminNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Producto no encontrado") from exc


@router.get("/citas", response_model=list[AdminAppointmentRead])
def get_appointments(db: DbSession, _user: Annotated[Usuario, Depends(require_permission("citas"))], fecha: datetime.date | None = None, estado: str | None = Query(default=None, max_length=50)):
    return AdminService(db).get_appointments(fecha, estado)


@router.get("/ventas/dia", response_model=AdminSalesDayRead)
def get_sales_day(db: DbSession, _user: Annotated[Usuario, Depends(require_permission("ventas"))], fecha: datetime.date | None = None):
    return AdminService(db).get_sales_day(fecha)


@router.get("/permisos", response_model=list[RolePermissionRead], dependencies=[Depends(get_current_admin_user), Depends(require_permission("usuarios", "editar"))])
def get_permissions(db: DbSession):
    return AdminService(db).get_role_permissions()


@router.put("/permisos/{role}/{module}", response_model=RolePermissionRead, dependencies=[Depends(get_current_admin_user), Depends(require_permission("usuarios", "editar"))])
def update_permission(role: TipoUsuario, module: str, data: RolePermissionUpdate, db: DbSession):
    try:
        return AdminService(db).update_role_permission(role, module, data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
