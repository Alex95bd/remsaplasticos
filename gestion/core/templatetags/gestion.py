from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def money(value, decimals=2):
    """Formatea un importe con separador de miles: 1234.5 -> 1,234.50."""
    if value is None or value == "":
        return "—"
    try:
        number = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return value
    return f"{number:,.{int(decimals)}f}"


@register.filter
def number(value):
    """Muestra un decimal sin ceros sobrantes: 20.000 -> 20."""
    if value is None or value == "":
        return "—"
    try:
        number = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return value
    text = f"{number:,f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


@register.simple_tag(takes_context=True)
def nav_active(context, *names):
    """Devuelve 'active' si la vista actual coincide con algún ``namespace`` o ``namespace:nombre``."""
    match = getattr(context.get("request"), "resolver_match", None)
    if not match:
        return ""
    current = f"{match.namespace}:{match.url_name}" if match.namespace else match.url_name
    for name in names:
        if name == current or (":" not in name and name == match.namespace):
            return "active"
    return ""
