from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class VariantOut(BaseModel):
    model: str
    capacity_ml: int
    capacity_label: str
    weight_g: float
    height_mm: float
    diameter_mm: float
    neck_finish: str
    units_per_box: int
    boxes_per_pallet: int

    class Config:
        from_attributes = True


class ColorOut(BaseModel):
    name: str
    hex_code: str

    class Config:
        from_attributes = True


class ProductOut(BaseModel):
    slug: str
    name: str
    material: str
    line: str
    summary: str
    description: str
    neck_finish: str
    certifications: str
    lead_time: str
    min_order: str
    image: str
    featured: bool
    category: str
    capacity_range: str
    features: list[str]
    applications: list[str]
    packaging: list[str]
    colors: list[ColorOut]
    variants: list[VariantOut]


class CategoryOut(BaseModel):
    slug: str
    name: str
    tagline: str
    description: str
    icon: str
    image: str
    product_count: int


class QuoteItemIn(BaseModel):
    product_slug: str | None = None
    product_name: str = Field(min_length=1, max_length=200)
    model: str = ""
    color: str = ""
    quantity: int = Field(default=1, ge=1, le=10_000_000)
    notes: str = ""


class QuoteIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    company: str = ""
    phone: str = ""
    city: str = ""
    industry: str = ""
    message: str = ""
    source: str = "web"
    items: list[QuoteItemIn] = []

    @field_validator("items")
    @classmethod
    def limit_items(cls, value: list[QuoteItemIn]) -> list[QuoteItemIn]:
        if len(value) > 40:
            raise ValueError("Demasiadas partidas en la cotización")
        return value


class QuoteOut(BaseModel):
    code: str
    created_at: datetime
    message: str


class ContactIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    subject: str = ""
    message: str = Field(min_length=5, max_length=4000)


class SubscriberIn(BaseModel):
    email: EmailStr


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    session_id: str = Field(default="", max_length=64)


class ChatOut(BaseModel):
    reply: str
    suggestions: list[str]
    products: list[dict]
    session_id: str
    engine: str
