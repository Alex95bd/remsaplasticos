import difflib
import re
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from audit.models import AuditLog
from audit.services import log_action
from catalog.models import Product, normalize_sku

from .models import PriceChange, PriceList, PriceListItem


def find_products(sku="", text="", limit=5):
    """Busca candidatos para un dictado: SKU exacto, SKU parecido o nombre parecido."""
    products = Product.objects.filter(is_active=True).select_related("unit")
    if sku:
        exact = products.filter(sku=normalize_sku(sku)).first()
        if exact:
            return [exact], True
    candidates = []
    if sku:
        compact = re.sub(r"[^A-Z0-9]", "", sku.upper())
        all_skus = {
            re.sub(r"[^A-Z0-9]", "", p.sku): p for p in Product.objects.filter(is_active=True).only("sku", "name")
        }
        for key in difflib.get_close_matches(compact, list(all_skus), n=limit, cutoff=0.6):
            candidates.append(all_skus[key])
    if text:
        words = [w for w in re.findall(r"\w{3,}", text) if not w.isdigit()][:4]
        q = Q()
        for w in words:
            q &= Q(name__icontains=w)
        if words:
            candidates += [p for p in products.filter(q)[:limit] if p not in candidates]
        if len(candidates) < limit:
            names = {p.name.lower(): p for p in Product.objects.filter(is_active=True).only("sku", "name")}
            for key in difflib.get_close_matches(text.lower(), list(names), n=limit, cutoff=0.45):
                if names[key] not in candidates:
                    candidates.append(names[key])
    return candidates[:limit], False


def find_price_list(text):
    if not text:
        return None
    lists = PriceList.objects.filter(is_active=True).select_related("customer")
    text_l = text.lower()
    for pl in lists:
        if text_l in (pl.code.lower(), pl.name.lower()) or (pl.customer and text_l in pl.customer.name.lower()):
            return pl
    names = {pl.name.lower(): pl for pl in lists}
    match = difflib.get_close_matches(text_l, list(names), n=1, cutoff=0.6)
    return names[match[0]] if match else None


def current_item(price_list, product, min_quantity):
    return PriceListItem.objects.filter(price_list=price_list, product=product, min_quantity=min_quantity).first()


@transaction.atomic
def set_price(
    *,
    price_list,
    product,
    min_quantity,
    unit_price,
    user,
    source=PriceChange.Source.MANUAL,
    transcript="",
    request=None,
):
    """Crea o actualiza un precio y registra el cambio. Devuelve (item, cambio o None si no hubo cambio)."""
    item = (
        PriceListItem.objects.select_for_update()
        .filter(price_list=price_list, product=product, min_quantity=min_quantity)
        .first()
    )
    old = item.unit_price if item else None
    if old is not None and old == unit_price:
        return item, None
    if item is None:
        item = PriceListItem(price_list=price_list, product=product, min_quantity=min_quantity)
    item.unit_price = unit_price
    item.updated_by = user
    item.save()
    change = PriceChange.objects.create(
        user=user,
        price_list=price_list,
        product=product,
        min_quantity=min_quantity,
        old_price=old,
        new_price=unit_price,
        source=source,
        transcript=transcript,
    )
    log_action(
        AuditLog.Action.PRICE_CHANGE,
        request=request,
        user=user,
        obj=price_list,
        changes={
            f"{product.sku} (≥{min_quantity.normalize():f})": {
                "antes": f"{old:f}" if old is not None else None,
                "despues": f"{unit_price:f}",
            }
        },
        message=f"{change.get_source_display()}: {product.sku} {old if old is not None else '—'} → {unit_price}"[:255],
    )
    return item, change


@transaction.atomic
def remove_price(*, item, user, request=None):
    PriceChange.objects.create(
        user=user,
        price_list=item.price_list,
        product=item.product,
        min_quantity=item.min_quantity,
        old_price=item.unit_price,
        new_price=None,
    )
    log_action(
        AuditLog.Action.PRICE_CHANGE,
        request=request,
        user=user,
        obj=item.price_list,
        message=f"Precio eliminado: {item.product.sku} ≥{item.min_quantity.normalize():f}",
    )
    item.delete()


def resolve_price(product, customer=None, quantity=Decimal("1"), on=None, currency=None):
    """Precio vigente para un cliente: lista del cliente, si no la lista general; mayor escalón ≤ cantidad."""
    on = on or timezone.localdate()
    lists = PriceList.objects.filter(is_active=True, valid_from__lte=on).filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=on)
    )
    if currency:
        lists = lists.filter(currency=currency)
    for scope in ([customer] if customer else []) + [None]:
        qs = PriceListItem.objects.filter(
            price_list__in=lists.filter(customer=scope), product=product, min_quantity__lte=quantity
        ).order_by("-min_quantity", "unit_price")
        item = qs.first()
        if item:
            return item
    return None
