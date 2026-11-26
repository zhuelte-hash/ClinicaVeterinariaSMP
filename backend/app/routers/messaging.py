import hashlib
import datetime as dt
import hmac
import json
import re

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.clinic import Cita, EstadoCita, Notificacion
from app.models.operations import EncuestaConsulta, MensajeEntrante, MensajeSalida, OrdenPendiente
from app.models.user import Usuario
from app.schemas.operations import InstallmentWrite, RescheduleRequest, SurveyAnswer
from app.security import require_permission, check_permission
from app.services.access_service import aware, digest, now
from app.services.automation_service import run_automations
from app.services.billing_service import BillingService
from app.routers.clinical_operations import request_reschedule
from app.services.policy_service import ZONE

router = APIRouter(tags=["Mensajería y encuestas"])


@router.get("/whatsapp/webhook")
def verify_webhook(mode: str = Query(alias="hub.mode"), token: str = Query(alias="hub.verify_token"), challenge: str = Query(alias="hub.challenge")):
    if get_settings().whatsapp_provider == "manual":
        raise HTTPException(503, "Modo manual: las respuestas se revisan directamente en WhatsApp")
    expected = get_settings().whatsapp_verify_token
    if mode != "subscribe" or not expected or not hmac.compare_digest(token, expected):
        raise HTTPException(403, "Verificación no autorizada")
    return Response(challenge, media_type="text/plain")


def normalized_phone(value):
    digits = "".join(filter(str.isdigit, value or ""))
    return "51" + digits if len(digits) == 9 else digits


def download_whatsapp_proof(media_id):
    """Limita también la descarga real: el tamaño declarado por Meta no basta."""
    settings = get_settings()
    headers = {"Authorization": f"Bearer {settings.whatsapp_access_token}"}
    metadata = httpx.get(f"{settings.whatsapp_api_url}/{media_id}", headers=headers, timeout=20)
    metadata.raise_for_status()
    info = metadata.json()
    maximum = 5 * 1024 * 1024
    if info.get("file_size", 0) > maximum:
        raise HTTPException(422, "El comprobante supera los 5 MB")
    if info.get("mime_type") not in {"image/jpeg", "image/png", "application/pdf"}:
        raise HTTPException(422, "Adjunta un comprobante JPG, PNG o PDF")
    with httpx.stream("GET", info["url"], headers=headers, timeout=20) as response:
        response.raise_for_status()
        content = bytearray()
        for chunk in response.iter_bytes():
            if len(content) + len(chunk) > maximum:
                raise HTTPException(422, "El comprobante supera los 5 MB")
            content.extend(chunk)
    return bytes(content)


