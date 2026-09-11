from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

product_colors = Table(
    "product_colors",
    Base.metadata,
    Column("product_id", ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("color_id", ForeignKey("colors.id", ondelete="CASCADE"), primary_key=True),
)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    tagline: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    icon: Mapped[str] = mapped_column(String(40), default="bottle")
    image: Mapped[str] = mapped_column(String(200), default="")
    position: Mapped[int] = mapped_column(Integer, default=0)

    products: Mapped[list["Product"]] = relationship(
        back_populates="category", cascade="all, delete-orphan", order_by="Product.position"
    )


class Color(Base):
    __tablename__ = "colors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    hex_code: Mapped[str] = mapped_column(String(9), default="#cccccc")

    products: Mapped[list["Product"]] = relationship(secondary=product_colors, back_populates="colors")


class Product(Base):
    """Un producto del catálogo (ej. Botella PET línea agua purificada)."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"))
    material: Mapped[str] = mapped_column(String(20), default="PET")
    line: Mapped[str] = mapped_column(String(80), default="")
    summary: Mapped[str] = mapped_column(String(300), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    features: Mapped[str] = mapped_column(Text, default="")  # una característica por línea
    applications: Mapped[str] = mapped_column(Text, default="")  # una por línea
    packaging: Mapped[str] = mapped_column(Text, default="")  # una línea por dato de empaque
    neck_finish: Mapped[str] = mapped_column(String(80), default="")
    certifications: Mapped[str] = mapped_column(String(200), default="Grado alimenticio / FDA")
    lead_time: Mapped[str] = mapped_column(String(120), default="7 a 10 días hábiles")
    min_order: Mapped[str] = mapped_column(String(120), default="1 tarima")
    image: Mapped[str] = mapped_column(String(200), default="")
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    category: Mapped[Category] = relationship(back_populates="products")
    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="ProductVariant.capacity_ml"
    )
    colors: Mapped[list[Color]] = relationship(secondary=product_colors, back_populates="products")

    @property
    def feature_list(self) -> list[str]:
        return [line.strip() for line in self.features.splitlines() if line.strip()]

    @property
    def application_list(self) -> list[str]:
        return [line.strip() for line in self.applications.splitlines() if line.strip()]

    @property
    def packaging_list(self) -> list[str]:
        return [line.strip() for line in self.packaging.splitlines() if line.strip()]

    @property
    def capacity_range(self) -> str:
        if not self.variants:
            return "—"
        caps = sorted(v.capacity_ml for v in self.variants if v.capacity_ml)
        if not caps:
            return "—"
        if caps[0] == caps[-1]:
            return format_capacity(caps[0])
        return f"{format_capacity(caps[0])} – {format_capacity(caps[-1])}"


class ProductVariant(Base):
    """Tipo/modelo específico de un producto: capacidad, peso, dimensiones."""

    __tablename__ = "product_variants"
    __table_args__ = (UniqueConstraint("product_id", "model", name="uq_variant_model"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    model: Mapped[str] = mapped_column(String(80))
    capacity_ml: Mapped[int] = mapped_column(Integer, default=0)
    weight_g: Mapped[float] = mapped_column(Float, default=0)
    height_mm: Mapped[float] = mapped_column(Float, default=0)
    diameter_mm: Mapped[float] = mapped_column(Float, default=0)
    neck_finish: Mapped[str] = mapped_column(String(80), default="")
    units_per_box: Mapped[int] = mapped_column(Integer, default=0)
    boxes_per_pallet: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped[Product] = relationship(back_populates="variants")

    @property
    def capacity_label(self) -> str:
        return format_capacity(self.capacity_ml)

    @property
    def units_per_pallet(self) -> int:
        return self.units_per_box * self.boxes_per_pallet


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    company: Mapped[str] = mapped_column(String(160), default="")
    email: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str] = mapped_column(String(60), default="")
    city: Mapped[str] = mapped_column(String(120), default="")
    industry: Mapped[str] = mapped_column(String(120), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="nueva")
    source: Mapped[str] = mapped_column(String(40), default="web")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    items: Mapped[list["QuoteItem"]] = relationship(
        back_populates="quote", cascade="all, delete-orphan"
    )


class QuoteItem(Base):
    __tablename__ = "quote_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id", ondelete="CASCADE"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    product_name: Mapped[str] = mapped_column(String(200))
    model: Mapped[str] = mapped_column(String(120), default="")
    color: Mapped[str] = mapped_column(String(60), default="")
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    notes: Mapped[str] = mapped_column(Text, default="")

    quote: Mapped[Quote] = relationship(back_populates="items")


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160))
    subject: Mapped[str] = mapped_column(String(200), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Subscriber(Base):
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(160), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(160), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(120), default="Administrador")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


def format_capacity(ml: int) -> str:
    if not ml:
        return "N/A"
    if ml >= 1000 and ml % 1000 == 0:
        return f"{ml // 1000} L"
    if ml >= 1000:
        return f"{ml / 1000:g} L".replace(".", ",")
    return f"{ml} ml"
