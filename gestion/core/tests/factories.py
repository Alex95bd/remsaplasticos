from decimal import Decimal

from django.contrib.auth.models import Group

from accounts.models import User
from catalog.models import Category, Product, UnitOfMeasure

PASSWORD = "Prueba-Segura-2026"


def make_user(username, *roles, **extra):
    user = User.objects.create_user(username=username, email=f"{username}@example.com", password=PASSWORD, **extra)
    if roles:
        user.groups.set(Group.objects.filter(name__in=roles))
    return user


def make_category(name="Garrafas PEAD"):
    return Category.objects.create(name=name)


def make_product(sku="T-001", category=None, **extra):
    data = {
        "name": "Garrafa de prueba 20 L",
        "category": category or Category.objects.first() or make_category(),
        "unit": UnitOfMeasure.objects.get(code="PZA"),
        "reference_price": Decimal("35.0000"),
    }
    data.update(extra)
    return Product.objects.create(sku=sku, **data)
