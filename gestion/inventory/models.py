import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from core.models import UserStampedModel


class Warehouse(UserStampedModel):
    code = models.CharField("clave", max_length=10, unique=True)
    name = models.CharField("nombre", max_length=100)
    address = models.TextField("dirección", blank=True)
    is_active = models.BooleanField("activo", default=True)
    external_code = models.CharField("código externo (Intelisis)", max_length=50, blank=True)

    class Meta:
        verbose_name = "almacén"
        verbose_name_plural = "almacenes"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} · {self.name}"

    def save(self, *args, **kwargs):
        self.code = (self.code or "").strip().upper()
        super().save(*args, **kwargs)


class Location(models.Model):
    warehouse = models.ForeignKey(Warehouse, verbose_name="almacén", on_delete=models.PROTECT, related_name="locations")
    code = models.CharField("ubicación", max_length=20, help_text="Ej. A-01-03 (pasillo-rack-nivel).")
    description = models.CharField("descripción", max_length=100, blank=True)
    is_active = models.BooleanField("activa", default=True)

    class Meta:
        verbose_name = "ubicación"
        verbose_name_plural = "ubicaciones"
        ordering = ["warehouse__code", "code"]
        constraints = [models.UniqueConstraint(fields=["warehouse", "code"], name="inventory_location_unique")]

    def __str__(self):
        return f"{self.warehouse.code}/{self.code}"

    def save(self, *args, **kwargs):
        self.code = (self.code or "").strip().upper()
        super().save(*args, **kwargs)


class Stock(models.Model):
    """Existencia actual de un producto en un almacén. Solo la modifican los servicios de movimientos."""

    product = models.ForeignKey(
        "catalog.Product", verbose_name="producto", on_delete=models.PROTECT, related_name="stocks"
    )
    warehouse = models.ForeignKey(Warehouse, verbose_name="almacén", on_delete=models.PROTECT, related_name="stocks")
    location = models.ForeignKey(
        Location, verbose_name="ubicación habitual", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    quantity = models.DecimalField("existencia", max_digits=14, decimal_places=3, default=0, editable=False)
    min_quantity = models.DecimalField(
        "stock mínimo", max_digits=14, decimal_places=3, default=0, validators=[MinValueValidator(0)]
    )
    updated_at = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        verbose_name = "existencia"
        verbose_name_plural = "existencias"
        ordering = ["product__sku", "warehouse__code"]
        constraints = [models.UniqueConstraint(fields=["product", "warehouse"], name="inventory_stock_unique")]
        permissions = [
            ("authorize_adjustment", "Puede autorizar ajustes de inventario"),
            ("transfer_stock", "Puede transferir entre almacenes"),
            ("export_stock", "Puede exportar existencias a Excel"),
        ]

    def __str__(self):
        return f"{self.product.sku} @ {self.warehouse.code}: {self.quantity}"

    @property
    def is_low(self):
        return self.min_quantity > 0 and self.quantity <= self.min_quantity


class StockMovement(models.Model):
    """Movimiento histórico. Es de solo inserción: las correcciones se hacen con un movimiento inverso."""

    class Kind(models.TextChoices):
        IN = "entrada", "Entrada"
        OUT = "salida", "Salida"
        ADJUST = "ajuste", "Ajuste autorizado"
        TRANSFER_OUT = "transf_salida", "Transferencia (salida)"
        TRANSFER_IN = "transf_entrada", "Transferencia (entrada)"
        REVERSAL = "reverso", "Cancelación (movimiento inverso)"

    created_at = models.DateTimeField("fecha", auto_now_add=True, db_index=True)
    kind = models.CharField("tipo", max_length=15, choices=Kind.choices, db_index=True)
    product = models.ForeignKey("catalog.Product", verbose_name="producto", on_delete=models.PROTECT, related_name="+")
    warehouse = models.ForeignKey(Warehouse, verbose_name="almacén", on_delete=models.PROTECT, related_name="movements")
    location = models.ForeignKey(
        Location, verbose_name="ubicación", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    quantity = models.DecimalField("cantidad (+/-)", max_digits=14, decimal_places=3)
    balance_after = models.DecimalField("existencia resultante", max_digits=14, decimal_places=3)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="responsable", on_delete=models.PROTECT)
    authorized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="autorizó",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    reason = models.CharField("motivo", max_length=200)
    reference = models.CharField("referencia", max_length=100, blank=True, help_text="Factura, pedido, remisión…")
    notes = models.TextField("observaciones", blank=True)
    transfer_id = models.UUIDField("transferencia", null=True, blank=True, db_index=True)
    reverses = models.OneToOneField(
        "self", verbose_name="cancela a", on_delete=models.PROTECT, null=True, blank=True, related_name="reversed_by"
    )

    class Meta:
        verbose_name = "movimiento de inventario"
        verbose_name_plural = "movimientos de inventario"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["product", "warehouse", "created_at"], name="inventory_mov_prod_idx")]
        constraints = [models.CheckConstraint(condition=~models.Q(quantity=0), name="inventory_mov_nonzero")]

    def __str__(self):
        return f"{self.get_kind_display()} {self.product.sku} {self.quantity:+}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Los movimientos de inventario no se modifican: registra un movimiento inverso.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Los movimientos de inventario no se eliminan: registra un movimiento inverso.")


def new_transfer_id():
    return uuid.uuid4()
