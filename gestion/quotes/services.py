"""Reglas de negocio de cotizaciones. Los importes se calculan siempre en el servidor."""

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from audit.models import AuditLog
from audit.services import diff_snapshots, log_action, model_snapshot

from .models import Quote, QuoteFollowUp, QuoteItem, QuoteSequence

HEADER_FIELDS = ["customer", "valid_until", "currency", "tax_rate", "conditions", "notes"]


def default_validity():
    return timezone.localdate() + timedelta(days=settings.QUOTE_DEFAULT_VALIDITY_DAYS)


def max_discount():
    return Decimal(str(settings.QUOTE_MAX_DISCOUNT_PCT))


def can_edit(user, quote):
    if not quote.is_editable or not user.has_perm("quotes.change_quote"):
        return False
    return quote.owner_id == user.pk or user.has_perm("quotes.change_any_quote")


def validate_line(user, product, unit_price, discount_pct):
    """Valida precio y descuento contra el catálogo y los permisos del usuario. Devuelve el precio final."""
    errors = []
    reference = product.reference_price
    if unit_price is None:
        if reference is None:
            errors.append("El producto no tiene precio de referencia: captura el precio unitario.")
        unit_price = reference
    if unit_price is not None and unit_price < 0:
        errors.append("El precio no puede ser negativo.")
    if (
        unit_price is not None
        and reference is not None
        and unit_price < reference
        and not user.has_perm("quotes.override_price")
    ):
        errors.append(f"El precio no puede ser menor al de referencia (${reference:,.4f}) sin autorización.")
    if discount_pct > max_discount() and not user.has_perm("quotes.approve_discount"):
        errors.append(f"El descuento máximo sin autorización es {max_discount()}%.")
    if errors:
        raise ValidationError(errors)
    return unit_price


def items_summary(quote):
    return [
        f"{i.sku} × {i.quantity.normalize():f} @ {i.unit_price.normalize():f} (-{i.discount_pct.normalize():f}%)"
        for i in quote.items.all()
    ]


@transaction.atomic
def save_quote(*, quote, lines, user, request=None):
    """Guarda encabezado y partidas. ``lines`` = [{product, quantity, unit_price, discount_pct}] ya validadas.

    Las partidas se reemplazan completas (la cotización solo es editable en borrador),
    copiando SKU, nombre, unidad y precio para conservar el historial.
    """
    is_new = quote.pk is None
    if is_new:
        quote.folio = QuoteSequence.next_folio()
        quote.owner = user
        quote.created_by = user
        before, before_items = {}, []
    else:
        locked = Quote.objects.select_for_update().get(pk=quote.pk)
        if not can_edit(user, locked):
            raise PermissionDenied("La cotización ya no es editable.")
        before, before_items = model_snapshot(locked, HEADER_FIELDS), items_summary(locked)
    quote.updated_by = user
    quote.save()
    quote.items.all().delete()
    for position, line in enumerate(lines, start=1):
        product = line["product"]
        item = QuoteItem(
            quote=quote,
            position=position,
            product=product,
            sku=product.sku,
            description=line.get("description") or product.name,
            unit=product.unit.code,
            quantity=line["quantity"],
            unit_price=line["unit_price"],
            discount_pct=line["discount_pct"],
            reference_price=product.reference_price,
        )
        item.compute()
        item.save()
    quote.recalculate()
    changes = diff_snapshots(before, model_snapshot(quote, HEADER_FIELDS))
    after_items = items_summary(quote)
    if after_items != before_items:
        changes["partidas"] = {"antes": before_items or None, "despues": after_items}
    if is_new or changes:
        log_action(
            AuditLog.Action.CREATE if is_new else AuditLog.Action.UPDATE,
            request=request,
            user=user,
            obj=quote,
            changes=changes,
            message=f"Total ${quote.total:,.2f} {quote.currency}",
        )
    return quote


@transaction.atomic
def change_status(*, quote, new_status, user, reason="", request=None):
    quote = Quote.objects.select_for_update().get(pk=quote.pk)
    if new_status not in quote.allowed_transitions:
        raise ValidationError(
            f"No se puede cambiar de «{quote.get_status_display()}» a «{Quote.Status(new_status).label}»."
        )
    if new_status == Quote.Status.SENT and not quote.items.exists():
        raise ValidationError("Agrega al menos una partida antes de enviar la cotización.")
    if new_status == Quote.Status.REJECTED and not reason.strip():
        raise ValidationError("Indica el motivo del rechazo.")
    old = quote.get_status_display()
    quote.status = new_status
    quote.status_changed_at = timezone.now()
    quote.updated_by = user
    if new_status == Quote.Status.REJECTED:
        quote.rejection_reason = reason.strip()
    quote.save(update_fields=["status", "status_changed_at", "updated_by", "rejection_reason", "updated_at"])
    note = f"{old} → {quote.get_status_display()}" + (f". Motivo: {reason.strip()}" if reason.strip() else "")
    QuoteFollowUp.objects.create(quote=quote, user=user, kind=QuoteFollowUp.Kind.STATUS, notes=note)
    log_action(
        AuditLog.Action.STATUS_CHANGE,
        request=request,
        user=user,
        obj=quote,
        changes={"estado": {"antes": old, "despues": quote.get_status_display()}},
        message=reason.strip()[:255],
    )
    return quote


@transaction.atomic
def duplicate_quote(*, quote, user, request=None):
    copy = Quote(
        customer=quote.customer,
        valid_until=default_validity(),
        currency=quote.currency,
        tax_rate=quote.tax_rate,
        conditions=quote.conditions,
        notes=quote.notes,
        duplicated_from=quote,
    )
    lines = []
    for item in quote.items.select_related("product__unit"):
        if item.product is None or not item.product.is_active:
            continue
        lines.append(
            {
                "product": item.product,
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "discount_pct": item.discount_pct,
            }
        )
    copy = save_quote(quote=copy, lines=lines, user=user, request=request)
    log_action(AuditLog.Action.DUPLICATE, request=request, user=user, obj=copy, message=f"Copia de {quote.folio}")
    return copy, len(lines) < quote.items.count()


def expire_overdue(today=None):
    """Marca como vencidas las cotizaciones enviadas/en seguimiento cuya vigencia terminó."""
    today = today or timezone.localdate()
    expired = 0
    for quote in Quote.objects.filter(status__in=Quote.OPEN_STATUSES, valid_until__lt=today):
        with transaction.atomic():
            locked = Quote.objects.select_for_update().get(pk=quote.pk)
            if locked.status not in Quote.OPEN_STATUSES:
                continue
            locked.status = Quote.Status.EXPIRED
            locked.status_changed_at = timezone.now()
            locked.save(update_fields=["status", "status_changed_at", "updated_at"])
            log_action(
                AuditLog.Action.STATUS_CHANGE,
                obj=locked,
                username="sistema",
                changes={"estado": {"antes": quote.get_status_display(), "despues": "Vencida"}},
                message="Vigencia terminada",
            )
            expired += 1
    return expired
