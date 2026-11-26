"""Registra el alcance E35 por botones, conservando estados y el resto del Word."""
import argparse
import datetime as dt
import hashlib
from pathlib import Path
import shutil
import sys
import tempfile
from uuid import uuid4
from xml.dom import minidom
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.update_manual_story_report import REPORT, TEMP, W, children, note, text, validate, write_paragraph

STORIES = {
    "HU-032": ("Como personal de la clínica, quiero preparar y enviar con un botón el recordatorio previo de cita por WhatsApp.",
               "Preparar avisos programados ahora y enviar el recordatorio vigente; el cliente recibe mascota, fecha y referencia completa de asistencia."),
    "HU-036": ("Como cliente, quiero cancelar una cita con motivo y recibir la confirmación que el personal envía mediante el botón de WhatsApp.",
               "Cancelar una cita de prueba y enviar desde WhatsApp de esta cita; comprobar recepción del motivo correcto."),
    "HU-039": ("Como cliente, quiero confirmar por WhatsApp mi asistencia con el mensaje preparado por un botón, para que administración registre la respuesta recibida.",
               "Responder ASISTIRE con id y código vigente del recordatorio o portal; Registrar asistencia recibida persiste una confirmación visible en las agendas, sin duplicados."),
    "HU-050": ("Como veterinario, quiero emitir receta y orden de pago y usar los botones de WhatsApp y descarga del PDF para enviarlas al cliente.",
               "Cerrar la atención con cita, abrir su bandeja, descargar y adjuntar el PDF; verificar recepción y código de una orden única."),
    "HU-056": ("Como veterinario, quiero programar la próxima vacuna y disponer de su recordatorio para enviarlo por WhatsApp con un botón.",
               "Preparar y enviar la próxima vacuna con y sin cita dentro del plazo; verificar fecha, propietario y ausencia de duplicados."),
    "HU-066": ("Como personal de caja, quiero enviar mediante un botón de WhatsApp el código e importe de la orden de cobro.",
               "Abrir el WhatsApp de una orden nueva, enviar y comprobar código e importe; preparar o gestionar el mensaje no registra pago ni movimiento de stock."),
    "HU-067": ("Como cliente, quiero abrir WhatsApp con la leyenda de mi orden y adjuntar mi comprobante, para que caja lo cargue y valide con sus botones.",
               "Enviar un JPG/PNG/PDF con la leyenda preparada; caja registra el archivo recibido con canal WhatsApp y valida sus efectos una sola vez."),
    "HU-097": ("Como personal de la clínica, quiero preparar con un botón los recordatorios de 24 h y 2 h y enviarlos manualmente por WhatsApp.",
               "Preparar y enviar cada tramo dentro de su ventana; comprobar referencia completa y rechazo del aviso obsoleto tras cancelar o reprogramar."),
    "HU-098": ("Como personal de la clínica, quiero enviar por botones de WhatsApp los avisos de cita confirmada, reprogramada o cancelada.",
               "Recibir los tres avisos con su horario efectivo; los mensajes anteriores incompatibles dejan de prepararse y no se duplican."),
    "HU-099": ("Como administrador, quiero que el alta de un cliente prepare una bienvenida para enviarla mediante el botón de WhatsApp.",
               "Clientes → Nuevo cliente → Enviar bienvenida por WhatsApp; comprobar recepción y una sola bienvenida. El alta administrativa no depende de SMTP; el registro público conserva correo verificado."),
    "HU-100": ("Como personal de caja, quiero preparar y enviar con un botón de WhatsApp el seguimiento de una orden sin comprobante desde las dos horas.",
               "Enviar dentro de la ventana de 2 a menos de 48 horas; comprobar que pago, comprobante en revisión o vencimiento invalidan el aviso pendiente."),
    "HU-101": ("Como personal de caja, quiero enviar con botones la confirmación del pago total y descargar la boleta para adjuntarla por WhatsApp.",
               "Comprobar recepción de confirmación y PDF después del pago total en orden, venta directa identificada y pedido web aprobado; la gestión del mensaje no repite venta ni stock."),
    "HU-103": ("Como personal de la clínica, quiero preparar las próximas vacunas según su plazo y enviarlas mediante botones de WhatsApp.",
               "Probar atención con cita y sin cita; verificar plazo, contacto actualizado y rechazo del aviso anterior después de cambiar la próxima fecha."),
    "HU-104": ("Como administrador, quiero personalizar textos locales de WhatsApp y aplicarlos al preparar mensajes pendientes mediante botones.",
               "Guardar el texto y sus variables, consultar vista previa y preparar/enviar un aviso pendiente con el texto actual; conservar el contenido de los mensajes ya gestionados."),
    "HU-105": ("Como personal autorizado, quiero enviar con un botón de WhatsApp al veterinario el aviso de una reprogramación aceptada por el cliente.",
               "Cliente acepta la propuesta y el profesional recibe el horario efectivo correcto; comprobar ausencia de duplicados y vigencia del profesional/contacto."),
    "HU-106": ("Como personal autorizado, quiero avisar al veterinario de una cancelación mediante el botón de WhatsApp.",
               "Cancelar desde cliente y administración y enviar los avisos al profesional correcto con cada motivo."),
    "HU-107": ("Como veterinario, quiero usar el botón de WhatsApp para avisar al cliente de resultados disponibles mediante un enlace a su cuenta.",
               "Preparar y enviar el aviso de laboratorio desde la atención; el enlace usa la dirección actual de la aplicación y permite consultar como propietario autenticado."),
    "HU-108": ("Como personal de la clínica, quiero preparar desde un botón la encuesta de una atención cerrada hace al menos 24 horas y enviarla por WhatsApp.",
               "Preparar y enviar la encuesta con y sin cita; abrir el enlace de la aplicación actual, responder y comprobar persistencia y rechazo de una segunda respuesta."),
}


