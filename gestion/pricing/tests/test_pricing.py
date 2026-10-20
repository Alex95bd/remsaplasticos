from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from accounts.roles import ROLE_ADMIN, ROLE_SALES, ROLE_WAREHOUSE
from audit.models import AuditLog
from core.tests.factories import PASSWORD, make_party, make_product, make_user
from pricing import services
from pricing.models import PriceChange, PriceList, PriceListItem
from pricing.parser import parse_dictation


class ParserTests(SimpleTestCase):
    today = date(2026, 10, 20)

    def test_full_dictation(self):
        r = parse_dictation(
            "Botella BOT-500 a 3 pesos con 50 centavos, mínimo mil piezas, lista mayoreo, "
            "vigente hasta el 31 de diciembre",
            today=self.today,
        )
        self.assertEqual(r.sku, "BOT-500")
        self.assertEqual(r.unit_price, Decimal("3.50"))
        self.assertEqual(r.currency, "MXN")
        self.assertEqual(r.min_quantity, Decimal("1000"))
        self.assertEqual(r.unit, "PZA")
        self.assertEqual(r.price_list, "mayoreo")
        self.assertEqual(r.valid_until, date(2026, 12, 31))
        self.assertEqual(r.warnings, [])

    def test_spoken_sku_and_dollars(self):
        r = parse_dictation("sku gar 20 precio 42.80 dólares a partir de quinientas piezas", today=self.today)
        self.assertEqual((r.sku, r.unit_price, r.currency, r.min_quantity), ("GAR-20", Decimal("42.80"), "USD", 500))

    def test_missing_price_warns(self):
        r = parse_dictation("tapa 38 milímetros", today=self.today)
        self.assertIsNone(r.unit_price)
        self.assertFalse(r.is_complete)
        self.assertTrue(r.warnings)


class PricingTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin", ROLE_ADMIN)
        self.sales = make_user("ventas", ROLE_SALES)
        self.clerk = make_user("almacen", ROLE_WAREHOUSE)
        self.product = make_product("BOT-500", name="Botella PET 500 ml", reference_price=Decimal("3.0000"))
        self.customer = make_party()
        self.general = PriceList.objects.create(code="may", name="Mayoreo")
        self.special = PriceList.objects.create(code="ESP", name="Especial", customer=self.customer)

    def test_set_price_records_history_and_audit(self):
        services.set_price(
            price_list=self.general,
            product=self.product,
            min_quantity=Decimal("1"),
            unit_price=Decimal("3.5"),
            user=self.admin,
        )
        _, change = services.set_price(
            price_list=self.general,
            product=self.product,
            min_quantity=Decimal("1"),
            unit_price=Decimal("3.6"),
            user=self.admin,
        )
        self.assertEqual(change.old_price, Decimal("3.5000"))
        _, none = services.set_price(
            price_list=self.general,
            product=self.product,
            min_quantity=Decimal("1"),
            unit_price=Decimal("3.6"),
            user=self.admin,
        )
        self.assertIsNone(none)
        self.assertEqual(PriceChange.objects.count(), 2)
        self.assertEqual(AuditLog.objects.filter(action="price_change").count(), 2)
        with self.assertRaises(ValueError):
            change.save()

    def test_resolve_price_by_customer_and_volume(self):
        for pl, qty, price in [(self.general, "1", "3.5"), (self.general, "1000", "3.2"), (self.special, "1", "3.1")]:
            services.set_price(
                price_list=pl,
                product=self.product,
                min_quantity=Decimal(qty),
                unit_price=Decimal(price),
                user=self.admin,
            )
        self.assertEqual(services.resolve_price(self.product, None, Decimal("10")).unit_price, Decimal("3.5"))
        self.assertEqual(services.resolve_price(self.product, None, Decimal("5000")).unit_price, Decimal("3.2"))
        self.assertEqual(services.resolve_price(self.product, self.customer, Decimal("10")).unit_price, Decimal("3.1"))

    def test_find_products_fuzzy(self):
        found, exact = services.find_products("BOT500")
        self.assertFalse(exact)
        self.assertEqual(found[0], self.product)
        found, exact = services.find_products("bot-500")
        self.assertTrue(exact)

    def test_dictation_flow_requires_confirmation(self):
        self.client.login(username="admin", password=PASSWORD)
        url = reverse("pricing:dictation")
        self.assertEqual(self.client.get(url).status_code, 200)
        r = self.client.post(
            url,
            {
                "step": "interpret",
                "source": "voz",
                "transcript": "BOT-500 a 3 pesos con 80 centavos mínimo mil piezas lista mayoreo",
            },
        )
        form = r.context["form"]
        self.assertEqual(form.initial["product"], self.product.pk)
        self.assertEqual(form.initial["price_list"], self.general.pk)
        self.assertFalse(PriceListItem.objects.exists())
        data = {
            "price_list": self.general.pk,
            "product": self.product.pk,
            "min_quantity": "1000",
            "unit_price": "3.80",
            "currency": "MXN",
            "source": "voz",
            "transcript": "BOT-500 a 3.80",
        }
        r = self.client.post(url, {"step": "preview", **data})
        self.assertEqual(r.context["step"], "preview")
        self.assertFalse(PriceListItem.objects.exists())
        r = self.client.post(url, {"step": "confirm", **data})
        self.assertRedirects(r, reverse("pricing:pricelist_detail", args=[self.general.pk]))
        change = PriceChange.objects.get()
        self.assertEqual(change.source, "voz")
        self.assertEqual(change.new_price, Decimal("3.8000"))

    def test_currency_mismatch_blocks(self):
        self.client.login(username="admin", password=PASSWORD)
        r = self.client.post(
            reverse("pricing:dictation"),
            {
                "step": "confirm",
                "price_list": self.general.pk,
                "product": self.product.pk,
                "min_quantity": "1",
                "unit_price": "3.8",
                "currency": "USD",
                "source": "texto",
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertFalse(PriceListItem.objects.exists())

    def test_permissions_and_exports(self):
        services.set_price(
            price_list=self.general,
            product=self.product,
            min_quantity=Decimal("1"),
            unit_price=Decimal("3.5"),
            user=self.admin,
        )
        self.client.login(username="ventas", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("pricing:pricelist_detail", args=[self.general.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("pricing:dictation")).status_code, 403)
        r = self.client.get(reverse("pricing:export", args=[self.general.pk, "pdf"]))
        self.assertTrue(r.content.startswith(b"%PDF"))
        r = self.client.get(reverse("pricing:export", args=[self.general.pk, "xlsx"]))
        self.assertEqual(r.status_code, 200)
        self.client.login(username="almacen", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("pricing:pricelist_list")).status_code, 403)

    def test_manual_set_and_delete(self):
        self.client.login(username="admin", password=PASSWORD)
        self.client.post(
            reverse("pricing:item_set", args=[self.general.pk]),
            {"product": self.product.pk, "min_quantity": "1", "unit_price": "4"},
        )
        item = PriceListItem.objects.get()
        self.client.post(reverse("pricing:item_delete", args=[self.general.pk, item.pk]))
        self.assertFalse(PriceListItem.objects.exists())
        self.assertEqual(PriceChange.objects.filter(new_price__isnull=True).count(), 1)
