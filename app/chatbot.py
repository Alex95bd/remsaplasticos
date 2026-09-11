"""Asistente virtual del sitio.

Funciona sin dependencias externas usando un motor de intenciones + búsqueda en el
catálogo. Si se configura ``OPENAI_API_KEY`` se usa un LLM con el catálogo como contexto.
"""

from __future__ import annotations

import json
import re
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Category, Product


@dataclass
class BotReply:
    message: str
    suggestions: list[str] = field(default_factory=list)
    products: list[dict] = field(default_factory=list)
    engine: str = "local"


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9\s]", " ", text)


DEFAULT_SUGGESTIONS = [
    "Ver catálogo de botellas PET",
    "Quiero una cotización",
    "¿Cuál es el pedido mínimo?",
    "¿Dónde están ubicados?",
]

INTENTS: list[tuple[list[str], str, list[str]]] = [
    (
        ["hola", "buenas", "buen dia", "buenas tardes", "buenos dias", "hey", "saludos"],
        "¡Hola! Soy **Remi**, el asistente virtual de {app_name}. Puedo ayudarte a encontrar el envase "
        "adecuado, darte especificaciones técnicas o iniciar una cotización. ¿Qué necesitas?",
        DEFAULT_SUGGESTIONS,
    ),
    (
        ["cotiza", "cotizacion", "precio", "costo", "cuanto cuesta", "presupuesto"],
        "Con gusto preparamos tu cotización. Puedes agregar productos al **carrito de cotización** desde el "
        "catálogo y enviar la solicitud en /cotizacion; un asesor responde en menos de 24 horas hábiles. "
        "También puedes escribir a {email} o llamar al {phone}.",
        ["Ir a cotización", "Ver catálogo", "¿Cuál es el pedido mínimo?"],
    ),
    (
        ["minimo", "pedido minimo", "cantidad minima", "moq"],
        "El pedido mínimo estándar es de **1 tarima por modelo**. Para envases personalizados (molde propio, "
        "insertos o color especial) el mínimo se define según el proyecto. Cuéntame qué producto te interesa "
        "y te doy el detalle.",
        ["Ver catálogo", "Quiero una cotización"],
    ),
    (
        ["entrega", "tiempo de entrega", "envio", "cuanto tarda", "logistica", "flete"],
        "El tiempo de entrega habitual es de **7 a 10 días hábiles** para productos de catálogo y de 4 a 6 "
        "semanas para desarrollos con molde nuevo. Entregamos en toda la República Mexicana con flete "
        "consolidado o dedicado.",
        ["Quiero una cotización", "Ver catálogo"],
    ),
    (
        ["ubicacion", "donde estan", "direccion", "planta", "sucursal", "mapa"],
        "Estamos en {address}. Horario de atención: lunes a viernes de 8:00 a 18:00 h.",
        ["Ver contacto", "Quiero una cotización"],
    ),
    (
        ["contacto", "telefono", "correo", "email", "whatsapp", "hablar con", "asesor", "vendedor"],
        "Puedes contactarnos al **{phone}** o **{phone_alt}**, escribir a **{email}**, o dejar tus datos en "
        "/contacto y un asesor comercial te busca el mismo día.",
        ["Ver contacto", "Quiero una cotización"],
    ),
    (
        ["personaliz", "molde", "diseno propio", "inserto", "grabado", "marca propia", "color especial", "pigment"],
        "Sí, personalizamos envases: **pigmentado a color** (carta Pantone), **protección UV**, grabado de marca "
        "en alto relieve mediante insertos (garrafones de 20 L) y desarrollo de molde exclusivo. Cuéntame el "
        "producto y el volumen anual estimado para orientarte.",
        ["Ver garrafones", "Quiero una cotización"],
    ),
    (
        ["reciclad", "sustentab", "ecolog", "pcr", "medio ambiente", "reciclaje"],
        "Trabajamos con **PET 100 % reciclable** y ofrecemos preformas con resina reciclada (rPET/PCR) según "
        "disponibilidad y grado requerido. También optimizamos gramajes para reducir el consumo de resina.",
        ["Ver preformas", "Quiero una cotización"],
    ),
    (
        ["certific", "fda", "grado alimenticio", "inocuidad", "calidad", "norma"],
        "Nuestros envases se fabrican con **resinas grado alimenticio (FDA)** bajo un sistema de control de "
        "calidad con inspección dimensional, pruebas de torque, hermeticidad y resistencia a presión.",
        ["Ver catálogo", "Descargar ficha técnica"],
    ),
    (
        ["ficha", "especificacion", "pdf", "datasheet", "ficha tecnica", "descargar"],
        "Cada producto del catálogo tiene una **ficha técnica en PDF descargable** con modelos, capacidades, "
        "pesos, dimensiones, colores y datos de empaque. Ábrela desde el botón *Descargar ficha técnica* en la "
        "página del producto.",
        ["Ver catálogo"],
    ),
    (
        ["gracias", "muchas gracias", "thank"],
        "¡Con gusto! Si necesitas algo más aquí estoy. ¿Te ayudo con una cotización?",
        ["Quiero una cotización", "Ver catálogo"],
    ),
]


