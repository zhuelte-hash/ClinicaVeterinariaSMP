import hashlib
import hmac
import json
import re

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.clinic import Cita, EstadoCita
from app.models.operations import EncuestaConsulta, MensajeEntrante, MensajeSalida, OrdenPendiente
from app.models.user import Usuario
from app.schemas.operations import InstallmentWrite, RescheduleRequest, SurveyAnswer
from app.security import require_permission
from app.services.access_service import aware, digest, now
from app.services.automation_service import run_automations
from app.services.billing_service import BillingService
from app.routers.clinical_operations import request_reschedule

router = APIRouter(tags=["Mensajería y encuestas"])


@router.get("/whatsapp/webhook")
def verify_webhook(mode: str = Query(alias="hub.mode"), token: str = Query(alias="hub.verify_token"), challenge: str = Query(alias="hub.challenge")):
    expected = get_settings().whatsapp_verify_token
    if mode != "subscribe" or not expected or not hmac.compare_digest(token, expected):
        raise HTTPException(403, "Verificación no autorizada")
    return Response(challenge, media_type="text/plain")


def normalized_phone(value):
    digits = "".join(filter(str.isdigit, value or ""))
    return "51" + digits if len(digits) == 9 else digits


async def receive_message(message, db):
    message_id = message["id"]
    if db.scalar(select(MensajeEntrante.id).where(MensajeEntrante.proveedor_id == message_id)):
        return
    phone = normalized_phone(message.get("from", ""))
    kind = message.get("type", "")
    caption = message.get("text", {}).get("body", "") if kind == "text" else message.get(kind, {}).get("caption", "")
    item = MensajeEntrante(proveedor_id=message_id, telefono=phone, contenido=caption)
    db.add(item)
    try:
        confirmation = re.search(r"ASISTIR[EÉ]\s+(\d+)", caption, re.I)
        reschedule = re.search(r"REPROGRAMAR\s+(\d+)\s+(\S+)", caption, re.I)
        if confirmation or reschedule:
            appointment_id = int((confirmation or reschedule)[1])
            appointment = db.scalar(select(Cita).where(Cita.id == appointment_id).execution_options(skip_branch_filter=True).with_for_update())
            if appointment is None or normalized_phone(appointment.telefono_contacto or appointment.mascota.cliente.usuario.telefono) != phone:
                raise HTTPException(403, "No se pudo vincular el remitente a la cita")
            db.info["sucursal_id"] = appointment.sucursal_id
            db.info["actor_id"] = appointment.mascota.cliente_id
            if confirmation:
                if appointment.estado not in {EstadoCita.CONFIRMADA, EstadoCita.REPROGRAMADA}:
                    raise HTTPException(409, "La cita no admite confirmación de asistencia")
                appointment.asistencia_confirmada_en = appointment.asistencia_confirmada_en or now()
                item.resultado = "asistencia_confirmada"
            else:
                request_reschedule(db, appointment.mascota.cliente.usuario, appointment.id, RescheduleRequest(fecha_propuesta=reschedule[2], motivo="Solicitado por WhatsApp", canal="whatsapp"))
                item.resultado = "reprogramacion_solicitada"
        elif kind in {"image", "document"}:
            code = re.search(r"OC-[A-F0-9]{12}", caption, re.I)
            amount = re.search(r"MONTO\s*[=:]\s*(\d+(?:\.\d{1,2})?)", caption, re.I)
            method = re.search(r"MEDIO\s*[=:]\s*(yape|plin|transferencia|tarjeta)", caption, re.I)
            operation = re.search(r"OPERACION\s*[=:]\s*([A-Za-z0-9-]+)", caption, re.I)
            if not code or not amount or not method:
                raise HTTPException(422, "Incluye OC-código, MONTO=importe y MEDIO=yape/plin/transferencia/tarjeta en la leyenda")
            order = db.scalar(select(OrdenPendiente).where(OrdenPendiente.codigo == code[0].upper()).execution_options(skip_branch_filter=True))
            owner = db.get(Usuario, order.cliente_id) if order else None
            if owner is None or normalized_phone(owner.telefono) != phone:
                raise HTTPException(403, "El remitente no corresponde al propietario de la orden")
            settings = get_settings()
            headers = {"Authorization": f"Bearer {settings.whatsapp_access_token}"}
            media = httpx.get(f"{settings.whatsapp_api_url}/{message[kind]['id']}", headers=headers, timeout=20)
            media.raise_for_status()
            metadata = media.json()
            if metadata.get("file_size", 0) > 5 * 1024 * 1024:
                raise HTTPException(422, "El comprobante supera los 5 MB")
            content = httpx.get(metadata["url"], headers=headers, timeout=20)
            content.raise_for_status()
            db.info["sucursal_id"] = order.sucursal_id
            data = InstallmentWrite(monto=amount[1], medio=method[1].lower(), codigo_operacion=operation[1] if operation else None, canal="whatsapp", clave_idempotencia=f"wa:{message_id}")
            BillingService(db).add_payment(owner, order.id, data, content.content, commit=False)
            item.resultado = f"comprobante_vinculado:{order.codigo}"
        else:
            item.resultado = "mensaje_registrado_sin_comando"
        db.commit()
    except HTTPException as exc:
        db.rollback()
        db.add(MensajeEntrante(proveedor_id=message_id, telefono=phone, contenido=caption, resultado=str(exc.detail)[:500]))
        db.commit()


@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    secret = get_settings().whatsapp_app_secret
    if not secret:
        raise HTTPException(503, "Configura WHATSAPP_APP_SECRET")
    body = await request.body()
    if len(body) > 2 * 1024 * 1024:
        raise HTTPException(413, "Evento demasiado grande")
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(request.headers.get("X-Hub-Signature-256", ""), expected):
        raise HTTPException(403, "Firma de evento inválida")
    try:
        payload = json.loads(body)
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for status in value.get("statuses", []):
                    item = db.scalar(select(MensajeSalida).where(MensajeSalida.proveedor_id == status["id"]))
                    if item:
                        state = status.get("status")
                        if state in {"delivered", "read"}:
                            item.estado, item.entregado_en = "entregado" if state == "delivered" else "leido", now()
                        elif state == "failed":
                            item.estado, item.error = "error", "El proveedor informó un fallo de entrega"
                db.commit()
                for message in value.get("messages", []):
                    await receive_message(message, db)
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(422, "Evento inválido") from exc
    return {"ok": True}


@router.post("/admin/operaciones/automatizaciones", dependencies=[Depends(require_permission("usuarios", "editar"))])
def automation_cycle(db: Session = Depends(get_db)):
    return run_automations(db)


@router.get("/encuestas/{token}")
def survey(token: str, db: Session = Depends(get_db)):
    item = db.scalar(select(EncuestaConsulta).where(EncuestaConsulta.token_hash == digest(token)))
    if item is None or aware(item.expira_en) < now():
        raise HTTPException(404, "La encuesta no existe o ha caducado")
    return {"respondida": item.respondida_en is not None, "pregunta": "¿Cómo calificarías la atención recibida?", "escala": "1: muy mala; 5: excelente"}


@router.post("/encuestas/{token}", status_code=204)
def answer_survey(token: str, data: SurveyAnswer, db: Session = Depends(get_db)):
    item = db.scalar(select(EncuestaConsulta).where(EncuestaConsulta.token_hash == digest(token)).with_for_update())
    if item is None or aware(item.expira_en) < now() or item.respondida_en:
        raise HTTPException(409, "La encuesta caducó o ya fue respondida")
    item.valoracion, item.comentario, item.respondida_en = data.valoracion, data.comentario, now()
    db.commit()
