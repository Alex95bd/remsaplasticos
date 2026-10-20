from django.test import TestCase
from django.urls import reverse

from accounts.roles import ROLE_ADMIN, ROLE_WAREHOUSE
from audit.models import AuditLog

from .factories import PASSWORD, make_product, make_user


class DashboardTests(TestCase):
    def test_requires_login(self):
        response = self.client.get(reverse("core:dashboard"))
        self.assertRedirects(response, f"{reverse('login')}?next=/")

    def test_health_is_public(self):
        response = self.client.get(reverse("core:health"))
        self.assertEqual(response.json(), {"status": "ok"})

    def test_kpis_use_database_values(self):
        make_product("A-1")
        make_product("A-2", is_active=False)
        make_product("A-3", reference_price=None)
        admin = make_user("jefa", ROLE_ADMIN)
        self.client.force_login(admin)
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.context["product_stats"], {"active": 2, "inactive": 1, "without_price": 1})
        self.assertEqual(response.context["active_users"], 1)
        self.assertContains(response, "Usuarios activos")

    def test_warehouse_sees_no_price_kpi_nor_users(self):
        self.client.force_login(make_user("almacen", ROLE_WAREHOUSE))
        response = self.client.get(reverse("core:dashboard"))
        self.assertNotContains(response, "sin precio de referencia")
        self.assertNotIn("active_users", response.context)
        self.assertEqual(response.context["activity_scope"], "own")


class LoginAuditTests(TestCase):
    def test_login_logout_and_failure_are_logged(self):
        make_user("ventas1")
        self.client.post(reverse("login"), {"username": "ventas1", "password": "incorrecta"})
        self.client.post(reverse("login"), {"username": "ventas1", "password": PASSWORD})
        self.client.post(reverse("logout"))
        actions = list(AuditLog.objects.order_by("id").values_list("action", flat=True))
        self.assertEqual(actions, ["login_failed", "login", "logout"])
        failed = AuditLog.objects.get(action="login_failed")
        self.assertEqual(failed.username, "ventas1")
        self.assertNotIn("incorrecta", str(failed.changes) + failed.message)

    def test_logout_requires_post(self):
        self.client.force_login(make_user("u1"))
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
