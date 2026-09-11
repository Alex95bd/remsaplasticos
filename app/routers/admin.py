from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import (
    AdminUser,
    Category,
    ChatMessage,
    ContactMessage,
    Product,
    ProductVariant,
    Quote,
    Subscriber,
)
from app.security import verify_password
from app.templating import templates

router = APIRouter(prefix="/admin", tags=["admin"])

SESSION_KEY = "admin_email"


def current_admin(request: Request, db: Session) -> AdminUser | None:
    email = request.session.get(SESSION_KEY)
    if not email:
        return None
    return db.query(AdminUser).filter(AdminUser.email == email).one_or_none()


def require_admin(request: Request, db: Session = Depends(get_db)) -> AdminUser:
    admin = current_admin(request, db)
    if admin is None:
        raise HTTPException(status_code=303, detail="/admin/login", headers={"Location": "/admin/login"})
    return admin


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse(request, "admin/login.html", {"error": None})


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(AdminUser).filter(func.lower(AdminUser.email) == email.lower().strip()).one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request,
            "admin/login.html",
            {"error": "Credenciales incorrectas."},
            status_code=401,
        )
    request.session[SESSION_KEY] = user.email
    return RedirectResponse("/admin", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@router.get("", response_class=HTMLResponse)
def dashboard(request: Request, admin: AdminUser = Depends(require_admin), db: Session = Depends(get_db)):
    quotes = (
        db.query(Quote).options(joinedload(Quote.items)).order_by(Quote.created_at.desc()).limit(8).all()
    )
    stats = {
        "productos": db.query(Product).filter(Product.is_active.is_(True)).count(),
        "categorias": db.query(Category).count(),
        "modelos": db.query(ProductVariant).count(),
        "cotizaciones": db.query(Quote).count(),
        "cotizaciones_nuevas": db.query(Quote).filter(Quote.status == "nueva").count(),
        "mensajes": db.query(ContactMessage).count(),
        "suscriptores": db.query(Subscriber).count(),
        "chats": db.query(func.count(func.distinct(ChatMessage.session_id))).scalar() or 0,
    }
    top_products = (
        db.query(Category.name, func.count(Product.id))
        .join(Product, Product.category_id == Category.id)
        .group_by(Category.name)
        .all()
    )
    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {
            "request": request,
            "admin": admin,
            "stats": stats,
            "quotes": quotes,
            "distribution": top_products,
            "active": "dashboard",
        },
    )


@router.get("/cotizaciones", response_class=HTMLResponse)
def quotes_list(
    request: Request,
    status: str | None = None,
    admin: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Quote).options(joinedload(Quote.items))
    if status:
        query = query.filter(Quote.status == status)
    quotes = query.order_by(Quote.created_at.desc()).all()
    return templates.TemplateResponse(
        request,
        "admin/cotizaciones.html",
        {"request": request, "admin": admin, "quotes": quotes, "status": status or "", "active": "cotizaciones"},
    )


@router.post("/cotizaciones/{quote_id}/estatus")
def update_quote_status(
    quote_id: int,
    status: str = Form(...),
    admin: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    quote = db.get(Quote, quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    quote.status = status
    db.commit()
    return RedirectResponse("/admin/cotizaciones", status_code=303)


@router.get("/mensajes", response_class=HTMLResponse)
def messages(request: Request, admin: AdminUser = Depends(require_admin), db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "admin/mensajes.html",
        {
            "request": request,
            "admin": admin,
            "messages": db.query(ContactMessage).order_by(ContactMessage.created_at.desc()).all(),
            "subscribers": db.query(Subscriber).order_by(Subscriber.created_at.desc()).all(),
            "active": "mensajes",
        },
    )


@router.get("/productos", response_class=HTMLResponse)
def products_admin(request: Request, admin: AdminUser = Depends(require_admin), db: Session = Depends(get_db)):
    products = (
        db.query(Product)
        .options(joinedload(Product.category), joinedload(Product.variants))
        .order_by(Product.position)
        .all()
    )
    return templates.TemplateResponse(
        request,
        "admin/productos.html",
        {"request": request, "admin": admin, "products": products, "active": "productos"},
    )


@router.post("/productos/{product_id}/visibilidad")
def toggle_product(
    product_id: int,
    admin: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    product.is_active = not product.is_active
    db.commit()
    return RedirectResponse("/admin/productos", status_code=303)


@router.get("/conversaciones", response_class=HTMLResponse)
def conversations(request: Request, admin: AdminUser = Depends(require_admin), db: Session = Depends(get_db)):
    sessions: dict[str, list[ChatMessage]] = {}
    for message in db.query(ChatMessage).order_by(ChatMessage.created_at).all():
        sessions.setdefault(message.session_id, []).append(message)
    return templates.TemplateResponse(
        request,
        "admin/conversaciones.html",
        {"request": request, "admin": admin, "sessions": sessions, "active": "conversaciones"},
    )
