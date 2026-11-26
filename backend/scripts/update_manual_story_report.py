"""Registra E34 en la matriz Word existente sin declarar recepción externa ni cambiar estados."""
import argparse
from collections import Counter
import datetime as dt
import hashlib
from pathlib import Path
import re
import shutil
import tempfile
from uuid import uuid4
from xml.dom import minidom
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "Informe_Historias_Usuario_SMP delcy.docx"
TEMP = Path(r"C:\Users\nomad\AppData\Local\Temp\opencode")
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

ADVANCES = {
    "HU-018": ("Fachada real del usuario publicada idempotentemente en el entorno configurado; asset y JPEG local. Verificación de carga, título, imagen completa y vista adaptable en Edge con el asset real.", "Confirmación visual final del usuario de la galería pública. La prueba local no sustituye esa aceptación."),
    "HU-032": ("Recordatorio generado por worker o por Preparar avisos programados ahora. Bandeja manual por rol/sede; contacto y vigencia comprobados antes de abrir WhatsApp.", "Enviar el aviso preparado y acreditar recepción real por el contacto de la reserva. El envío automático del alcance original sigue sin acreditar."),
    "HU-036": ("Cancelación con motivo y aviso manual persistido. Apertura privada del texto hacia el contacto actual, copia y registro de gestión sin alterar cita, pago o stock por abrir el enlace.", "Cancelar una cita de prueba, enviar el aviso desde WhatsApp normal y confirmar recepción por el cliente."),
    "HU-039": ("Mensaje legible con referencia ASISTIRE versionada. Administración registra remitente y referencia; se validan sede, propietario, contacto y horario, se persiste una única asistencia y se notifica al veterinario. Cliente y agendas consultan el mismo dato; referencias obsoletas/manipuladas rechazadas.", "Recibir un mensaje real del propietario y registrar su referencia desde Citas. La recepción es manual; no se acredita lectura automática del chat."),
    "HU-050": ("Bandeja veterinaria para casos propios y derivaciones aceptadas. Descarga autenticada del PDF persistido con código de orden dentro del archivo, apertura del mensaje y gestión auditada. Caja y administración conservan sus accesos autorizados.", "Cerrar atención de prueba y enviar/adjuntar realmente el PDF por WhatsApp; confirmar código de orden y recepción por el cliente."),
    "HU-056": ("Programación con y sin cita y recordatorio manual. Antes de preparar se revalidan vacuna, próxima fecha, clave de aplicación/fecha, propietario, sede, plazo y teléfono; cambio de fecha invalida el aviso anterior.", "Recibir el aviso real de una próxima vacuna con y sin cita, sin duplicación. El envío automático original queda sin acreditar."),
    "HU-066": ("Bandeja de caja con código e importe de la orden. Preparar/copiar/abrir/registrar gestión no valida pago ni crea venta o salida de inventario; se descartan órdenes finalizadas.", "Enviar el código e importe reales a una cuenta de prueba y confirmar recepción y ausencia de efectos financieros por el aviso."),
    "HU-067": ("Enlace del cliente al WhatsApp institucional 938304590 con leyenda de orden. Caja registra el archivo recibido con canal WhatsApp y después lo valida una sola vez; archivo privado y efectos transaccionales conservados.", "Enviar un archivo real con leyenda y registrarlo/revisarlo en caja. La recepción automática por webhook del alcance original sigue sin acreditar."),
    "HU-097": ("Ambos tramos, 24 h y 2 h, se generan sin duplicarse en la cola manual. Revalidación al preparar cancela tramo/horario obsoleto. Pruebas con reloj controlado, sin afirmar espera ni recepción externa reales.", "Enviar y recibir los dos tramos reales y comprobar cancelación/reprogramación. El despacho automático original queda sin acreditar."),
    "HU-098": ("Confirmación, reprogramación y cancelación manuales. Se descarta un aviso si hay un cambio posterior, estado/horario incompatible, atención iniciada o destinatario no vigente; el contacto actual se relee antes de abrirlo.", "Recibir los tres avisos reales con fecha efectiva y sin mensajes obsoletos o duplicados."),
    "HU-099": ("Bienvenida única tras verificar el registro, disponible en la bandeja administrativa manual; reenvíos de verificación no la duplican. Se conserva la revalidación de cliente y teléfono.", "Completar un registro/verificación de prueba con correo operativo y confirmar recepción real de la bienvenida enviada manualmente."),
    "HU-100": ("Seguimiento desde 2 h y antes de 48 h accesible desde caja; pago/abono validado, comprobante en revisión, vencimiento o anulación invalidan el aviso pendiente. La actualización de avisos puede solicitarse desde la interfaz.", "Enviar el seguimiento real durante su ventana y comprobar que no se prepara un aviso obsoleto después de pagar, cargar comprobante o vencer."),
    "HU-101": ("Confirmación de pago total y boleta PDF privadas desde caja, incluidas liquidación de orden, venta directa y aprobación de pedido web. Compatibilidad con referencias históricas pago:<id>; registrar gestión no repite venta ni stock.", "Validar pago real de prueba y enviar/adjuntar confirmación y boleta; confirmar recepción y ausencia de duplicados."),
    "HU-103": ("Próxima vacuna con plazo 0–30 días, atenciones con/sin cita y teléfono actualizado. Fuera del plazo se conserva espera recuperable; fecha vencida, cambio de fecha/tipo o propietario no disponible cancela el aviso.", "Acreditar recepción real en ambos orígenes de atención. La automatización saliente original no se acredita mediante el modo manual."),
    "HU-104": ("Personalización y vista previa de textos manuales, con variables persistidas y permisos. Se conserva el orden de parámetros pendientes y el historial ya gestionado/enviado. El modo elegido usa textos locales, sin aprobación de Meta.", "Aceptar y demostrar el texto personalizado en un envío real del alcance manual. La correspondencia con plantillas aprobadas de Meta del alcance anterior permanece sin acreditar."),
    "HU-105": ("Aviso al veterinario tras aceptación de reprogramación, visible en bandejas autorizadas. Cambio posterior, cancelación o reasignación invalidan el mensaje; el teléfono actual del profesional se normaliza al preparar.", "Recibir un aviso real en el WhatsApp del veterinario, sin duplicados y con horario efectivo correcto."),
    "HU-106": ("Cancelación para el profesional con motivo y validación del estado/último evento/profesional activo. Los avisos previos de reprogramación quedan cancelados si aún no fueron enviados al cambiar el estado.", "Recibir avisos reales por cancelación desde cliente y administración y comprobar motivo y destinatario."),
    "HU-107": ("Aviso de laboratorio sin resultados en el texto, accesible al veterinario del caso o receptor de derivación aceptada. Se conserva el enlace privado para el propietario autenticado y la autorización de archivos.", "Enviar el aviso real y abrir el resultado como propietario desde un FRONTEND_URL accesible en su dispositivo."),
    "HU-108": ("Encuesta única desde 24 h del cierre, también sin cita. Bandeja manual oculta el token en listados; la preparación privada permite enviar el enlace. Respuesta única persistida; aviso respondido o caducado se invalida.", "Recibir el enlace real, responder y comprobar persistencia/uso único con y sin cita. Hace falta un FRONTEND_URL accesible para el destinatario; no se acredita despacho automático."),
}


