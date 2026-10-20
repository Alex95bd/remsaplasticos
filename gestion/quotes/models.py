from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from core.choices import Currency
from core.models import UserStampedModel

CENT = Decimal("0.01")


def money(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


class QuoteSequence(models.Model):
    """Consecutivo de folios por año. Se bloquea con ``select_for_update`` al generar folios."""

    year = models.PositiveIntegerField(unique=True)
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "consecutivo de folios"

    def __str__(self):
        return f"{self.year}: {self.last_number}"

    @classmethod
    def next_folio(cls, year=None):
        year = year or timezone.localdate().year
        with transaction.atomic():
            seq, _ = cls.objects.select_for_update().get_or_create(year=year)
            seq.last_number += 1
            seq.save(update_fields=["last_number"])
            return f"COT-{year}-{seq.last_number:05d}"


class Quote(UserStampedModel):
    class Status(models.TextChoices):
        DRAFT = "borrador", "Borrador"
        SENT = "enviada", "Enviada"
        FOLLOW_UP = "seguimiento", "En seguimiento"
        APPROVED = "aprobada", "Aprobada"
        REJECTED = "rechazada", "Rechazada"
        EXPIRED = "vencida", "Vencida"

    OPEN_STATUSES = [Status.SENT, Status.FOLLOW_UP]
    TRANSITIONS = {
        Status.DRAFT: [Status.SENT],
        Status.SENT: [Status.FOLLOW_UP, Status.APPROVED, Status.REJECTED, Status.EXPIRED],
        Status.FOLLOW_UP: [Status.APPROVED, Status.REJECTED, Status.EXPIRED],
        Status.APPROVED: [],
        Status.REJECTED: [],
        Status.EXPIRED: [],
    }

    folio = models.CharField("folio", max_length=20, unique=True, editable=False)
    customer = models.ForeignKey("crm.Party", verbose_name="cliente", on_delete=models.PROTECT, related_name="quotes")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="responsable", on_delete=models.PROTECT, related_name="quotes"
    )
    issue_date = models.DateField("fecha", default=timezone.localdate)
    valid_until = models.DateField("vigencia")
    currency = models.CharField("moneda", max_length=3, choices=Currency.choices, default=Currency.MXN)
    tax_rate = models.DecimalField(
        "IVA (%)", max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    subtotal = models.DecimalField("subtotal", max_digits=14, decimal_places=2, default=0, editable=False)
    discount_total = models.DecimalField("descuentos", max_digits=14, decimal_places=2, default=0, editable=False)
    tax_total = models.DecimalField("IVA", max_digits=14, decimal_places=2, default=0, editable=False)
    total = models.DecimalField("total", max_digits=14, decimal_places=2, default=0, editable=False)
    conditions = models.TextField("condiciones comerciales", blank=True)
    notes = models.TextField("observaciones", blank=True)
    status = models.CharField("estado", max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True)
    status_changed_at = models.DateTimeField("cambio de estado", null=True, blank=True, editable=False)
    rejection_reason = models.TextField("motivo de rechazo", blank=True)
    duplicated_from = models.ForeignKey(
        "self", verbose_name="duplicada de", null=True, blank=True, on_delete=models.SET_NULL, editable=False
    )

    class Meta:
        verbose_name = "cotización"
        verbose_name_plural = "cotizaciones"
        ordering = ["-created_at", "-id"]
        permissions = [
            ("override_price", "Puede cotizar por debajo del precio de referencia"),
            ("approve_discount", "Puede autorizar descuentos mayores al límite"),
            ("change_any_quote", "Puede editar cotizaciones de otros usuarios"),
        ]
        indexes = [models.Index(fields=["status", "issue_date"], name="quote_status_date_idx")]
        constraints = [
            models.CheckConstraint(condition=models.Q(total__gte=0), name="quote_total_non_negative"),
        ]

    def __str__(self):
        return f"{self.folio} · {self.customer}"

    @property
    def is_editable(self):
        return self.status == self.Status.DRAFT

    @property
    def allowed_transitions(self):
        return self.TRANSITIONS.get(self.status, [])

    @property
    def is_overdue(self):
        return self.status in self.OPEN_STATUSES and self.valid_until < timezone.localdate()

    def recalculate(self, save=True):
        """Recalcula importes en el servidor a partir de las partidas guardadas."""
        subtotal = discount = Decimal("0")
        for item in self.items.all():
            subtotal += item.line_subtotal
            discount += item.line_discount
        net = subtotal - discount
        tax = money(net * self.tax_rate / 100)
        self.subtotal, self.discount_total, self.tax_total = money(subtotal), money(discount), tax
        self.total = money(net) + tax
        if save:
            self.save(update_fields=["subtotal", "discount_total", "tax_total", "total", "updated_at"])


class QuoteItem(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="items")
    position = models.PositiveIntegerField("partida", default=1)
    product = models.ForeignKey(
        "catalog.Product", verbose_name="producto", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    sku = models.CharField("SKU", max_length=40)
    description = models.CharField("descripción", max_length=255)
    unit = models.CharField("unidad", max_length=10)
    quantity = models.DecimalField("cantidad", max_digits=12, decimal_places=3, validators=[MinValueValidator(0)])
    unit_price = models.DecimalField(
        "precio unitario", max_digits=14, decimal_places=4, validators=[MinValueValidator(0)]
    )
    discount_pct = models.DecimalField(
        "descuento (%)",
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    reference_price = models.DecimalField(
        "precio de referencia al cotizar", max_digits=14, decimal_places=4, null=True, blank=True
    )
    line_subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    line_discount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        verbose_name = "partida"
        ordering = ["position", "id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="quoteitem_quantity_positive"),
            models.CheckConstraint(condition=models.Q(unit_price__gte=0), name="quoteitem_price_non_negative"),
        ]

    def __str__(self):
        return f"{self.sku} × {self.quantity}"

    def compute(self):
        self.line_subtotal = money(self.quantity * self.unit_price)
        self.line_discount = money(self.line_subtotal * self.discount_pct / 100)
        self.line_total = self.line_subtotal - self.line_discount


class QuoteFollowUp(models.Model):
    class Kind(models.TextChoices):
        CALL = "llamada", "Llamada"
        EMAIL = "correo", "Correo"
        VISIT = "visita", "Visita"
        NOTE = "nota", "Nota"
        STATUS = "estado", "Cambio de estado"

    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="follow_ups")
    created_at = models.DateTimeField("fecha", auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+", verbose_name="usuario"
    )
    kind = models.CharField("tipo", max_length=10, choices=Kind.choices, default=Kind.NOTE)
    notes = models.TextField("comentario")
    next_action_date = models.DateField("próxima acción", null=True, blank=True)

    class Meta:
        verbose_name = "seguimiento"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.quote.folio} · {self.get_kind_display()}"
