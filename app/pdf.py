"""Generación de la ficha técnica (PDF) descargable de cada producto."""

from datetime import date
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.config import settings
from app.models import Product

BRAND = colors.HexColor("#0b63c5")
DARK = colors.HexColor("#10243d")
LIGHT = colors.HexColor("#eef4fb")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontSize=20, textColor=DARK, alignment=0, spaceAfter=2),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"], fontSize=10.5, textColor=colors.HexColor("#5a6b7f")
        ),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontSize=12, textColor=BRAND, spaceBefore=12, spaceAfter=4),
        "body": ParagraphStyle("body", parent=base["Normal"], fontSize=9.5, leading=14, alignment=TA_JUSTIFY),
        "small": ParagraphStyle("small", parent=base["Normal"], fontSize=8, textColor=colors.HexColor("#6b7a8d")),
        "cell": ParagraphStyle("cell", parent=base["Normal"], fontSize=8.5, leading=12),
    }


def _header_footer(canvas, doc) -> None:
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(DARK)
    canvas.rect(0, height - 22 * mm, width, 22 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 15)
    canvas.drawString(18 * mm, height - 13 * mm, settings.app_name.upper())
    canvas.setFont("Helvetica", 8.5)
    canvas.drawRightString(width - 18 * mm, height - 13 * mm, "FICHA TÉCNICA DE PRODUCTO")
    canvas.setFillColor(colors.HexColor("#6b7a8d"))
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(18 * mm, 12 * mm, f"{settings.company_address}")
    canvas.drawString(18 * mm, 8 * mm, f"Tel. {settings.company_phone} · {settings.company_email}")
    canvas.drawRightString(width - 18 * mm, 8 * mm, f"Página {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#d7e1ec"))
    canvas.line(18 * mm, 16 * mm, width - 18 * mm, 16 * mm)
    canvas.restoreState()


def _bullets(items: list[str], style: ParagraphStyle) -> list:
    return [Paragraph(f"• {item}", style) for item in items]


def build_spec_sheet(product: Product) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=28 * mm,
        bottomMargin=20 * mm,
        title=f"Ficha técnica - {product.name}",
        author=settings.app_name,
    )
    st = _styles()
    story: list = [
        Paragraph(product.name, st["title"]),
        Paragraph(
            f"{product.category.name} · Material {product.material} · Línea {product.line or 'general'}",
            st["subtitle"],
        ),
        Spacer(1, 8),
    ]

    resume = [
        ["Código", product.slug.upper()],
        ["Categoría", product.category.name],
        ["Material", product.material],
        ["Capacidades", product.capacity_range],
        ["Acabado de boca", product.neck_finish or "—"],
        ["Colores disponibles", ", ".join(color.name for color in product.colors) or "—"],
        ["Certificaciones", product.certifications],
        ["Pedido mínimo", product.min_order],
        ["Tiempo de entrega", product.lead_time],
    ]
    table = Table(
        [[Paragraph(k, st["cell"]), Paragraph(v, st["cell"])] for k, v in resume],
        colWidths=[45 * mm, 129 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), LIGHT),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d7e1ec")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story += [table, Paragraph("Descripción", st["h2"]), Paragraph(product.description, st["body"])]

    if product.variants:
        header = ["Modelo", "Capacidad", "Peso (g)", "Altura (mm)", "Diám. (mm)", "Boca", "Pzas/caja", "Cajas/tarima"]
        rows = [[Paragraph(f"<b>{h}</b>", st["cell"]) for h in header]]
        for v in product.variants:
            rows.append(
                [
                    Paragraph(v.model, st["cell"]),
                    Paragraph(v.capacity_label, st["cell"]),
                    Paragraph(f"{v.weight_g:g}", st["cell"]),
                    Paragraph(f"{v.height_mm:g}", st["cell"]),
                    Paragraph(f"{v.diameter_mm:g}", st["cell"]),
                    Paragraph(v.neck_finish or "—", st["cell"]),
                    Paragraph(f"{v.units_per_box:,}".replace(",", " "), st["cell"]),
                    Paragraph(str(v.boxes_per_pallet), st["cell"]),
                ]
            )
        variants_table = Table(
            rows,
            colWidths=[24 * mm, 20 * mm, 17 * mm, 20 * mm, 19 * mm, 30 * mm, 22 * mm, 22 * mm],
            repeatRows=1,
        )
        variants_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), BRAND),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d7e1ec")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story += [Paragraph("Modelos y capacidades disponibles", st["h2"]), variants_table]

    story += [Paragraph("Características técnicas", st["h2"]), *_bullets(product.feature_list, st["body"])]
    if product.application_list:
        story += [Paragraph("Aplicaciones", st["h2"]), *_bullets(product.application_list, st["body"])]
    if product.packaging_list:
        story += [Paragraph("Empaque y embalaje", st["h2"]), *_bullets(product.packaging_list, st["body"])]
    if product.colors:
        color_cells = [
            [Paragraph(c.name, st["cell"]) for c in product.colors[i : i + 4]]
            for i in range(0, len(product.colors), 4)
        ]
        for row in color_cells:
            while len(row) < 4:
                row.append(Paragraph("", st["cell"]))
        colors_table = Table(color_cells, colWidths=[43.5 * mm] * 4)
        colors_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d7e1ec")),
                    ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story += [Paragraph("Colores disponibles", st["h2"]), colors_table]

    story += [
        Spacer(1, 14),
        KeepTogether(
            [
                Paragraph(
                    f"Documento generado el {date.today().strftime('%d/%m/%Y')}. Las especificaciones pueden variar "
                    "según el diseño final aprobado y están sujetas a tolerancias de proceso. Para cotizaciones y "
                    f"asesoría técnica escriba a {settings.company_email} o llame al {settings.company_phone}.",
                    st["small"],
                )
            ]
        ),
    ]

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buffer.getvalue()
