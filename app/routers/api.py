import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app import chatbot
from app.database import get_db
from app.models import (
    Category,
    ChatMessage,
    ContactMessage,
    Product,
    ProductVariant,
    Quote,
    QuoteItem,
    Subscriber,
)
from app.pdf import build_spec_sheet
from app.schemas import (
    ChatIn,
    ChatOut,
    ContactIn,
    ProductOut,
    QuoteIn,
    QuoteOut,
    SubscriberIn,
)

router = APIRouter(prefix="/api", tags=["api"])


def product_query(db: Session):
    return (
        db.query(Product)
        .options(joinedload(Product.category), joinedload(Product.variants), joinedload(Product.colors))
        .filter(Product.is_active.is_(True))
    )


def serialize_product(product: Product) -> dict:
    return ProductOut(
        slug=product.slug,
        name=product.name,
        material=product.material,
        line=product.line,
        summary=product.summary,
        description=product.description,
        neck_finish=product.neck_finish,
        certifications=product.certifications,
        lead_time=product.lead_time,
        min_order=product.min_order,
        image=product.image,
        featured=product.featured,
        category=product.category.name,
        capacity_range=product.capacity_range,
        features=product.feature_list,
        applications=product.application_list,
        packaging=product.packaging_list,
        colors=product.colors,
        variants=product.variants,
    ).model_dump()


def filter_products(
    db: Session,
    *,
    category: str | None = None,
    material: str | None = None,
    search: str | None = None,
    capacity_min: int | None = None,
    capacity_max: int | None = None,
    color: str | None = None,
    featured: bool | None = None,
    order: str = "relevancia",
) -> list[Product]:
    query = product_query(db)
    if category:
        query = query.join(Category).filter(Category.slug == category)
    if material:
        query = query.filter(Product.material == material)
    if featured is not None:
        query = query.filter(Product.featured.is_(featured))
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Product.name.ilike(like),
                Product.summary.ilike(like),
                Product.description.ilike(like),
                Product.applications.ilike(like),
                Product.line.ilike(like),
            )
        )
    if capacity_min is not None or capacity_max is not None:
        sub = db.query(ProductVariant.product_id)
        if capacity_min is not None:
            sub = sub.filter(ProductVariant.capacity_ml >= capacity_min)
        if capacity_max is not None:
            sub = sub.filter(ProductVariant.capacity_ml <= capacity_max)
        query = query.filter(Product.id.in_(sub))

    products = query.order_by(Product.position).all()
    if color:
        products = [p for p in products if any(c.name == color for c in p.colors)]
    if order == "nombre":
        products.sort(key=lambda p: p.name)
    elif order == "capacidad":
        products.sort(key=lambda p: max((v.capacity_ml for v in p.variants), default=0))
    elif order == "destacados":
        products.sort(key=lambda p: (not p.featured, p.position))
    return products


@router.get("/categorias")
def list_categories(db: Session = Depends(get_db)) -> list[dict]:
    categories = db.query(Category).order_by(Category.position).all()
    return [
        {
            "slug": c.slug,
            "name": c.name,
            "tagline": c.tagline,
            "description": c.description,
            "icon": c.icon,
            "image": c.image,
            "product_count": sum(1 for p in c.products if p.is_active),
        }
        for c in categories
    ]


@router.get("/productos")
def list_products(
    categoria: str | None = None,
    material: str | None = None,
    q: str | None = None,
    capacidad_min: int | None = None,
    capacidad_max: int | None = None,
    color: str | None = None,
    destacados: bool | None = None,
    orden: str = "relevancia",
    db: Session = Depends(get_db),
) -> dict:
    products = filter_products(
        db,
        category=categoria,
        material=material,
        search=q,
        capacity_min=capacidad_min,
        capacity_max=capacidad_max,
        color=color,
        featured=destacados,
        order=orden,
    )
    return {"total": len(products), "items": [serialize_product(p) for p in products]}


@router.get("/productos/{slug}")
def get_product(slug: str, db: Session = Depends(get_db)) -> dict:
    product = product_query(db).filter(Product.slug == slug).one_or_none()
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return serialize_product(product)


@router.get("/productos/{slug}/ficha-tecnica.pdf")
def spec_sheet(slug: str, db: Session = Depends(get_db)) -> Response:
    product = product_query(db).filter(Product.slug == slug).one_or_none()
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    pdf = build_spec_sheet(product)
    filename = f"ficha-tecnica-{product.slug}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/cotizaciones", response_model=QuoteOut, status_code=201)
def create_quote(payload: QuoteIn, db: Session = Depends(get_db)) -> QuoteOut:
    code = f"COT-{datetime.utcnow():%Y%m%d}-{uuid.uuid4().hex[:5].upper()}"
    quote = Quote(
        code=code,
        name=payload.name,
        company=payload.company,
        email=payload.email,
        phone=payload.phone,
        city=payload.city,
        industry=payload.industry,
        message=payload.message,
        source=payload.source,
    )
    for item in payload.items:
        product = (
            db.query(Product).filter(Product.slug == item.product_slug).one_or_none()
            if item.product_slug
            else None
        )
        quote.items.append(
            QuoteItem(
                product_id=product.id if product else None,
                product_name=product.name if product else item.product_name,
                model=item.model,
                color=item.color,
                quantity=item.quantity,
                notes=item.notes,
            )
        )
    db.add(quote)
    db.commit()
    return QuoteOut(
        code=code,
        created_at=quote.created_at,
        message="Recibimos tu solicitud. Un asesor comercial te contactará en menos de 24 horas hábiles.",
    )


@router.post("/contacto", status_code=201)
def create_contact(payload: ContactIn, db: Session = Depends(get_db)) -> dict:
    db.add(
        ContactMessage(
            name=payload.name,
            email=payload.email,
            subject=payload.subject,
            message=payload.message,
        )
    )
    db.commit()
    return {"message": "¡Gracias! Tu mensaje fue enviado, te responderemos muy pronto."}


@router.post("/suscripciones", status_code=201)
def subscribe(payload: SubscriberIn, db: Session = Depends(get_db)) -> dict:
    exists = db.query(Subscriber).filter(func.lower(Subscriber.email) == payload.email.lower()).count()
    if not exists:
        db.add(Subscriber(email=payload.email))
        db.commit()
    return {"message": "Suscripción registrada. Recibirás novedades y lanzamientos de producto."}


@router.post("/chat", response_model=ChatOut)
def chat(payload: ChatIn, db: Session = Depends(get_db)) -> ChatOut:
    session_id = payload.session_id or uuid.uuid4().hex[:16]
    history = [
        {"role": m.role, "content": m.content}
        for m in db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id.desc())
        .limit(8)
        .all()[::-1]
    ]
    reply = chatbot.answer(db, payload.message, history)
    db.add(ChatMessage(session_id=session_id, role="user", content=payload.message))
    db.add(ChatMessage(session_id=session_id, role="assistant", content=reply.message))
    db.commit()
    return ChatOut(
        reply=reply.message,
        suggestions=reply.suggestions,
        products=reply.products,
        session_id=session_id,
        engine=reply.engine,
    )


@router.get("/buscar")
def search(q: str = Query(min_length=2), db: Session = Depends(get_db)) -> list[dict]:
    products = filter_products(db, search=q)[:8]
    return [
        {"name": p.name, "slug": p.slug, "category": p.category.name, "capacity": p.capacity_range}
        for p in products
    ]
