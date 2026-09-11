from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Category, Color, Product
from app.routers.api import filter_products
from app.templating import templates

router = APIRouter(tags=["web"])

MATERIALS = ["PET", "PEAD", "PP", "PVC"]


def base_context(request: Request, db: Session) -> dict:
    return {
        "request": request,
        "categories": db.query(Category).order_by(Category.position).all(),
    }


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    featured = (
        db.query(Product)
        .options(joinedload(Product.variants), joinedload(Product.colors))
        .filter(Product.is_active.is_(True), Product.featured.is_(True))
        .order_by(Product.position)
        .all()
    )
    return templates.TemplateResponse(
        request,
        "index.html",
        {**base_context(request, db), "featured": featured, "active": "home"},
    )


@router.get("/catalogo", response_class=HTMLResponse)
def catalog(
    request: Request,
    categoria: str | None = None,
    material: str | None = None,
    q: str | None = None,
    color: str | None = None,
    capacidad: str | None = None,
    orden: str = "relevancia",
    db: Session = Depends(get_db),
):
    ranges = {
        "0-500": (0, 500),
        "500-1000": (500, 1000),
        "1000-5000": (1000, 5000),
        "5000-": (5000, None),
    }
    cap_min, cap_max = ranges.get(capacidad or "", (None, None))
    products = filter_products(
        db,
        category=categoria,
        material=material,
        search=q,
        capacity_min=cap_min,
        capacity_max=cap_max,
        color=color,
        order=orden,
    )
    return templates.TemplateResponse(
        request,
        "catalogo.html",
        {
            **base_context(request, db),
            "products": products,
            "materials": MATERIALS,
            "colors": db.query(Color).order_by(Color.name).all(),
            "filters": {
                "categoria": categoria or "",
                "material": material or "",
                "q": q or "",
                "color": color or "",
                "capacidad": capacidad or "",
                "orden": orden,
            },
            "active": "catalogo",
        },
    )


@router.get("/producto/{slug}", response_class=HTMLResponse)
def product_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    product = (
        db.query(Product)
        .options(joinedload(Product.variants), joinedload(Product.colors), joinedload(Product.category))
        .filter(Product.slug == slug, Product.is_active.is_(True))
        .one_or_none()
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    related = (
        db.query(Product)
        .filter(
            Product.category_id == product.category_id,
            Product.id != product.id,
            Product.is_active.is_(True),
        )
        .order_by(Product.position)
        .limit(3)
        .all()
    )
    return templates.TemplateResponse(
        request,
        "producto.html",
        {**base_context(request, db), "product": product, "related": related, "active": "catalogo"},
    )


@router.get("/cotizacion", response_class=HTMLResponse)
def quote_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request, "cotizacion.html", {**base_context(request, db), "active": "cotizacion"}
    )


@router.get("/nosotros", response_class=HTMLResponse)
def about(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "nosotros.html", {**base_context(request, db), "active": "nosotros"})


@router.get("/servicios", response_class=HTMLResponse)
def services(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "servicios.html", {**base_context(request, db), "active": "servicios"})


@router.get("/contacto", response_class=HTMLResponse)
def contact(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "contacto.html", {**base_context(request, db), "active": "contacto"})
