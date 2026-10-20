from django.test import TestCase
from django.urls import reverse

from accounts.roles import ROLE_ADMIN, ROLE_SALES
from audit.models import AuditLog
from audit.services import log_action
from core.tests.factories import make_user


class AuditLogTests(TestCase):
    def test_entries_are_immutable(self):
        entry = log_action(AuditLog.Action.EXPORT, message="prueba")
        entry.message = "alterado"
        with self.assertRaises(ValueError):
            entry.save()
        with self.assertRaises(ValueError):
            entry.delete()

    def test_list_requires_permission_and_filters(self):
        log_action(AuditLog.Action.EXPORT, message="exportación A")
        log_action(AuditLog.Action.IMPORT, message="importación B")
        self.client.force_login(make_user("vend", ROLE_SALES))
        self.assertEqual(self.client.get(reverse("audit:list")).status_code, 403)
        self.client.force_login(make_user("adm", ROLE_ADMIN))
        response = self.client.get(reverse("audit:list"), {"accion": "import"})
        self.assertEqual([e.message for e in response.context["entries"]], ["importación B"])
