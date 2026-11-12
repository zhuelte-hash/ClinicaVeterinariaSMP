from html import escape
from io import BytesIO


def make_pdf(title, lines, table=None):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    output = BytesIO()
    styles = getSampleStyleSheet()
    content = [Paragraph("Clínica Veterinaria San Martín de Porres", styles["Heading2"]), Paragraph(escape(title), styles["Title"])]
    for line in lines:
        content.extend([Paragraph(escape(str(line)).replace("\n", "<br/>"), styles["BodyText"]), Spacer(1, 7)])
    if table:
        rows = [[Paragraph(escape(str(cell or "—")), styles["BodyText"]) for cell in row] for row in table]
        grid = Table(rows, repeatRows=1, hAlign="LEFT")
        grid.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d9f3f4")), ("GRID", (0, 0), (-1, -1), .4, colors.lightgrey), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 6)]))
        content.append(grid)
    SimpleDocTemplate(output, pagesize=A4, title=title, author="Clínica SMP", leftMargin=35, rightMargin=35).build(content)
    return output.getvalue()


def receipt_pdf(receipt):
    return make_pdf(f"Comprobante {receipt.serie_correlativo}", [f"Orden: {receipt.codigo_orden}", f"Cliente: {receipt.cliente_nombre or 'Público general'}", f"Fecha: {receipt.fecha_emision}", f"Estado: {receipt.estado}", f"Total: S/ {receipt.total:.2f}", "Comprobante interno de venta"], [["Detalle", "Cantidad", "Precio", "Importe"]] + [[row.nombre, row.cantidad, row.precio_unitario, row.subtotal] for row in receipt.detalles])
