from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from core.choices import Currency
from core.models import UserStampedModel


class PriceList(UserStampedModel):
    code = models.CharField("clave", max_length=20, unique=True)
    name = models.CharField("nombre", max_length=120)
    currency = models.CharField("moneda", max_length=3, choices=Currency.choices, default=Currency.MXN)
    customer = models.ForeignKey(
        "crm.Party",
        verbose_name="cliente (opcional)",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="price_lists",
        help_text="Vacío = lista general.",
    )
    valid_from = models.DateField("vigente desde", default=timezone.localdate)
    valid_until = models.DateField("vigente hasta", null=True, blank=True)
    is_active = models.BooleanField("activa", default=True)
    notes = models.TextField("notas", blank=True)

    class Meta:
        verbose_name = "lista de precios"
        verbose_name_plural = "listas de precios"
        ordering = ["code"]
        permissions = [("export_pricelist", "Puede exportar listas de precios (Excel/PDF)")]

    def __str__(self):
        return f"{self.code} · {self.name}"

    def save(self, *args, **kwargs):
        self.code = (self.code or "").strip().upper()
        super().save(*args, **kwargs)

    def clean(self):
        if self.valid_until and self.valid_until < self.valid_from:
            raise ValidationError({"valid_until": "La vigencia final no puede ser anterior a la inicial."})

    def is_current(self, on=None):
        on = on or timezone.localdate()
        return self.is_active and self.valid_from <= on and (self.valid_until is None or self.valid_until >= on)


class PriceListItem(models.Model):
    price_list = models.ForeignKey(PriceList, on_delete=models.CASCADE, related_name="items", verbose_name="lista")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, related_name="+", verbose_name="producto")
    min_quantity = models.DecimalField(
        "cantidad mínima", max_digits=12, decimal_places=3, default=1, validators=[MinValueValidator(0)]
    )
    unit_price = models.DecimalField(
        "precio unitario", max_digits=14, decimal_places=4, validators=[MinValueValidator(0)]
    )
    updated_at = models.DateTimeField("actualizado", auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="actualizado por",
    )

    class Meta:
        verbose_name = "precio"
        verbose_name_plural = "precios"
        ordering = ["product__sku", "min_quantity"]
        constraints = [
            models.UniqueConstraint(fields=["price_list", "product", "min_quantity"], name="pricing_item_unique"),
            models.CheckConstraint(condition=models.Q(unit_price__gte=0), name="pricing_item_price_non_negative"),
        ]

    def __str__(self):
        return f"{self.product.sku} ≥{self.min_quantity}: {self.unit_price}"


class PriceChange(models.Model):
    """Historial de cambios de precio (solo inserción)."""

    class Source(models.TextChoices):
        MANUAL = "manual", "Captura manual"
        VOICE = "voz", "Dictado por voz"
        TEXT = "texto", "Texto interpretado"

    created_at = models.DateTimeField("fecha", auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+", verbose_name="usuario"
    )
    price_list = models.ForeignKey(PriceList, on_delete=models.CASCADE, related_name="changes", verbose_name="lista")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, related_name="+", verbose_name="producto")
    min_quantity = models.DecimalField("cantidad mínima", max_digits=12, decimal_places=3)
    old_price = models.DecimalField("precio anterior", max_digits=14, decimal_places=4, null=True, blank=True)
    new_price = models.DecimalField("precio nuevo", max_digits=14, decimal_places=4, null=True, blank=True)
    source = models.CharField("origen", max_length=10, choices=Source.choices, default=Source.MANUAL)
    transcript = models.TextField("transcripción", blank=True)

    class Meta:
        verbose_name = "cambio de precio"
        verbose_name_plural = "cambios de precio"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.product.sku}: {self.old_price} → {self.new_price}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("El historial de precios es de solo inserción.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("El historial de precios es de solo inserción.")
