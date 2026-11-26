"""Webhooks firmados de Twilio y acceso temporal al PDF que recupera el proveedor."""
import datetime as dt
import re

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from twilio.request_validator import RequestValidator

from app.config import get_settings
from app.database import get_db
from app.models.operations import MensajeSalida
from app.routers.messaging import receive_message
from app.services.access_service import now
from app.services.twilio_service import MESSAGE_SID, document_allowed, download_proof, twilio_error
from app.services.whatsapp_config_service import normalized_phone, twilio_missing

router = APIRouter(prefix="/whatsapp/twilio", tags=["Twilio Sandbox"])


async def signed_form(request):
    settings = get_settings()
    if settings.whatsapp_provider != "twilio" or twilio_missing(settings):
        raise HTTPException(503, "Selecciona Twilio y completa su configuración local")
    if request.headers.get("Content-Type", "").split(";", 1)[0].lower() != "application/x-www-form-urlencoded":
        raise HTTPException(415, "Twilio debe enviar un formulario POST")
    if len(await request.body()) > 64 * 1024:
        raise HTTPException(413, "Evento demasiado grande")
    form = await request.form()
    # Usar el origen configurado evita depender de Host/X-Forwarded-* del túnel.
    url = settings.twilio_public_url.rstrip("/") + request.url.path
    if request.url.query:
        url += "?" + request.url.query
    if not RequestValidator(settings.twilio_auth_token).validate(url, form, request.headers.get("X-Twilio-Signature", "")):
        raise HTTPException(403, "Firma de Twilio inválida; comprueba la URL HTTPS exacta del webhook")
    if form.get("AccountSid") != settings.twilio_account_sid:
        raise HTTPException(403, "El evento no corresponde a esta cuenta de Twilio")
    if not re.fullmatch(MESSAGE_SID, form.get("MessageSid", "")):
        raise HTTPException(422, "Referencia de Twilio inválida")
    return form


@router.post("/incoming")
async def incoming(request: Request, db: Session = Depends(get_db)):
    form = await signed_form(request)
    settings = get_settings()
    if form.get("To") != settings.twilio_whatsapp_from or not re.fullmatch(r"whatsapp:\+[1-9]\d{9,14}", form.get("From", "")):
        raise HTTPException(403, "El mensaje debe llegar por WhatsApp al emisor configurado")
    sid = form["MessageSid"]
    message = {"id": f"twilio:{sid}", "from": normalized_phone(form["From"]),
               "type": "text", "text": {"body": form.get("Body", "")}}
    if form.get("NumMedia", "0") not in {"0", "1"}:
        raise HTTPException(422, "Envía un único comprobante por mensaje")
    mime = form.get("MediaContentType0", "")
    if form.get("NumMedia", "0") == "1":
        kind = "image" if mime.startswith("image/") else "document"
        message.update({"type": kind, kind: {"id": form.get("MediaUrl0", ""), "caption": form.get("Body", "")}})
    await receive_message(message, db, download_proof=lambda url: download_proof(url, sid, mime))
    # El mensaje entrante persiste antes de habilitar el siguiente ciclo del worker.
    db.execute(update(MensajeSalida).where(MensajeSalida.canal == "whatsapp",
               MensajeSalida.destinatario == message["from"], MensajeSalida.estado == "pendiente_configuracion",
               MensajeSalida.intentos < 5).values(proximo_intento=None))
    db.commit()
    return Response("<Response/>", media_type="application/xml", headers={"Cache-Control": "private, no-store"})


@router.post("/status", status_code=204)
async def status(request: Request, db: Session = Depends(get_db), message_id: int | None = Query(default=None, gt=0)):
    form = await signed_form(request)
    settings = get_settings()
    if form.get("From") and form["From"] != settings.twilio_whatsapp_from:
        raise HTTPException(403, "El estado no corresponde al emisor configurado")
    statement = select(MensajeSalida).where(MensajeSalida.canal == "whatsapp")
    statement = statement.where(MensajeSalida.id == message_id) if message_id else statement.where(MensajeSalida.proveedor_id == form["MessageSid"])
    item = db.scalar(statement.with_for_update())
    if item is None:
        return
    if item.proveedor_id is None:
        raise HTTPException(503, "El envío todavía está guardando su referencia; reintenta el evento")
    if item.proveedor_id != form["MessageSid"]:
        return  # Callback anterior a un reintento: no cambia la referencia vigente.
    if form.get("To") and form["To"] != f"whatsapp:+{item.destinatario}":
        raise HTTPException(403, "El estado no corresponde al destinatario")
    state = form.get("MessageStatus", "")
    if item.estado != "cancelado":
        if state in {"delivered", "read"} and item.estado != "leido":
            item.estado = "leido" if state == "read" else "entregado"
            item.entregado_en, item.error = item.entregado_en or now(), None
        elif state in {"failed", "undelivered"} and item.estado not in {"entregado", "leido"}:
            try:
                code = int(form.get("ErrorCode") or 0)
            except ValueError:
                code = 0
            item.estado = "pendiente_configuracion" if code in {20003, 21608, 63015, 63016} else "error"
            item.error = twilio_error(code)
            item.proximo_intento = now() + dt.timedelta(minutes=5)
    db.commit()


@router.get("/documents/{message_id}")
@router.head("/documents/{message_id}", include_in_schema=False)
def document(message_id: int, expires: int, signature: str, request: Request, db: Session = Depends(get_db)):
    item = db.get(MensajeSalida, message_id)
    if get_settings().whatsapp_provider != "twilio" or not document_allowed(item, expires, signature):
        raise HTTPException(404, "Documento no disponible")
    return Response(item.documento if request.method == "GET" else b"", media_type="application/pdf", headers={
        "Content-Length": str(len(item.documento)), "Content-Disposition": f'attachment; filename="documento-{item.id}.pdf"',
        "Cache-Control": "private, no-store", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff"})
