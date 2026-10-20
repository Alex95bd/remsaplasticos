"""Carga datos de DEMOSTRACIÓN claramente identificados.

- Los productos usan SKU con prefijo ``DEMO-`` y la descripción inicia con ``[DEMO]``.
- Las categorías de demostración tienen la descripción ``[DEMO] ...``.
- Los precios son ficticios y solo sirven para probar la aplicación.

Uso:
    python manage.py cargar_demo
    python manage.py cargar_demo --usuarios --password "UnaClaveSegura2026"
    python manage.py cargar_demo --eliminar
"""

from decimal import Decimal

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from accounts.roles import ROLE_ADMIN, ROLE_READONLY, ROLE_SALES, ROLE_WAREHOUSE
from catalog.models import Category, Product, UnitOfMeasure

DEMO_TAG = "[DEMO]"
SKU_PREFIX = "DEMO-"

CATEGORIES = [
    "Botellas PET",
    "Frascos PET",
    "Garrafas PEAD",
    "Garrafones y botellones",
    "Preformas",
    "Tapas",
]

# sku, nombre, categoría, tipo, unidad, presentación, capacidad ml, alto, diámetro, peso g, precio
PRODUCTS = [
    (
        "BOT-500",
        "Botella PET 500 ml cristal",
        "Botellas PET",
        "terminado",
        "PZA",
        "Caja con 300 piezas",
        "500",
        "205",
        "65",
        "18",
        "1.85",
    ),
    (
        "BOT-1000",
        "Botella PET 1 L cristal",
        "Botellas PET",
        "terminado",
        "PZA",
        "Caja con 200 piezas",
        "1000",
        "260",
        "80",
        "28",
        "2.60",
    ),
    (
        "FRA-250",
        "Frasco PET 250 ml boca ancha",
        "Frascos PET",
        "terminado",
        "PZA",
        "Caja con 400 piezas",
        "250",
        "95",
        "70",
        "22",
        "2.10",
    ),
    (
        "GAR-5L",
        "Garrafa PEAD 5 L natural",
        "Garrafas PEAD",
        "terminado",
        "PZA",
        "Bolsa con 60 piezas",
        "5000",
        "300",
        "175",
        "180",
        "14.50",
    ),
    (
        "GAR-20L",
        "Garrafa PEAD 20 L natural",
        "Garrafas PEAD",
        "terminado",
        "PZA",
        "Tarima con 120 piezas",
        "20000",
        "430",
        "290",
        "900",
        "35.00",
    ),
    (
        "GFN-20L",
        "Garrafón PET 20 L azul",
        "Garrafones y botellones",
        "terminado",
        "PZA",
        "Tarima con 90 piezas",
        "20000",
        "490",
        "270",
        "720",
        "68.00",
    ),
    (
        "PRE-28-18",
        "Preforma PET 18 g cuello 28 mm",
        "Preformas",
        "semiterminado",
        "MIL",
        "Caja con 5,000 piezas",
        None,
        "95",
        "28",
        "18",
        "780.00",
    ),
    (
        "TAP-28",
        "Tapa plástica 28 mm blanca",
        "Tapas",
        "terminado",
        "MIL",
        "Bolsa con 2,000 piezas",
        None,
        "16",
        "30",
        "2.5",
        "320.00",
    ),
]

DEMO_USERS = [
    ("demo.admin", "Admin", ROLE_ADMIN),
    ("demo.ventas", "Ventas", ROLE_SALES),
    ("demo.almacen", "Almacén", ROLE_WAREHOUSE),
    ("demo.consulta", "Consulta", ROLE_READONLY),
]


def _dec(value):
    return Decimal(value) if value is not None else None


class Command(BaseCommand):
    help = "Carga o elimina datos de demostración (identificados con DEMO)."

    def add_arguments(self, parser):
        parser.add_argument("--eliminar", action="store_true", help="Elimina los datos de demostración.")
        parser.add_argument("--usuarios", action="store_true", help="Crea usuarios demo.* para cada rol.")
        parser.add_argument("--password", help="Contraseña para los usuarios demo (obligatoria con --usuarios).")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["eliminar"]:
            return self.remove()
        if options["usuarios"] and not options["password"]:
            raise CommandError("Indica --password para los usuarios demo; no se usan contraseñas predeterminadas.")

        categories = {}
        for name in CATEGORIES:
            category, _ = Category.objects.get_or_create(
                name=name, defaults={"description": f"{DEMO_TAG} Categoría de demostración."}
            )
            categories[name] = category

        units = {unit.code: unit for unit in UnitOfMeasure.objects.all()}
        created = 0
        for sku, name, category, ptype, unit, presentation, cap, height, diameter, weight, price in PRODUCTS:
            _, was_created = Product.objects.update_or_create(
                sku=f"{SKU_PREFIX}{sku}",
                defaults={
                    "name": name,
                    "description": f"{DEMO_TAG} Producto de demostración; datos y precio ficticios.",
                    "category": categories[category],
                    "product_type": ptype,
                    "unit": units[unit],
                    "presentation": presentation,
                    "capacity_ml": _dec(cap),
                    "height_mm": _dec(height),
                    "diameter_mm": _dec(diameter),
                    "weight_g": _dec(weight),
                    "reference_price": _dec(price),
                },
            )
            created += was_created
        self.stdout.write(self.style.SUCCESS(f"Productos demo: {len(PRODUCTS)} ({created} nuevos)."))

        if options["usuarios"]:
            for username, label, role in DEMO_USERS:
                user, _ = User.objects.get_or_create(
                    username=username,
                    defaults={"email": f"{username}@demo.invalid", "first_name": "Demo", "last_name": label},
                )
                user.set_password(options["password"])
                user.save()
                user.groups.set([Group.objects.get(name=role)])
            self.stdout.write(self.style.SUCCESS("Usuarios demo: " + ", ".join(u[0] for u in DEMO_USERS)))

    def remove(self):
        products, _ = Product.objects.filter(sku__startswith=SKU_PREFIX).delete()
        categories, _ = Category.objects.filter(description__startswith=DEMO_TAG, products__isnull=True).delete()
        users, _ = User.objects.filter(username__startswith="demo.", email__endswith="@demo.invalid").delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Eliminados: {products} productos, {categories} categorías, {users} registros de usuarios."
            )
        )
