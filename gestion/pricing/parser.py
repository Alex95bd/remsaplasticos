"""Interpretación de dictados de precios en español.

Nunca guarda nada: devuelve los datos detectados, el nivel de certeza y advertencias
para que la persona los revise y confirme antes de aplicar cualquier cambio.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

UNITS = {
    "pieza": "PZA",
    "piezas": "PZA",
    "pza": "PZA",
    "pzas": "PZA",
    "millar": "MIL",
    "millares": "MIL",
    "kilo": "KG",
    "kilos": "KG",
    "kilogramo": "KG",
    "kilogramos": "KG",
    "kg": "KG",
    "caja": "CJA",
    "cajas": "CJA",
    "paquete": "PAQ",
    "paquetes": "PAQ",
}
MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}
WORD_NUMBERS = {
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "veinte": 20,
    "treinta": 30,
    "cuarenta": 40,
    "cincuenta": 50,
    "cien": 100,
    "ciento": 100,
    "doscientos": 200,
    "doscientas": 200,
    "trescientos": 300,
    "trescientas": 300,
    "quinientos": 500,
    "quinientas": 500,
    "mil": 1000,
}
NUM = r"\d+(?:[.,]\d+)?"


def strip_accents(text):
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def to_decimal(text):
    text = text.replace(",", ".") if text.count(",") == 1 and "." not in text else text.replace(",", "")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def words_to_digits(text):
    """Convierte expresiones simples como «mil» o «quinientas piezas» a dígitos."""
    words = "|".join(sorted(WORD_NUMBERS, key=len, reverse=True))
    pattern = rf"\b(?:{words})(?:\s+(?:y\s+)?(?:{words}))*\b"

    def repl(match):
        total, current = 0, 0
        for word in match.group(0).replace(" y ", " ").split():
            value = WORD_NUMBERS[word]
            if value == 1000:
                total += (current or 1) * 1000
                current = 0
            else:
                current += value
        return str(total + current)

    return re.sub(pattern, repl, text)


@dataclass
class ParsedPrice:
    transcript: str
    sku: str = ""
    product_text: str = ""
    unit_price: Decimal | None = None
    currency: str = ""
    min_quantity: Decimal | None = None
    unit: str = ""
    price_list: str = ""
    valid_until: date | None = None
    warnings: list = field(default_factory=list)

    @property
    def is_complete(self):
        return bool((self.sku or self.product_text) and self.unit_price is not None)


def parse_dictation(transcript, today=None):
    today = today or date.today()
    original = " ".join((transcript or "").split())
    text = words_to_digits(strip_accents(original.lower()))
    result = ParsedPrice(transcript=original)

    # Precio: «35 pesos con 50 centavos», «a 35.50», «precio 12», «$ 4.20»
    m = re.search(rf"({NUM})\s*(?:pesos|peso|dolares|dolar|usd|mxn)?\s+con\s+(\d{{1,2}})\s*(?:centavos)?", text)
    if m:
        result.unit_price = to_decimal(f"{m.group(1)}.{int(m.group(2)):02d}")
    else:
        m = re.search(rf"(?:precio(?:\s+unitario)?(?:\s+de)?|\ba\b|\$|cuesta|vale)\s*\$?\s*({NUM})", text) or re.search(
            rf"({NUM})\s*(?:pesos|peso|dolares|dolar|usd|mxn)\b", text
        )
        if m:
            result.unit_price = to_decimal(m.group(1))
    if re.search(r"\b(dolares|dolar|usd)\b", text):
        result.currency = "USD"
    elif re.search(r"\b(pesos|peso|mxn)\b", text):
        result.currency = "MXN"

    # Cantidad mínima: «mínimo 1000 piezas», «a partir de 500», «desde 100 millares»
    m = re.search(rf"(?:minimo(?:\s+de)?|a partir de|desde|por|mayoreo de)\s+({NUM})\s*([a-z]+)?", text)
    if m:
        result.min_quantity = to_decimal(m.group(1))
        if m.group(2) in UNITS:
            result.unit = UNITS[m.group(2)]
    if not result.unit:
        for word, code in UNITS.items():
            if re.search(rf"\b{word}\b", text):
                result.unit = code
                break

    # Lista o cliente: «lista mayoreo», «para el cliente Envases del Sur»
    m = re.search(
        r"\blista\s+(?:de\s+precios\s+)?([a-z0-9][\w\s-]{1,40}?)(?=[,.;]|\s+(?:a|precio|minimo|vigen|desde|$)|$)", text
    )
    if m:
        result.price_list = m.group(1).strip()
    m = re.search(r"\bcliente\s+([a-z0-9][\w\s.&-]{1,60}?)(?=[,.;]|\s+(?:a|precio|minimo|vigen|lista)\b|$)", text)
    if m and not result.price_list:
        result.price_list = m.group(1).strip()

    # Vigencia: «vigente hasta el 31 de diciembre (de 2026)» o «hasta 31/12/2026»
    m = re.search(r"(?:vigen\w*|hasta)\s+(?:el\s+)?(\d{1,2})\s+de\s+([a-z]+)(?:\s+(?:de|del)\s+(\d{4}))?", text)
    try:
        if m and m.group(2) in MONTHS:
            year = int(m.group(3) or today.year)
            result.valid_until = date(year, MONTHS[m.group(2)], int(m.group(1)))
            if not m.group(3) and result.valid_until < today:
                result.valid_until = result.valid_until.replace(year=year + 1)
        elif m2 := re.search(r"(?:vigen\w*|hasta)\s+(?:el\s+)?(\d{1,2})/(\d{1,2})/(\d{2,4})", text):
            year = int(m2.group(3))
            result.valid_until = date(year + 2000 if year < 100 else year, int(m2.group(2)), int(m2.group(1)))
    except ValueError:
        result.warnings.append("No se pudo interpretar la fecha de vigencia.")

    # SKU / modelo: tokens con letras y dígitos («BOT-500», «gar 20», «t 38»)
    m = re.search(
        r"\b(?:sku|modelo|clave|codigo)\s+([a-z]{1,6}[\s-]?\d{1,6}(?:[\s-](?=[a-z]*\d)[a-z0-9]{1,6})?)\b", text
    ) or re.search(r"\b([a-z]{2,6}-\d{1,6}(?:-[a-z0-9]{1,6})?)\b", text)
    if m:
        result.sku = re.sub(r"\s+", "-", m.group(1).strip()).upper()
    m = re.search(r"\b(?:producto|articulo)\s+(.+?)(?=\s+(?:a|precio|en|con|minimo|desde|lista|vigen)\b|[,.;]|$)", text)
    if m:
        result.product_text = m.group(1).strip()
    elif not result.sku:
        head = re.split(r"\s+(?:a|precio|en|con|minimo|desde|lista|vigen\w*)\b|[,.;]", text, maxsplit=1)[0]
        result.product_text = head.strip()

    if result.unit_price is None:
        result.warnings.append("No se detectó el precio unitario.")
    if not result.currency:
        result.warnings.append("No se mencionó la moneda; revisa que sea la de la lista.")
    if not (result.sku or result.product_text):
        result.warnings.append("No se identificó el producto.")
    return result