def children(node, name):
    return [child for child in node.childNodes if child.nodeType == child.ELEMENT_NODE and child.tagName == name]


def text(node):
    return "".join("".join(part.data for part in element.childNodes if part.nodeType == part.TEXT_NODE) for element in node.getElementsByTagName("w:t"))


def write_paragraph(doc, paragraph, value, label=None):
    runs = paragraph.getElementsByTagName("w:r")
    properties = runs[-1].getElementsByTagName("w:rPr") if runs else []
    style = properties[0].cloneNode(True) if properties else None
    for child in list(paragraph.childNodes):
        if child.nodeType == child.ELEMENT_NODE and child.tagName in {"w:r", "w:hyperlink"}:
            paragraph.removeChild(child)
    for content, bold in ([(label, True), (value, False)] if label else [(value, False)]):
        run = doc.createElementNS(W, "w:r")
        if style is not None or bold:
            props = style.cloneNode(True) if style is not None else doc.createElementNS(W, "w:rPr")
            for element in list(props.childNodes):
                if element.nodeType == element.ELEMENT_NODE and element.tagName in {"w:b", "w:bCs"}:
                    props.removeChild(element)
            if bold:
                props.appendChild(doc.createElementNS(W, "w:b"))
            run.appendChild(props)
        value_node = doc.createElementNS(W, "w:t"); value_node.setAttribute("xml:space", "preserve")
        value_node.appendChild(doc.createTextNode(content)); run.appendChild(value_node); paragraph.appendChild(run)


