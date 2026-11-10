import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import TipoUsuario, Usuario
from app.schemas.purchase import PedidoCreate, PedidoRead, RevisionPedido
from app.security import get_current_active_user, get_current_client_user, require_permission
from app.services.purchase_service import MAX_PROOF_BYTES, PurchaseService, payment_config

router = APIRouter(prefix="/pedidos-web", tags=["Pedidos web"])
Db = Annotated[Session, Depends(get_db)]
Client = Annotated[Usuario, Depends(get_current_client_user)]


def purchase_user(db: Db, user: Annotated[Usuario, Depends(get_current_active_user)]):
    if user.tipo == TipoUsuario.ADMINISTRADOR:
        return require_permission("ventas")(user=user, db=db)
    if user.tipo not in (TipoUsuario.CLIENTE, TipoUsuario.CAJERO):
        raise HTTPException(403, "Se requiere rol de cliente, cajero o administrador")
    return user


User = Annotated[Usuario, Depends(purchase_user)]


@router.get("/configuracion")
def configuration():
    return payment_config()


@router.post("", status_code=201, response_model=PedidoRead)
async def create(db: Db, user: Client, datos: Annotated[str, Form(max_length=50000)], comprobante: Annotated[UploadFile, File()]):
    try:
        data = PedidoCreate.model_validate_json(datos)
    except ValidationError as exc:
        raise HTTPException(422, "Datos del pedido inválidos: " + str(exc)) from exc
    try:
        content = await comprobante.read(MAX_PROOF_BYTES + 1)
    finally:
        await comprobante.close()
    return PurchaseService(db).create(user, data, content)


@router.get("", response_model=list[PedidoRead])
def listing(db: Db, user: User, estado: Literal["PENDIENTE", "APROBADO", "RECHAZADO", "CANCELADO"] | None = None,
            codigo: str | None = Query(default=None, max_length=50), fecha: datetime.date | None = None,
            pagina: int = Query(default=1, ge=1)):
    return PurchaseService(db).list(user, estado, codigo, fecha, pagina)


@router.get("/{order_id}", response_model=PedidoRead)
def detail(order_id: int, db: Db, user: User):
    service = PurchaseService(db)
    return service.serialize(service.get(order_id, user))


@router.get("/{order_id}/comprobante")
def proof(order_id: int, db: Db, user: User):
    order = PurchaseService(db).get(order_id, user)
    return Response(order.comprobante_contenido, media_type=order.comprobante_tipo,
        headers={"Content-Disposition": f'attachment; filename="{order.comprobante_pago}"',
                 "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.post("/{order_id}/revision", response_model=PedidoRead)
def review(order_id: int, data: RevisionPedido, db: Db, user: User):
    if user.tipo == TipoUsuario.ADMINISTRADOR:
        require_permission("ventas", "aprobar")(user=user, db=db)
    elif user.tipo != TipoUsuario.CAJERO:
        raise HTTPException(403, "Solo caja o administración pueden revisar pedidos")
    return PurchaseService(db).review(user, order_id, data)
