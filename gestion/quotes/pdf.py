"""PDF de cotización con identidad REMSA (ReportLab)."""

from io import BytesIO
from xml.sax.saxutils import escape

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY = colors.HexColor("#0A2540")
CYAN = colors.HexColor("#00C2FF")
LIGHT = colors.HexColor("#F3F6FA")


def fmt(value, decimals=2):
    return f"{value:,.{decimals}f}"


def qty(value):
    text = f"{value:,f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def p(text, style):
    return Paragraph(escape(str(text or "")).replace("\n", "<br/>"), style)


def _header_footer(title):
    def draw(canvas, doc):
        canvas.saveState()
        width, height = letter
        canvas.setFillColor(NAVY)
        canvas.rect(0, height - 22 * mm, width, 22 * mm, fill=1, stroke=0)
        canvas.setFillColor(CYAN)
        canvas.rect(0, height - 23.2 * mm, width, 1.2 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 16)
        canvas.drawString(15 * mm, height - 12 * mm, "REMSA")
        canvas.setFont("Helvetica", 8.5)
        canvas.drawString(15 * mm, height - 17 * mm, settings.COMPANY_NAME)
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawRightString(width - 15 * mm, height - 13 * mm, title)
        canvas.setFillColor(colors.HexColor("#6C7A8A"))
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(15 * mm, 10 * mm, f"{settings.COMPANY_NAME} · Documento generado por REMSA Gestión Comercial")
        canvas.drawRightString(width - 15 * mm, 10 * mm, f"Página {doc.page}")
        canvas.restoreState()

    return draw


def styles():
    base = getSampleStyleSheet()
    return {
        "normal": ParagraphStyle("n", parent=base["Normal"], fontSize=8.5, leading=11),
        "small": ParagraphStyle(
            "s", parent=base["Normal"], fontSize=7.5, leading=9.5, textColor=colors.HexColor("#4B5B6C")
        ),
        "label": ParagraphStyle("l", parent=base["Normal"], fontSize=7.5, textColor=colors.HexColor("#6C7A8A")),
        "h": ParagraphStyle(
            "h", parent=base["Normal"], fontSize=10, leading=13, textColor=NAVY, fontName="Helvetica-Bold"
        ),
        "right": ParagraphStyle("r", parent=base["Normal"], fontSize=8.5, alignment=TA_RIGHT),
    }


def build_document(story, title):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=30 * mm,
        bottomMargin=18 * mm,
        title=title,
        author=settings.COMPANY_NAME,
    )
    draw = _header_footer(title)
    doc.build(story, onFirstPage=draw, onLaterPages=draw)
    return buffer.getvalue()


def table_style(header_rows=1):
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, header_rows - 1), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), colors.white),
            ("FONTNAME", (0, 0), (-1, header_rows - 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, header_rows), (-1, -1), [colors.white, LIGHT]),
            ("LINEBELOW", (0, -1), (-1, -1), 0.5, NAVY),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
    )


def quote_pdf(quote) -> bytes:
    st = styles()
    c = quote.customer
    story = []
    info = [
        [p("Cliente", st["label"]), p("Folio", st["label"]), p("Fecha", st["label"]), p("Vigencia", st["label"])],
        [
            p(c.name, st["h"]),
            p(quote.folio, st["h"]),
            p(quote.issue_date.strftime("%d/%m/%Y"), st["normal"]),
            p(quote.valid_until.strftime("%d/%m/%Y"), st["normal"]),
        ],
        [
            p(
                " · ".join(x for x in [f"RFC {c.rfc}" if c.rfc else "", c.contact_name, c.phone, c.email] if x),
                st["small"],
            ),
            p(f"Moneda: {quote.currency}", st["small"]),
            p(f"Atiende: {quote.owner.get_full_name() or quote.owner.username}", st["small"]),
            "",
        ],
    ]
    t = Table(info, colWidths=[85 * mm, 35 * mm, 32 * mm, 33 * mm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("SPAN", (2, 2), (3, 2))]))
    story += [t, Spacer(1, 6 * mm)]

    rows = [["#", "SKU", "Descripción", "Cant.", "Unidad", "P. unitario", "Desc.", "Importe"]]
    for item in quote.items.all():
        rows.append(
            [
                item.position,
                item.sku,
                p(item.description, st["normal"]),
                qty(item.quantity),
                item.unit,
                fmt(
                    item.unit_price, 4 if item.unit_price != item.unit_price.quantize(1) and item.unit_price < 10 else 2
                ),
                f"{qty(item.discount_pct)}%" if item.discount_pct else "—",
                fmt(item.line_total),
            ]
        )
    items = Table(rows, colWidths=[8 * mm, 26 * mm, 63 * mm, 16 * mm, 14 * mm, 22 * mm, 13 * mm, 23 * mm], repeatRows=1)
    style = table_style()
    style.add("ALIGN", (3, 0), (-1, -1), "RIGHT")
    style.add("ALIGN", (4, 0), (4, -1), "CENTER")
    items.setStyle(style)
    story += [items, Spacer(1, 4 * mm)]

    totals = [
        ["Subtotal", fmt(quote.subtotal)],
        ["Descuentos", f"-{fmt(quote.discount_total)}"],
        [f"IVA {qty(quote.tax_rate)}%", fmt(quote.tax_total)],
        [f"Total {quote.currency}", fmt(quote.total)],
    ]
    tt = Table(totals, colWidths=[30 * mm, 30 * mm], hAlign="RIGHT")
    tt.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, -1), (-1, -1), NAVY),
                ("LINEABOVE", (0, -1), (-1, -1), 0.8, CYAN),
            ]
        )
    )
    story += [tt, Spacer(1, 6 * mm)]
    if quote.conditions:
        story += [p("Condiciones comerciales", st["h"]), p(quote.conditions, st["normal"]), Spacer(1, 3 * mm)]
    if quote.notes:
        story += [p("Observaciones", st["h"]), p(quote.notes, st["normal"]), Spacer(1, 3 * mm)]
    story.append(
        p(
            "Precios sujetos a cambio sin previo aviso después de la vigencia indicada. "
            "Esta cotización no constituye un pedido ni aparta inventario.",
            st["small"],
        )
    )
    return build_document(story, f"Cotización {quote.folio}")