def note(doc, parent, label, value):
    for paragraph in children(parent, "w:p"):
        if text(paragraph).startswith(label):
            write_paragraph(doc, paragraph, value, label); return paragraph
    paragraph = doc.createElementNS(W, "w:p")
    examples = children(parent, "w:p")
    if examples:
        props = children(examples[-1], "w:pPr")
        if props: paragraph.appendChild(props[0].cloneNode(True))
    write_paragraph(doc, paragraph, value, label); parent.appendChild(paragraph)
    return paragraph


def story_rows(doc):
    result = {}
    for table in doc.getElementsByTagName("w:tbl"):
        rows = children(table, "w:tr")
        if not rows or "Identificador" not in text(rows[0]): continue
        for row in rows[1:]:
            cells = children(row, "w:tc")
            found = re.search(r"HU-\d{3}", text(cells[0])) if cells else None
            if found:
                if found[0] in result: raise ValueError("Identificador de historia duplicado")
                result[found[0]] = cells
    return result


def validate(doc):
    rows = story_rows(doc)
    states = Counter()
    for cells in rows.values():
        found = re.search(r"Estado:\s*(Completada|Parcial|Pendiente)", text(cells[1]))
        if not found: raise ValueError("Historia sin estado funcional")
        states[found[1]] += 1
    if len(rows) != 115 or states != Counter({"Completada": 96, "Parcial": 19}):
        raise ValueError("La base del informe cambió; revisa sus estados antes de registrar E34")
    return rows