def update(report, passed, skipped, ui_runs):
    if not TEMP.is_dir():
        raise ValueError("No está disponible el directorio temporal de respaldo")
    original = report.read_bytes()
    original_hash = hashlib.sha256(original).digest()
    with ZipFile(report) as archive:
        infos = archive.infolist()
        parts = {info.filename: archive.read(info.filename) for info in infos}
    doc = minidom.parseString(parts["word/document.xml"])
    rows = validate(doc)
    unrelated = {key: [text(cell) for cell in cells] for key, cells in rows.items() if key not in STORIES}
    database_evidence = (f"{skipped} omitidas dependientes de PostgreSQL de pruebas. " if skipped
                         else "0 omitidas y 0 fallos, con PostgreSQL 15 temporal en Docker y migraciones hasta 20261124_27; contenedor y red eliminados, limpieza verificada. ")
    evidence = (f"E35 — 25/11/2026. {passed} pruebas backend aprobadas; " + database_evidence +
                f"13 casos nuevos en tests/test_whatsapp_buttons.py. Compilación Angular correcta; {ui_runs} recorridos Edge integrados "
                "en 1440×1000 y 390×844 con frontend, API/JWT y SQLite aislada: filtros contextuales, apertura por botón, copia, PDF, asistencia y encuesta. "
                "Implementación lista para prueba del usuario; recepción real pendiente de esa prueba.")
    for identifier, (definition, criterion) in STORIES.items():
        cells = rows[identifier]
        paragraph = next((p for p in children(cells[1], "w:p") if text(p).startswith("Como ")), None)
        if paragraph is None:
            raise ValueError(f"No se encontró la descripción de {identifier}")
        if not any(text(p).startswith("Alcance anterior a E35:") for p in children(cells[2], "w:p")):
            note(doc, cells[2], "Alcance anterior a E35: ", text(paragraph))
        write_paragraph(doc, paragraph, definition)
        action = next((p for p in children(cells[2], "w:p") if text(p).startswith("Siguiente acción / criterio:")), None)
        if action is None:
            raise ValueError(f"No se encontró el criterio de {identifier}")
        if not any(text(p).startswith("Criterio anterior a E35:") for p in children(cells[2], "w:p")):
            note(doc, cells[2], "Criterio anterior a E35: ", text(action).split(":", 1)[1].strip())
        write_paragraph(doc, action, criterion, "Siguiente acción / criterio: ")
        note(doc, cells[2], "Implementación E35: ", "Completa en el alcance de WhatsApp por botones confirmado por el usuario. Estado de aceptación: pendiente de su prueba posterior. Guía: backend/PRUEBAS_WHATSAPP_BOTONES.md.")
        note(doc, cells[2], "Evidencia E35: ", evidence)

    body = doc.getElementsByTagName("w:body")[0]
    for paragraph in children(body, "w:p"):
        if text(paragraph).startswith("Versión 3."):
            write_paragraph(doc, paragraph, "Versión 3.19 — WhatsApp por botones, listo para prueba de usuario | Actualización: 25 de noviembre de 2026")
        elif text(paragraph).startswith("Base consolidada actual:"):
            write_paragraph(doc, paragraph, "Base consolidada actual: 96 completadas, 19 parciales y 0 pendientes (115), por aceptación. E35 entrega las 18 historias de WhatsApp implementadas con botones y envío humano, listas para el test posterior del usuario. Las filas conservan Parcial hasta registrar ese test. HU-018 mantiene su aceptación independiente.")
    scope = "El usuario confirmó WhatsApp solo con botones, para hacer el test después. El alcance vigente es preparación, apertura/copia, descarga y adjunto humano de PDF, registro administrativo de asistencia y carga/revisión del comprobante por caja. Los criterios anteriores de automatización se conservan como antecedentes."
    for label, value in [("E35 — Alcance confirmado y entrega: ", scope), ("E35 — Verificación técnica: ", evidence)]:
        existing = next((p for p in children(body, "w:p") if text(p).startswith(label)), None)
        if existing is not None:
            write_paragraph(doc, existing, value, label)
        else:
            paragraph = doc.createElementNS(W, "w:p")
            write_paragraph(doc, paragraph, value, label)
            first_table = children(body, "w:tbl")[0]
            body.insertBefore(paragraph, first_table)

    journal = next(table for table in children(body, "w:tbl") if "Historias / cambio" in text(children(table, "w:tr")[0]))
    existing = next((row for row in children(journal, "w:tr")[1:] if "Versión 3.19 / E35" in text(row)), None)
    row = existing if existing is not None else children(journal, "w:tr")[-1].cloneNode(True)
    values = ["25/11/2026", "Versión 3.19 / E35: alcance por botones de las 18 historias de WhatsApp; implementación completa y lista para la prueba posterior del usuario.", evidence]
    for cell, value in zip(children(row, "w:tc"), values):
        paragraphs = children(cell, "w:p")
        if not paragraphs:
            raise ValueError("La tabla de cambios tiene una celda incompatible")
        for extra in paragraphs[1:]:
            cell.removeChild(extra)
        write_paragraph(doc, paragraphs[0], value)
    if existing is None:
        journal.appendChild(row)
    final_rows = validate(doc)
    if unrelated != {key: [text(cell) for cell in cells] for key, cells in final_rows.items() if key not in STORIES}:
        raise ValueError("Se detectó un cambio ajeno a las historias de WhatsApp")
    parts["word/document.xml"] = doc.toxml(encoding="UTF-8", standalone=True)
    if "docProps/core.xml" in parts:
        core = minidom.parseString(parts["docProps/core.xml"])
        modified = core.getElementsByTagName("dcterms:modified")
        if modified and modified[0].firstChild:
            modified[0].firstChild.data = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        parts["docProps/core.xml"] = core.toxml(encoding="UTF-8", standalone=True)
    if hashlib.sha256(report.read_bytes()).digest() != original_hash:
        raise ValueError("El Word cambió durante la preparación")
    backup = TEMP / f"informe-historias-pre-E35-{uuid4().hex}.docx"
    shutil.copy2(report, backup)
    with tempfile.NamedTemporaryFile(dir=report.parent, suffix=".docx", delete=False) as output:
        temporary = Path(output.name)
    try:
        with ZipFile(temporary, "w") as archive:
            for info in infos:
                archive.writestr(info, parts[info.filename])
        with ZipFile(temporary) as archive:
            if archive.testzip() is not None:
                raise ValueError("El Word no pasó la validación ZIP")
            validate(minidom.parseString(archive.read("word/document.xml")))
        if hashlib.sha256(report.read_bytes()).digest() != original_hash:
            raise ValueError("El Word cambió antes del guardado")
        temporary.replace(report)
    finally:
        temporary.unlink(missing_ok=True)
    print("Word E35 actualizado: 18 historias implementadas por botones, con prueba de usuario pendiente; 115 historias conservadas.")
    print(f"Respaldo anterior: {backup}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--passed", required=True, type=int)
    parser.add_argument("--skipped", required=True, type=int)
    parser.add_argument("--ui-runs", required=True, type=int)
    args = parser.parse_args()
    update(REPORT, args.passed, args.skipped, args.ui_runs)