async def receive_message(message, db, *, download_proof=None):
    message_id = message["id"]
    if db.scalar(select(MensajeEntrante.id).where(MensajeEntrante.proveedor_id == message_id)):
        return
    phone = normalized_phone(message.get("from", ""))
    kind = message.get("type", "")
    caption = message.get("text", {}).get("body", "") if kind == "text" else message.get(kind, {}).get("caption", "")
    item = MensajeEntrante(proveedor_id=message_id, telefono=phone, contenido=caption, fecha=now())
    db.add(item)
    try:
        confirmation = re.fullmatch(r"\s*ASISTIR[EÉ]\s+(\d+)(?:\s+([A-Za-z0-9_-]+))?\s*", caption, re.I)
        reschedule = re.search(r"REPROGRAMAR\s+(\d+)\s+(\S+)", caption, re.I)
        if confirmation or reschedule:
            appointment_id = int((confirmation or reschedule)[1])
            appointment = db.scalar(select(Cita).where(Cita.id == appointment_id).execution_options(skip_branch_filter=True).with_for_update())
            if appointment is None or normalized_phone(appointment.telefono_contacto or appointment.mascota.cliente.usuario.telefono) != phone:
                raise HTTPException(403, "No se pudo vincular el remitente a la cita")
            db.info["sucursal_id"] = appointment.sucursal_id
            db.info["actor_id"] = appointment.mascota.cliente_id
            if confirmation:
                owner = appointment.mascota.cliente.usuario
                if not owner.activo or not owner.correo_verificado:
                    raise HTTPException(403, "La cuenta del propietario no está activa y verificada")
                from app.services.attendance_service import attendance_code, schedule_event
                if confirmation[2]:
                    if not hmac.compare_digest(confirmation[2].lower(), attendance_code(db, appointment)):
                        raise HTTPException(409, "El horario o contacto cambió; prepara una nueva confirmación desde Mis citas")
                elif message.get("timestamp"):
                    event = schedule_event(db, appointment)
                    if event and int(message["timestamp"]) < int(aware(event.fecha).timestamp()):
                        raise HTTPException(409, "El mensaje es anterior al último horario; vuelve a confirmar la cita actual")
                check_permission(db, owner, "citas", "editar")
                scheduled = aware(appointment.fecha_hora_programada)
                if (appointment.estado not in {EstadoCita.CONFIRMADA, EstadoCita.REPROGRAMADA}
                        or appointment.proceso_atencion is not None or appointment.fecha_hora_llegada is not None
                        or scheduled <= now() or scheduled.astimezone(ZONE).date() > now().astimezone(ZONE).date() + dt.timedelta(days=1)):
                    raise HTTPException(409, "La cita no admite confirmación de asistencia")
                if appointment.asistencia_confirmada_en is None and appointment.veterinario_id:
                    db.add(Notificacion(usuario_id=appointment.veterinario_id, cita_id=appointment.id, tipo="asistencia_confirmada", titulo="Asistencia confirmada por WhatsApp", mensaje=f"El propietario de {appointment.mascota.nombre} confirmó asistencia a la cita #{appointment.id}."))
                appointment.asistencia_confirmada_en = appointment.asistencia_confirmada_en or now()
                item.resultado = "asistencia_confirmada"
            else:
                request_reschedule(db, appointment.mascota.cliente.usuario, appointment.id, RescheduleRequest(fecha_propuesta=reschedule[2], motivo="Solicitado por WhatsApp", canal="whatsapp"))
                item.resultado = "reprogramacion_solicitada"
        elif kind in {"image", "document"}:
            code = re.search(r"\bOC-[A-F0-9]{12}\b", caption, re.I)
            amount = re.search(r"\bMONTO\s*[=:]\s*(\d+(?:\.\d{1,2})?)(?=\s|$)", caption, re.I)
            method = re.search(r"\bMEDIO\s*[=:]\s*(yape|plin|transferencia|tarjeta)(?=\s|$)", caption, re.I)
            operation = re.search(r"\bOPERACION\s*[=:]\s*([A-Za-z0-9-]+)(?=\s|$)", caption, re.I)
            if not code or not amount or not method:
                raise HTTPException(422, "Incluye OC-código, MONTO=importe y MEDIO=yape/plin/transferencia/tarjeta en la leyenda")
            order = db.scalar(select(OrdenPendiente).where(OrdenPendiente.codigo == code[0].upper()).execution_options(skip_branch_filter=True))
            owner = db.get(Usuario, order.cliente_id) if order else None
            if owner is None or normalized_phone(owner.telefono) != phone:
                raise HTTPException(403, "El remitente no corresponde al propietario de la orden")
            if not owner.activo:
                raise HTTPException(403, "La cuenta del propietario está desactivada")
            db.info["sucursal_id"] = order.sucursal_id
            db.info["actor_id"] = owner.id
            check_permission(db, owner, "ventas", "crear")
            data = InstallmentWrite(monto=amount[1], medio=method[1].lower(), codigo_operacion=operation[1] if operation else None, canal="whatsapp", clave_idempotencia=f"wa:{message_id}")
            content = (download_proof or download_whatsapp_proof)(message[kind]["id"])
            BillingService(db).add_payment(owner, order.id, data, content, commit=False)
            item.resultado = f"comprobante_vinculado:{order.codigo}"
        else:
            item.resultado = "mensaje_registrado_sin_comando"
        db.commit()
    except httpx.HTTPError as exc:
        db.rollback()
        # Sin registrar el ID como procesado: Meta puede volver a entregar el evento.
        raise HTTPException(503, "No se pudo descargar el comprobante; vuelve a entregar el evento") from exc
    except IntegrityError:
        db.rollback()
        if db.scalar(select(MensajeEntrante.id).where(MensajeEntrante.proveedor_id == message_id)):
            return
        raise
    except (ValueError, KeyError, TypeError) as exc:
        db.rollback()
        db.add(MensajeEntrante(proveedor_id=message_id, telefono=phone, contenido=caption, resultado="Comprobante o comando inválido; revisa formato y archivo"))
        db.commit()
    except HTTPException as exc:
        db.rollback()
        db.add(MensajeEntrante(proveedor_id=message_id, telefono=phone, contenido=caption, resultado=str(exc.detail)[:500]))
        db.commit()


@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    if get_settings().whatsapp_provider == "manual":
        raise HTTPException(503, "Modo manual: las respuestas y comprobantes se registran por el personal")
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
                receiver = value.get("metadata", {}).get("phone_number_id")
                configured_receiver = get_settings().whatsapp_phone_number_id
                if receiver and configured_receiver and receiver != configured_receiver:
                    raise HTTPException(403, "El evento no corresponde al número WhatsApp de la clínica")
                for status in value.get("statuses", []):
                    item = db.scalar(select(MensajeSalida).where(MensajeSalida.proveedor_id == status["id"]))
                    if item:
                        state = status.get("status")
                        if state in {"delivered", "read"} and item.estado != "leido":
                            item.estado = "entregado" if state == "delivered" else "leido"
                            item.entregado_en = item.entregado_en or now()
                            item.error = None
                        elif state == "failed" and item.estado not in {"entregado", "leido"}:
                            item.estado, item.error = "error", "El proveedor informó un fallo de entrega"
                db.commit()
                for message in value.get("messages", []):
                    await receive_message(message, db)
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(422, "Evento inválido") from exc
    return {"ok": True}


@router.post("/admin/operaciones/automatizaciones", dependencies=[Depends(require_permission("usuarios", "editar"))])
def automation_cycle(db: Session = Depends(get_db)):
    return run_automations(db, manual_button=get_settings().whatsapp_provider == "manual")


@router.get("/encuestas/{token}")
def survey(token: str, response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    item = db.scalar(select(EncuestaConsulta).where(EncuestaConsulta.token_hash == digest(token)))
    if item is None or aware(item.expira_en) <= now():
        raise HTTPException(404, "La encuesta no existe o ha caducado")
    return {"respondida": item.respondida_en is not None, "pregunta": "¿Cómo calificarías la atención recibida?", "escala": "1: muy mala; 5: excelente"}


@router.post("/encuestas/{token}", status_code=204)
def answer_survey(token: str, data: SurveyAnswer, response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "private, no-store"
    item = db.scalar(select(EncuestaConsulta).where(EncuestaConsulta.token_hash == digest(token)).with_for_update())
    if item is None or aware(item.expira_en) <= now() or item.respondida_en:
        raise HTTPException(409, "La encuesta caducó o ya fue respondida")
    item.valoracion, item.comentario, item.respondida_en = data.valoracion, data.comentario, now()
    db.commit()
