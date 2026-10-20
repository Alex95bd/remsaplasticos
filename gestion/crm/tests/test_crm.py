from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.roles import ROLE_ADMIN, ROLE_SALES, ROLE_WAREHOUSE
from audit.models import AuditLog
from core.tests.factories import PASSWORD, make_party, make_user
from crm.models import Party


def party_data(**extra):
    data = {
        "party_type": "cliente", "person_type": "moral", "name": "Envases del Sureste SA de CV",
        "rfc": "ESU010101AB1", "payment_terms_days": 30, "is_active": "on",
    }  # fmt: skip
    data.update(extra)
    return data


class PartyModelTests(TestCase):
    def test_rfc_normalized_and_length_by_person_type(self):
        party = Party(name="Juan Pérez", party_type="cliente", person_type="moral", rfc="pexj-800101-ab1")
        with self.assertRaises(ValidationError):
            party.full_clean()
        party.person_type = "fisica"
        party.full_clean()
        self.assertEqual(party.rfc, "PEXJ800101AB1")

    def test_duplicate_rules(self):
        make_party(name="Plásticos Uno", rfc="PUN010101AB1")
        dup = Party(name="  plásticos   uno ", party_type="cliente", rfc="")
        with self.assertRaises(ValidationError) as ctx:
            dup.full_clean()
        self.assertIn("name", ctx.exception.message_dict)
        dup = Party(name="Otro", party_type="cliente", rfc="PUN010101AB1")
        with self.assertRaises(ValidationError):
            dup.full_clean()

    def test_generic_rfc_can_repeat(self):
        make_party(name="Público A", rfc="XAXX010101000")
        Party(name="Público B", party_type="cliente", rfc="XAXX010101000").full_clean()

    @override_settings(CRM_DUPLICATE_RULES=["rfc"])
    def test_rules_are_configurable(self):
        make_party(name="Mismo Nombre")
        Party(name="Mismo Nombre", party_type="cliente").full_clean()


class PartyViewTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin", ROLE_ADMIN)
        self.sales = make_user("ventas", ROLE_SALES)
        self.warehouse = make_user("almacen", ROLE_WAREHOUSE)

    def test_sales_can_create_and_audit_is_written(self):
        self.client.login(username="ventas", password=PASSWORD)
        response = self.client.post(reverse("crm:party_create"), party_data())
        party = Party.objects.get()
        self.assertRedirects(response, reverse("crm:party_detail", args=[party.pk]))
        self.assertEqual(party.created_by, self.sales)
        self.assertTrue(AuditLog.objects.filter(action="create", object_id=str(party.pk)).exists())

    def test_invalid_rfc_rejected(self):
        self.client.login(username="admin", password=PASSWORD)
        response = self.client.post(reverse("crm:party_create"), party_data(rfc="123"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Party.objects.exists())

    def test_warehouse_reads_but_cannot_write(self):
        party = make_party()
        self.client.login(username="almacen", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("crm:party_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("crm:party_detail", args=[party.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("crm:party_create")).status_code, 403)
        self.assertEqual(self.client.post(reverse("crm:party_toggle_active", args=[party.pk])).status_code, 403)

    def test_filters(self):
        make_party(name="Cliente Alfa")
        make_party(name="Proveedor Beta", party_type="proveedor")
        make_party(name="Cliente Inactivo", is_active=False)
        self.client.login(username="admin", password=PASSWORD)
        names = [p.name for p in self.client.get(reverse("crm:party_list"), {"tipo": "proveedor"}).context["parties"]]
        self.assertEqual(names, ["Proveedor Beta"])
        names = [p.name for p in self.client.get(reverse("crm:party_list"), {"q": "alfa"}).context["parties"]]
        self.assertEqual(names, ["Cliente Alfa"])
        names = [p.name for p in self.client.get(reverse("crm:party_list"), {"estado": "inactivos"}).context["parties"]]
        self.assertEqual(names, ["Cliente Inactivo"])

    def test_toggle_active(self):
        party = make_party()
        self.client.login(username="admin", password=PASSWORD)
        self.client.post(reverse("crm:party_toggle_active", args=[party.pk]))
        party.refresh_from_db()
        self.assertFalse(party.is_active)