def _format(text: str) -> str:
    return text.format(
        app_name=settings.app_name,
        email=settings.company_email,
        phone=settings.company_phone,
        phone_alt=settings.company_phone_alt,
        address=settings.company_address,
    )


def search_catalog(db: Session, query: str, limit: int = 4) -> list[Product]:
    tokens = [t for t in normalize(query).split() if len(t) > 2]
    if not tokens:
        return []
    products = db.query(Product).filter(Product.is_active.is_(True)).all()
    scored: list[tuple[int, Product]] = []
    for product in products:
        haystack = normalize(
            " ".join(
                [
                    product.name,
                    product.summary,
                    product.material,
                    product.line,
                    product.category.name,
                    product.applications,
                    " ".join(v.model for v in product.variants),
                    " ".join(v.capacity_label for v in product.variants),
                ]
            )
        )
        score = sum(3 if token in normalize(product.name) else 1 for token in tokens if token in haystack)
        if score:
            scored.append((score, product))
    scored.sort(key=lambda item: (-item[0], item[1].position))
    return [product for _, product in scored[:limit]]


def _product_payload(product: Product) -> dict:
    return {
        "name": product.name,
        "url": f"/producto/{product.slug}",
        "summary": product.summary,
        "capacity": product.capacity_range,
        "material": product.material,
        "image": product.image,
    }


def local_reply(db: Session, message: str) -> BotReply:
    text = normalize(message)
    if not text.strip():
        return BotReply(_format(INTENTS[0][1]), DEFAULT_SUGGESTIONS)

    for keywords, response, suggestions in INTENTS:
        if any(keyword in text for keyword in keywords):
            matches = search_catalog(db, message, limit=3)
            return BotReply(
                _format(response),
                suggestions,
                [_product_payload(p) for p in matches],
            )

    matches = search_catalog(db, message)
    if matches:
        names = ", ".join(f"**{p.name}**" for p in matches)
        return BotReply(
            f"Encontré {len(matches)} producto(s) que coinciden con tu búsqueda: {names}. "
            "Abre la ficha para ver modelos, capacidades, colores y descargar el PDF de especificaciones.",
            ["Quiero una cotización", "¿Cuál es el pedido mínimo?", "Ver catálogo completo"],
            [_product_payload(p) for p in matches],
        )

    categories = db.query(Category).order_by(Category.position).all()
    listado = " · ".join(c.name for c in categories)
    return BotReply(
        "Aún no tengo una respuesta exacta para eso, pero puedo ayudarte con nuestro catálogo: "
        f"{listado}. También puedo darte información de cotizaciones, pedido mínimo, tiempos de entrega "
        f"o personalización. Si prefieres hablar con una persona escribe a {settings.company_email}.",
        DEFAULT_SUGGESTIONS,
    )


def _catalog_context(db: Session) -> str:
    lines = []
    for category in db.query(Category).order_by(Category.position).all():
        lines.append(f"# {category.name}: {category.tagline}")
        for product in category.products:
            if not product.is_active:
                continue
            models = ", ".join(f"{v.model} ({v.capacity_label})" for v in product.variants)
            colors = ", ".join(c.name for c in product.colors)
            lines.append(
                f"- {product.name} [/producto/{product.slug}] material {product.material}. {product.summary} "
                f"Modelos: {models}. Colores: {colors}."
            )
    return "\n".join(lines)


def llm_reply(db: Session, message: str, history: list[dict]) -> BotReply | None:
    if not settings.openai_api_key:
        return None
    system = (
        f"Eres Remi, asistente comercial de {settings.app_name}, fabricante mexicano de envases de PET, PEAD y "
        "PVC. Responde en español, en máximo 90 palabras, con tono profesional y cercano. Usa solo la "
        "información del catálogo; si no la tienes, invita a contactar a un asesor. Incluye la ruta del "
        "producto (ej. /producto/slug) cuando recomiendes uno.\n"
        f"Datos de contacto: tel {settings.company_phone}, correo {settings.company_email}, "
        f"dirección {settings.company_address}.\n\nCATÁLOGO:\n{_catalog_context(db)}"
    )
    messages = [{"role": "system", "content": system}]
    messages += [m for m in history if m.get("role") in {"user", "assistant"}][-6:]
    messages.append({"role": "user", "content": message})
    payload = json.dumps(
        {"model": settings.openai_model, "messages": messages, "temperature": 0.3, "max_tokens": 350}
    ).encode()
    request = urllib.request.Request(
        f"{settings.openai_base_url.rstrip('/')}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.openai_api_key}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            data = json.loads(response.read())
        content = data["choices"][0]["message"]["content"].strip()
    except (urllib.error.URLError, KeyError, TimeoutError, json.JSONDecodeError):
        return None
    matches = search_catalog(db, message, limit=3)
    return BotReply(content, DEFAULT_SUGGESTIONS, [_product_payload(p) for p in matches], engine="llm")


def answer(db: Session, message: str, history: list[dict] | None = None) -> BotReply:
    return llm_reply(db, message, history or []) or local_reply(db, message)
