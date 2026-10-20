from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.roles import ROLE_ADMIN, ROLE_READONLY, ROLE_SALES
from audit.models import AuditLog
from core.tests.factories import PASSWORD, make_party, make_product, make_user
from quotes.models import Quote, QuoteSequence
from quotes.services import change_status, expire_overdue


def quote_post(customer, items, **extra):
    data = {
        "customer": customer.pk,
        "valid_until": (timezone.localdate() + timedelta(days=10)).isoformat(),
        "currency": "MXN",
        "tax_rate": "16",
        "conditions": "",
        "notes": "",
        "items-TOTAL_FORMS": str(len(items)),
        "items-INITIAL_FORMS": "0",
        "items-MIN_NUM_FORMS": "0",
        "items-MAX_NUM_FORMS": "1000",
    }
    for i, item in enumerate(items):
        for key, value in item.items():
            data[f"items-{i}-{key}"] = value
    data.update(extra)
    return data


class QuoteFlowTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin", ROLE_ADMIN)
        self.sales = make_user("ventas", ROLE_SALES)
        self.other = make_user("ventas2", ROLE_SALES)
        self.reader = make_user("consulta", ROLE_READONLY)
        self.customer = make_party()
        self.p1 = make_product("T-001", reference_price=Decimal("35.0000"))
        self.p2 = make_product("T-002", name="Tapa 38 mm", reference_price=Decimal("1.2500"))
        self.client.login(username="ventas", password=PASSWORD)

    def create_quote(self, items=None, **extra):
        items = items or [
            {"product": self.p1.pk, "quantity": "100", "unit_price": "", "discount_pct": "5"},
            {"product": self.p2.pk, "quantity": "1000", "unit_price": "1.30", "discount_pct": ""},
        ]
        return self.client.post(reverse("quotes:quote_create"), quote_post(self.customer, items, **extra))

    def test_create_calculates_totals_on_server(self):
        response = self.create_quote(**{"total": "1.00", "subtotal": "1.00"})
        quote = Quote.objects.get()
        self.assertRedirects(response, reverse("quotes:quote_detail", args=[quote.pk]))
        # 100 × 35 = 3500 − 5 % = 3325 ; 1000 × 1.30 = 1300 ; neto 4625 ; IVA 740 ; total 5365
        self.assertEqual(quote.subtotal, Decimal("4800.00"))
        self.assertEqual(quote.discount_total, Decimal("175.00"))
        self.assertEqual(quote.tax_total, Decimal("740.00"))
        self.assertEqual(quote.total, Decimal("5365.00"))
        self.assertEqual(quote.owner, self.sales)
        self.assertRegex(quote.folio, r"^COT-\d{4}-00001$")
        item = quote.items.get(sku="T-001")
        self.assertEqual(item.description, self.p1.name)
        self.assertEqual(item.unit_price, Decimal("35.0000"))
        self.assertTrue(AuditLog.objects.filter(action="create", object_id=str(quote.pk)).exists())

    def test_history_preserved_when_product_changes(self):
        self.create_quote()
        self.p1.name = "Nombre nuevo"
        self.p1.reference_price = Decimal("99")
        self.p1.save()
        item = Quote.objects.get().items.get(sku="T-001")
        self.assertEqual(item.description, "Garrafa de prueba 20 L")
        self.assertEqual(item.unit_price, Decimal("35.0000"))

    def test_price_below_reference_rejected_without_permission(self):
        response = self.create_quote([{"product": self.p1.pk, "quantity": "1", "unit_price": "10", "discount_pct": ""}])
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Quote.objects.exists())
        self.client.login(username="admin", password=PASSWORD)
        self.create_quote([{"product": self.p1.pk, "quantity": "1", "unit_price": "10", "discount_pct": ""}])
        self.assertEqual(Quote.objects.get().total, Decimal("11.60"))

    def test_discount_limit(self):
        response = self.create_quote([{"product": self.p1.pk, "quantity": "1", "unit_price": "", "discount_pct": "50"}])
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Quote.objects.exists())

    def test_invalid_quantity_rejected(self):
        for qty in ["0", "-5", "abc"]:
            self.create_quote([{"product": self.p1.pk, "quantity": qty, "unit_price": "", "discount_pct": ""}])
        self.assertFalse(Quote.objects.exists())

    def test_requires_items(self):
        self.create_quote([{"product": self.p1.pk, "quantity": "1", "DELETE": "on"}])
        self.assertFalse(Quote.objects.exists())

    def test_edit_replaces_items_and_logs_changes(self):
        self.create_quote()
        quote = Quote.objects.get()
        items = [{"product": self.p1.pk, "quantity": "10", "unit_price": "", "discount_pct": ""}]
        self.client.post(reverse("quotes:quote_update", args=[quote.pk]), quote_post(self.customer, items))
        quote.refresh_from_db()
        self.assertEqual(quote.items.count(), 1)
        self.assertEqual(quote.total, Decimal("406.00"))
        log = AuditLog.objects.filter(action="update", object_id=str(quote.pk)).first()
        self.assertIn("partidas", log.changes)

    def test_other_user_cannot_edit(self):
        self.create_quote()
        quote = Quote.objects.get()
        self.client.login(username="ventas2", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("quotes:quote_update", args=[quote.pk])).status_code, 403)
        self.assertEqual(
            self.client.post(reverse("quotes:quote_status", args=[quote.pk]), {"status": "enviada"}).status_code, 403
        )

    def test_reader_cannot_create(self):
        self.client.login(username="consulta", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("quotes:quote_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("quotes:quote_create")).status_code, 403)

    def test_status_flow_and_rejection_reason(self):
        self.create_quote()
        quote = Quote.objects.get()
        url = reverse("quotes:quote_status", args=[quote.pk])
        self.client.post(url, {"status": "aprobada"})
        quote.refresh_from_db()
        self.assertEqual(quote.status, "borrador")  # transición inválida
        self.client.post(url, {"status": "enviada"})
        self.client.post(url, {"status": "rechazada", "reason": ""})
        quote.refresh_from_db()
        self.assertEqual(quote.status, "enviada")
        self.client.post(url, {"status": "rechazada", "reason": "Precio alto"})
        quote.refresh_from_db()
        self.assertEqual(quote.status, "rechazada")
        self.assertEqual(quote.rejection_reason, "Precio alto")
        self.assertEqual(quote.follow_ups.filter(kind="estado").count(), 2)
        self.assertEqual(self.client.get(reverse("quotes:quote_update", args=[quote.pk])).status_code, 403)

    def test_follow_up_duplicate_and_pdf(self):
        self.create_quote()
        quote = Quote.objects.get()
        self.client.post(reverse("quotes:quote_follow_up", args=[quote.pk]), {"kind": "llamada", "notes": "Llamé"})
        self.assertEqual(quote.follow_ups.count(), 1)
        response = self.client.post(reverse("quotes:quote_duplicate", args=[quote.pk]))
        copy = Quote.objects.exclude(pk=quote.pk).get()
        self.assertRedirects(response, reverse("quotes:quote_detail", args=[copy.pk]))
        self.assertEqual(copy.total, quote.total)
        self.assertEqual(copy.duplicated_from, quote)
        self.assertNotEqual(copy.folio, quote.folio)
        pdf = self.client.get(reverse("quotes:quote_pdf", args=[quote.pk]) + "?descargar=1")
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.assertIn("attachment", pdf["Content-Disposition"])

    def test_filters(self):
        self.create_quote()
        response = self.client.get(reverse("quotes:quote_list"), {"estado": "borrador", "q": "COT"})
        self.assertEqual(len(response.context["quotes"]), 1)
        response = self.client.get(reverse("quotes:quote_list"), {"estado": "aprobada"})
        self.assertEqual(len(response.context["quotes"]), 0)

    def test_expire_overdue(self):
        self.create_quote()
        quote = Quote.objects.get()
        change_status(quote=quote, new_status="enviada", user=self.sales)
        Quote.objects.filter(pk=quote.pk).update(valid_until=timezone.localdate() - timedelta(days=1))
        self.assertEqual(expire_overdue(), 1)
        quote.refresh_from_db()
        self.assertEqual(quote.status, "vencida")

    def test_sequence(self):
        a, b = QuoteSequence.next_folio(2030), QuoteSequence.next_folio(2030)
        self.assertEqual((a, b), ("COT-2030-00001", "COT-2030-00002"))
