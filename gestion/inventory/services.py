"""Movimientos de inventario. Cada operación es atómica y bloquea las existencias involucradas."""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from audit.models import AuditLog
from audit.services import log_action

from .models import Stock, StockMovement, new_transfer_id


def _locked_stock(product, warehouse):
    Stock.objects.get_or_create(product=product, warehouse=warehouse)
    return Stock.objects.select_for_update().get(product=product, warehouse=warehouse)


def _check_inputs(product, warehouse, quantity):
    if quantity is None or quantity <= 0:
        raise ValidationError("La cantidad debe ser mayor que cero.")
    if not product.is_active:
        raise ValidationError("El producto está inactivo.")
    if not warehouse.is_active:
        raise ValidationError(f"El almacén {warehouse.code} está inactivo.")


def _apply(stock, delta, *, kind, user, reason, request=None, log=True, **extra):
    new_balance = stock.quantity + delta
    if new_balance < 0 and not settings.INVENTORY_ALLOW_NEGATIVE:
        raise ValidationError(
            f"Existencia insuficiente de {stock.product.sku} en {stock.warehouse.code}: "
            f"hay {stock.quantity.normalize():f}, se requieren {abs(delta).normalize():f}."
        )
    stock.quantity = new_balance
    stock.save(update_fields=["quantity", "updated_at"])
    movement = StockMovement.objects.create(
        kind=kind,
        product=stock.product,
        warehouse=stock.warehouse,
        quantity=delta,
        balance_after=new_balance,
        user=user,
        reason=reason.strip(),
        **extra,
    )
    if log:
        log_action(
            AuditLog.Action.MOVEMENT,
            request=request,
            user=user,
            obj=movement,
            message=f"{movement.get_kind_display()} {stock.product.sku} {delta:+f} en {stock.warehouse.code} "
            f"(saldo {new_balance.normalize():f}). {reason}"[:255],
        )
    return movement


@transaction.atomic
def register_entry(*, product, warehouse, quantity, user, reason, reference="", notes="", location=None, request=None):
    _check_inputs(product, warehouse, quantity)
    stock = _locked_stock(product, warehouse)
    return _apply(
        stock,
        quantity,
        kind=StockMovement.Kind.IN,
        user=user,
        reason=reason,
        request=request,
        reference=reference,
        notes=notes,
        location=location,
    )


@transaction.atomic
def register_exit(*, product, warehouse, quantity, user, reason, reference="", notes="", location=None, request=None):
    _check_inputs(product, warehouse, quantity)
    stock = _locked_stock(product, warehouse)
    return _apply(
        stock,
        -quantity,
        kind=StockMovement.Kind.OUT,
        user=user,
        reason=reason,
        request=request,
        reference=reference,
        notes=notes,
        location=location,
    )


@transaction.atomic
def register_adjustment(*, product, warehouse, counted, user, reason, reference="", notes="", request=None):
    """Ajusta la existencia al conteo físico. Requiere permiso de autorización."""
    if not user.has_perm("inventory.authorize_adjustment"):
        raise PermissionDenied("Los ajustes requieren autorización.")
    if counted is None or counted < 0:
        raise ValidationError("El conteo físico no puede ser negativo.")
    if not reason.strip():
        raise ValidationError("Indica el motivo del ajuste.")
    stock = _locked_stock(product, warehouse)
    delta = counted - stock.quantity
    if delta == 0:
        raise ValidationError("El conteo coincide con la existencia registrada; no hay nada que ajustar.")
    return _apply(
        stock,
        delta,
        kind=StockMovement.Kind.ADJUST,
        user=user,
        reason=reason,
        request=request,
        reference=reference,
        notes=notes,
        authorized_by=user,
    )


@transaction.atomic
def transfer(*, product, source, target, quantity, user, reason, reference="", notes="", request=None):
    if source.pk == target.pk:
        raise ValidationError("El almacén de origen y destino deben ser distintos.")
    _check_inputs(product, source, quantity)
    _check_inputs(product, target, quantity)
    # Bloqueo en orden fijo para evitar interbloqueos entre transferencias opuestas.
    first, second = sorted([source, target], key=lambda w: w.pk)
    locked = {first.pk: _locked_stock(product, first), second.pk: _locked_stock(product, second)}
    transfer_id = new_transfer_id()
    out = _apply(
        locked[source.pk],
        -quantity,
        kind=StockMovement.Kind.TRANSFER_OUT,
        user=user,
        reason=reason,
        reference=reference,
        notes=notes,
        transfer_id=transfer_id,
        log=False,
    )
    inc = _apply(
        locked[target.pk],
        quantity,
        kind=StockMovement.Kind.TRANSFER_IN,
        user=user,
        reason=reason,
        reference=reference,
        notes=notes,
        transfer_id=transfer_id,
        log=False,
    )
    log_action(
        AuditLog.Action.MOVEMENT,
        request=request,
        user=user,
        obj=out,
        message=f"Transferencia {product.sku} {quantity.normalize():f} de {source.code} a {target.code}. {reason}"[
            :255
        ],
    )
    return out, inc


@transaction.atomic
def reverse_movement(*, movement, user, reason, request=None):
    """Cancela un movimiento con otro de signo contrario; el original se conserva intacto."""
    if not user.has_perm("inventory.authorize_adjustment"):
        raise PermissionDenied("Cancelar movimientos requiere autorización.")
    movement = StockMovement.objects.select_for_update().get(pk=movement.pk)
    if movement.kind == StockMovement.Kind.REVERSAL:
        raise ValidationError("No se puede cancelar una cancelación.")
    if movement.transfer_id:
        raise ValidationError("Las transferencias se cancelan registrando la transferencia inversa.")
    if StockMovement.objects.filter(reverses=movement).exists():
        raise ValidationError("Este movimiento ya fue cancelado.")
    if not reason.strip():
        raise ValidationError("Indica el motivo de la cancelación.")
    stock = _locked_stock(movement.product, movement.warehouse)
    return _apply(
        stock,
        -movement.quantity,
        kind=StockMovement.Kind.REVERSAL,
        user=user,
        request=request,
        reason=reason,
        reference=movement.reference,
        reverses=movement,
        authorized_by=user,
    )


def low_stock_queryset():
    from django.db.models import F

    return Stock.objects.filter(min_quantity__gt=0, quantity__lte=F("min_quantity"), product__is_active=True)


ZERO = Decimal("0")