def update(report, passed, skipped, ui_runs, regressions):
    original_hash = hashlib.sha256(report.read_bytes()).digest()
    with ZipFile(report) as archive:
        infos = archive.infolist(); parts = {info.filename: archive.read(info.filename) for info in infos}
    doc = minidom.parseString(parts["word/document.xml"])
    rows = validate(doc)
    evidence = (f"E34 — 24/11/2026. {passed} pruebas aprobadas y {skipped} omitidas que requieren PostgreSQL de pruebas; Docker no disponible. "
                f"42 casos nuevos en tests/test_manual_story_completion.py; compilación Angular correcta. {ui_runs} recorridos integrados Edge, 1440×1000 y 390×844, "
                f"con frontend compilado, FastAPI/JWT reales, SQLite aislada y asset real de fachada. {regressions} regresiones visuales con API controlada. "
                "Sin envíos externos ni acreditación de recepción WhatsApp. Pendientes finales de aceptación conservados.")
    for identifier, (advance, criterion) in ADVANCES.items():
        cell = rows[identifier][2]
        action = next((p for p in children(cell, "w:p") if text(p).startswith("Siguiente acción / criterio:")), None)
        if action is None: raise ValueError(f"Falta el criterio de {identifier}")
        if not any(text(p).startswith("Criterio anterior a E34:") for p in children(cell, "w:p")):
            note(doc, cell, "Criterio anterior a E34: ", text(action).split(":", 1)[1].strip())
        write_paragraph(doc, action, criterion, "Siguiente acción / criterio: ")
        note(doc, cell, "Avance E34 — 24/11/2026: ", advance)
        note(doc, cell, "Evidencia E34: ", evidence)
    body = doc.getElementsByTagName("w:body")[0]
    for paragraph in children(body, "w:p"):
        value = text(paragraph)
        if value.startswith("Versión 3."):
            write_paragraph(doc, paragraph, "Versión 3.18 — Operación WhatsApp manual y validación de historias | Actualización: 24 de noviembre de 2026")
        elif value.startswith("Base consolidada actual:"):
            write_paragraph(doc, paragraph, "Base consolidada actual: 96 completadas, 19 parciales y 0 pendientes (115). E34 incorpora el alcance manual elegido por el usuario, WhatsApp institucional 938304590, asistencia persistida, bandejas por rol/sede y validación de avisos. Las 19 filas conservan Parcial hasta sus pruebas reales o aceptación final; la generación local y la gestión manual no acreditan entrega automática.")
    heading = next((p for p in children(body, "w:p") if re.match(r"8\.", text(p))), None)
    marker = heading or children(body, "w:tbl")[-1]
    for label, value in [("E34 — WhatsApp manual y validación funcional: ", "El usuario eligió la opción 2 (envío manual con WhatsApp normal) y proporcionó 938304590. Se conservan los textos originales de las historias y sus estados; se documenta el alcance manual y las brechas finales, sin declarar entrega externa."),
                         ("E34 — Implementación y pruebas: ", evidence),
                         ("E34 — Rutas de evidencia: ", "backend/tests/test_manual_story_completion.py; backend/scripts/check_manual_stories_ui.py; backend/app/services/manual_access_service.py; backend/app/services/notice_validity_service.py; backend/GUIA_WHATSAPP_MANUAL.md; frontend/src/app/features/messaging/manual-inbox.component.ts.")]:
        existing = next((p for p in children(body, "w:p") if text(p).startswith(label)), None)
        if existing: write_paragraph(doc, existing, value, label)
        else:
            paragraph = doc.createElementNS(W, "w:p"); write_paragraph(doc, paragraph, value, label); body.insertBefore(paragraph, marker)
    tables = children(body, "w:tbl")
    journal = next(table for table in tables if "Historias / cambio" in text(children(table, "w:tr")[0]))
    existing = next((row for row in children(journal, "w:tr")[1:] if "Versión 3.18 / E34" in text(row)), None)
    row = existing or children(journal, "w:tr")[-1].cloneNode(True)
    for cell, value in zip(children(row, "w:tc"), ["24/11/2026", "Versión 3.18 / E34: alcance manual elegido, contacto 938304590, asistencia registrada, bandejas por rol y avisos revalidados; actualización de las 19 parciales.", f"96 completadas, 19 parciales y 0 pendientes. {passed} pruebas aprobadas/{skipped} omitidas; {ui_runs} recorridos Edge integrados y {regressions} comprobaciones con API controlada. Recepción externa y confirmación final de galería pendientes."]):
        paragraphs = children(cell, "w:p")
        paragraph = paragraphs[0] if paragraphs else doc.createElementNS(W, "w:p")
        for extra in paragraphs[1:]: cell.removeChild(extra)
        if not paragraphs: cell.appendChild(paragraph)
        write_paragraph(doc, paragraph, value)
    if existing is None: journal.appendChild(row)
    validate(doc)
    parts["word/document.xml"] = doc.toxml(encoding="UTF-8", standalone=True)
    if "docProps/core.xml" in parts:
        core = minidom.parseString(parts["docProps/core.xml"])
        modified = core.getElementsByTagName("dcterms:modified")
        if modified:
            modified[0].firstChild.data = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        parts["docProps/core.xml"] = core.toxml(encoding="UTF-8", standalone=True)
    if not TEMP.is_dir(): raise ValueError("No está disponible la carpeta temporal autorizada")
    if hashlib.sha256(report.read_bytes()).digest() != original_hash:
        raise ValueError("El informe cambió durante la preparación; vuelve a revisarlo antes de actualizar")
    backup = TEMP / f"informe-historias-pre-E34-{uuid4().hex}.docx"
    shutil.copy2(report, backup)
    with tempfile.NamedTemporaryFile(dir=report.parent, suffix=".docx", delete=False) as output:
        temporary = Path(output.name)
    try:
        with ZipFile(temporary, "w") as archive:
            for info in infos: archive.writestr(info, parts[info.filename])
        with ZipFile(temporary) as archive:
            if archive.testzip() is not None: raise ValueError("El paquete Word no pasó la verificación ZIP")
            validate(minidom.parseString(archive.read("word/document.xml")))
        if hashlib.sha256(report.read_bytes()).digest() != original_hash:
            raise ValueError("El informe cambió antes de guardarlo; se conservó el archivo del usuario")
        temporary.replace(report)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Word actualizado: {report.name}. 115 historias; 96 completadas, 19 parciales, 0 pendientes.")
    print(f"Copia previa: {backup}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--passed", required=True, type=int)
    parser.add_argument("--skipped", required=True, type=int)
    parser.add_argument("--ui-runs", required=True, type=int)
    parser.add_argument("--ui-regressions", required=True, type=int)
    args = parser.parse_args()
    update(REPORT, args.passed, args.skipped, args.ui_runs, args.ui_regressions)
