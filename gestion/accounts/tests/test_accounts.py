from django.contrib.auth.models import Group
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from accounts.roles import ROLE_ADMIN, ROLE_NAMES, ROLE_READONLY, ROLE_SALES, ROLE_WAREHOUSE, sync_roles
from audit.models import AuditLog
from core.tests.factories import PASSWORD, make_user


class RolesTests(TestCase):
    def test_roles_created_after_migrate(self):
        self.assertEqual(set(Group.objects.values_list("name", flat=True)), set(ROLE_NAMES))

    def test_sync_reports_no_missing_permissions(self):
        for info in sync_roles().values():
            self.assertEqual(info["missing"], [])

    def test_role_permissions(self):
        admin = make_user("a", ROLE_ADMIN)
        sales = make_user("v", ROLE_SALES)
        warehouse = make_user("w", ROLE_WAREHOUSE)
        readonly = make_user("c", ROLE_READONLY)
        self.assertTrue(admin.has_perms(["accounts.add_user", "catalog.import_product", "audit.view_auditlog"]))
        self.assertTrue(sales.has_perm("catalog.view_reference_price"))
        self.assertFalse(sales.has_perm("catalog.change_product"))
        for user in (warehouse, readonly):
            self.assertTrue(user.has_perm("catalog.view_product"))
            self.assertFalse(user.has_perm("catalog.view_reference_price"))
            self.assertFalse(user.has_perm("catalog.add_product"))


class UserManagementTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin1", ROLE_ADMIN)
        self.client.force_login(self.admin)

    def test_non_admin_gets_403(self):
        self.client.force_login(make_user("vend", ROLE_SALES))
        self.assertEqual(self.client.get(reverse("accounts:user_list")).status_code, 403)
        response = self.client.post(reverse("accounts:user_create"), {"username": "x"})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username="x").exists())

    def test_create_user_with_role_and_audit(self):
        sales = Group.objects.get(name=ROLE_SALES)
        response = self.client.post(
            reverse("accounts:user_create"),
            {
                "username": "nuevo",
                "first_name": "Ana",
                "last_name": "Pérez",
                "email": "ana@example.com",
                "groups": [sales.pk],
                "is_active": "on",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertRedirects(response, reverse("accounts:user_list"))
        user = User.objects.get(username="nuevo")
        self.assertTrue(user.check_password(PASSWORD))
        self.assertEqual(user.role_names, [ROLE_SALES])
        entry = AuditLog.objects.get(action="create", object_id=str(user.pk))
        self.assertEqual(entry.changes["groups"]["despues"], [ROLE_SALES])
        self.assertNotIn("password", str(entry.changes))

    def test_cannot_assign_non_role_group(self):
        other = Group.objects.create(name="Secreto")
        user = make_user("otro")
        response = self.client.post(
            reverse("accounts:user_update", args=[user.pk]),
            {
                "username": "otro",
                "first_name": "O",
                "last_name": "T",
                "email": "otro@example.com",
                "groups": [other.pk],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("groups", response.context["form"].errors)

    def test_cannot_change_own_roles_or_deactivate_self(self):
        self.client.post(
            reverse("accounts:user_update", args=[self.admin.pk]),
            {"username": "admin1", "first_name": "A", "last_name": "B", "email": "admin1@example.com", "groups": []},
        )
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role_names, [ROLE_ADMIN])
        self.assertTrue(self.admin.is_active)
        self.client.post(reverse("accounts:user_toggle_active", args=[self.admin.pk]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_toggle_active_other_user(self):
        user = make_user("temporal")
        self.client.post(reverse("accounts:user_toggle_active", args=[user.pk]))
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertTrue(AuditLog.objects.filter(action="deactivate", object_id=str(user.pk)).exists())

    def test_admin_role_cannot_edit_superuser(self):
        root = User.objects.create_superuser("root", "root@example.com", PASSWORD)
        self.assertEqual(self.client.get(reverse("accounts:user_update", args=[root.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("accounts:user_set_password", args=[root.pk])).status_code, 404)

    def test_admin_sets_password(self):
        user = make_user("olvidadizo")
        new = "Otra-Clave-Segura-99"
        self.client.post(
            reverse("accounts:user_set_password", args=[user.pk]), {"new_password1": new, "new_password2": new}
        )
        user.refresh_from_db()
        self.assertTrue(user.check_password(new))
        self.assertTrue(AuditLog.objects.filter(action="password_set").exists())

    def test_weak_password_rejected(self):
        response = self.client.post(
            reverse("accounts:user_create"),
            {
                "username": "debil",
                "first_name": "D",
                "last_name": "B",
                "email": "d@example.com",
                "password1": "12345",
                "password2": "12345",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="debil").exists())


class SelfServiceTests(TestCase):
    def test_password_reset_sends_email(self):
        make_user("ana")
        response = self.client.post(reverse("accounts:password_reset"), {"email": "ana@example.com"})
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/cuentas/recuperar/", mail.outbox[0].body)

    def test_password_change_is_audited(self):
        user = make_user("pepe")
        self.client.force_login(user)
        new = "Nueva-Clave-Segura-77"
        self.client.post(
            reverse("accounts:password_change"),
            {"old_password": PASSWORD, "new_password1": new, "new_password2": new},
        )
        user.refresh_from_db()
        self.assertTrue(user.check_password(new))
        self.assertTrue(AuditLog.objects.filter(action="password_change", user=user).exists())

    def test_profile_cannot_escalate(self):
        user = make_user("lupe")
        self.client.force_login(user)
        self.client.post(
            reverse("accounts:profile"),
            {"first_name": "Lupe", "last_name": "R", "email": "lupe@example.com", "is_superuser": "on", "groups": [1]},
        )
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Lupe")
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.role_names, [])
