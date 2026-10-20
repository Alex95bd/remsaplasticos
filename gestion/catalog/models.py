from decimal import Decimal

from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from core.choices import Currency
from core.models import UserStampedModel

sku_validator = RegexValidator(
    r"^[A-Z0-9][A-Z0-9._\-/]*$",
    "Usa solo letras, números, punto, guion, guion bajo o diagonal, sin espacios.",
)
non_negative = MinValueValidator(Decimal("0"))


def normalize_sku(value: str) -> str:
    return (value or "").strip().upper()


class Category(UserStampedModel):
    name = models.CharField("nombre", max_length=120)
    description = models.TextField("descripción", blank=True)
    is_active = models.BooleanField("activa", default=True)

    class Meta:
        verbose_name = "categoría"
        verbose_name_plural = "categorías"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"), name="catalog_category_name_ci_uniq", violation_error_message="Ya existe esa categoría."
            )
        ]

    def __str__(self):
        return self.name


class UnitOfMeasure(UserStampedModel):
    code = models.CharField(
        "clave",
        max_length=10,
        unique=True,
        validators=[RegexValidator(r"^[A-Z0-9]+$", "Usa solo letras mayúsculas y números.")],
    )
    name = models.CharField("nombre", max_length=60)
    is_active = models.BooleanField("activa", default=True)

    class Meta:
        verbose_name = "unidad de medida"
        verbose_name_plural = "unidades de medida"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} · {self.name}"

    def save(self, *args, **kwargs):
        self.code = (self.code or "").strip().upper()
        super().save(*args, **kwargs)


class Product(UserStampedModel):
    class ProductType(models.TextChoices):
        FINISHED = "terminado", "Producto terminado"
        SEMI_FINISHED = "semiterminado", "Semiterminado (preforma)"
        RAW_MATERIAL = "materia_prima", "Materia prima"
        SUPPLY = "insumo", "Insumo"
        PACKAGING = "empaque", "Material de empaque"
        SERVICE = "servicio", "Servicio"

    sku = models.CharField(
        "SKU",
        max_length=40,
        unique=True,
        validators=[sku_validator],
        help_text="Código único. Se guarda en mayúsculas.",
        error_messages={"unique": "Ya existe un producto con este SKU."},
    )
    name = models.CharField("nombre comercial", max_length=200, db_index=True)
    description = models.TextField("descripción", blank=True)
    category = models.ForeignKey(Category, verbose_name="categoría", on_delete=models.PROTECT, related_name="products")
    product_type = models.CharField(
        "tipo de producto", max_length=20, choices=ProductType.choices, default=ProductType.FINISHED, db_index=True
    )
    unit = models.ForeignKey(
        UnitOfMeasure, verbose_name="unidad de medida", on_delete=models.PROTECT, related_name="products"
    )
    presentation = models.CharField(
        "presentación", max_length=120, blank=True, help_text="Ej. Caja con 50 piezas, tarima de 1,200 piezas."
    )
    capacity_ml = models.DecimalField(
        "capacidad (ml)", max_digits=10, decimal_places=2, null=True, blank=True, validators=[non_negative]
    )
    height_mm = models.DecimalField(
        "alto (mm)", max_digits=8, decimal_places=2, null=True, blank=True, validators=[non_negative]
    )
    diameter_mm = models.DecimalField(
        "diámetro (mm)", max_digits=8, decimal_places=2, null=True, blank=True, validators=[non_negative]
    )
    weight_g = models.DecimalField(
        "peso (g)", max_digits=10, decimal_places=2, null=True, blank=True, validators=[non_negative]
    )
    reference_price = models.DecimalField(
        "precio de referencia",
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[non_negative],
        help_text="Precio unitario antes de impuestos. Las listas de precios se manejan en la Fase 4.",
    )
    currency = models.CharField("moneda", max_length=3, choices=Currency.choices, default=Currency.MXN)
    is_active = models.BooleanField("activo", default=True, db_index=True)
    external_code = models.CharField(
        "código externo (Intelisis)",
        max_length=50,
        blank=True,
        help_text="Clave del artículo en Intelisis para la futura integración.",
    )

    class Meta:
        verbose_name = "producto"
        verbose_name_plural = "productos"
        ordering = ["name", "sku"]
        permissions = [
            ("import_product", "Puede importar productos desde Excel"),
            ("export_product", "Puede exportar productos a Excel"),
            ("view_reference_price", "Puede ver precios de referencia"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["external_code"],
                condition=~Q(external_code=""),
                name="catalog_product_external_code_uniq",
                violation_error_message="Ya existe un producto con este código externo.",
            ),
            models.CheckConstraint(
                condition=Q(reference_price__isnull=True) | Q(reference_price__gte=0),
                name="catalog_product_price_non_negative",
            ),
        ]
        indexes = [models.Index(fields=["category", "is_active"], name="catalog_prod_cat_active_idx")]

    def __str__(self):
        return f"{self.sku} · {self.name}"

    def clean(self):
        self.sku = normalize_sku(self.sku)
        self.external_code = (self.external_code or "").strip()

    def save(self, *args, **kwargs):
        self.sku = normalize_sku(self.sku)
        self.external_code = (self.external_code or "").strip()
        super().save(*args, **kwargs)
