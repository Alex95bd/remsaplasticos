import datetime
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.db import models

from .models import AuditLog

SENSITIVE_FIELDS = {"password", "password1", "password2", "new_password1", "new_password2", "old_password"}


def client_ip(request):
    return request.META.get("REMOTE_ADDR") or None


def serialize_value(value):
    if value is None:
        return None
    if isinstance(value, bool | int | str):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime.date | datetime.datetime):
        return value.isoformat()
    if isinstance(value, models.Model):
        return str(value)
    if isinstance(value, list | tuple | set):
        return sorted(str(item) for item in value)
    return str(value)


def model_snapshot(instance, fields):
    """Devuelve un diccionario legible con los valores actuales de ``fields``."""
    snapshot = {}
    for name in fields:
        if name in SENSITIVE_FIELDS:
            continue
        try:
            field = instance._meta.get_field(name)
        except Exception:
            continue
        if field.many_to_many:
            value = list(getattr(instance, name).all()) if instance.pk else []
        elif field.is_relation:
            value = getattr(instance, name)
        else:
            value = getattr(instance, field.attname)
            if isinstance(field, models.DecimalField) and value is not None:
                value = Decimal(value).quantize(Decimal(1).scaleb(-field.decimal_places))
        if getattr(field, "choices", None) and not field.is_relation:
            value = dict(field.flatchoices).get(value, value)
        snapshot[name] = serialize_value(value)
    return snapshot


def diff_snapshots(before, after):
    changes = {}
    for name, new in after.items():
        old = before.get(name)
        if old != new and not (old in (None, "", []) and new in (None, "", [])):
            changes[name] = {"antes": old, "despues": new}
    return changes


def log_action(action, *, request=None, user=None, obj=None, message="", changes=None, username=""):
    if user is None and request is not None and getattr(request, "user", None) is not None:
        if request.user.is_authenticated:
            user = request.user
    entry = AuditLog(
        user=user,
        username=(user.get_username() if user else username)[:150],
        action=action,
        message=message[:255],
        changes=changes or {},
    )
    if obj is not None:
        entry.content_type = ContentType.objects.get_for_model(obj)
        entry.object_id = str(obj.pk)
        entry.object_repr = str(obj)[:200]
    if request is not None:
        entry.ip_address = client_ip(request)
        entry.user_agent = request.META.get("HTTP_USER_AGENT", "")[:255]
    entry.save()
    return entry
