from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from accounts.roles import ROLE_ADMIN, ROLE_SALES, ROLE_WAREHOUSE, sync_roles
from audit.models import AuditLog
from catalog.models import UnitOfMeasure
from core.tests.factories import PASSWORD, make_product, make_user
from inventory import services
from inventory.models import Stock, StockMovement, Warehouse


class InventoryServiceTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin", ROLE_ADMIN)
        self.clerk = make_user("almacen", ROLE_WAREHOUSE)
        self.product = make_product("INV-1")
        self.main = Warehouse.objects.create(code="mat", name="Matriz")
        self.branch = Warehouse.objects.create(code="SUC", name="Sucursal")

    def entry(self, qty="100", **kw):
        return services.register_entry(
            product=self.product, warehouse=self.main, quantity=Decimal(qty), user=self.clerk, reason="Compra", **kw
        )

    def stock(self, warehouse=None):
        return Stock.objects.get(product=self.product, warehouse=warehouse or self.main).quantity

    def test_entry_and_exit_update_balance_and_history(self):
        self.assertEqual(self.main.code, "MAT")
        self.entry("100")
        m = services.register_exit(
            product=self.product, warehouse=self.main, quantity=Decimal("30"), user=self.clerk, reason="Venta"
        )
        self.assertEqual(self.stock(), Decimal("70"))
        self.assertEqual(m.balance_after, Decimal("70"))
        self.assertEqual(m.quantity, Decimal("-30"))
        self.assertEqual(AuditLog.objects.filter(action="movement").count(), 2)

    def test_negative_stock_blocked(self):
        self.entry("5")
        with self.assertRaises(ValidationError):
            services.register_exit(
                product=self.product, warehouse=self.main, quantity=Decimal("6"), user=self.clerk, reason="Venta"
            )
        self.assertEqual(self.stock(), Decimal("5"))
        self.assertEqual(StockMovement.objects.count(), 1)

    @override_settings(INVENTORY_ALLOW_NEGATIVE=True)
    def test_negative_allowed_by_policy(self):
        services.register_exit(
            product=self.product, warehouse=self.main, quantity=Decimal("2"), user=self.clerk, reason="Venta"
        )
        self.assertEqual(self.stock(), Decimal("-2"))

    def test_invalid_quantity(self):
        for qty in ["0", "-1"]:
            with self.assertRaises(ValidationError):
                self.entry(qty)

    def test_transfer_is_atomic_pair(self):
        self.entry("10")
        out, inc = services.transfer(
            product=self.product,
            source=self.main,
            target=self.branch,
            quantity=Decimal("4"),
            user=self.clerk,
            reason="Reabasto",
        )
        self.assertEqual(out.transfer_id, inc.transfer_id)
        self.assertEqual((self.stock(), self.stock(self.branch)), (Decimal("6"), Decimal("4")))
        with self.assertRaises(ValidationError):
            services.transfer(
                product=self.product,
                source=self.main,
                target=self.branch,
                quantity=Decimal("7"),
                user=self.clerk,
                reason="Excede",
            )
        self.assertEqual((self.stock(), self.stock(self.branch)), (Decimal("6"), Decimal("4")))

    def test_adjustment_requires_authorization(self):
        self.entry("10")
        with self.assertRaises(PermissionDenied):
            services.register_adjustment(
                product=self.product, warehouse=self.main, counted=Decimal("8"), user=self.clerk, reason="Conteo"
            )
        m = services.register_adjustment(
            product=self.product, warehouse=self.main, counted=Decimal("8"), user=self.admin, reason="Conteo"
        )
        self.assertEqual(m.quantity, Decimal("-2"))
        self.assertEqual(m.authorized_by, self.admin)

    def test_movements_are_immutable_and_reversible(self):
        m = self.entry("10")
        with self.assertRaises(ValueError):
            m.save()
        with self.assertRaises(ValueError):
            m.delete()
        r = services.reverse_movement(movement=m, user=self.admin, reason="Captura duplicada")
        self.assertEqual(r.reverses, m)
        self.assertEqual(self.stock(), Decimal("0"))
        with self.assertRaises(ValidationError):
            services.reverse_movement(movement=m, user=self.admin, reason="Otra vez")

    def test_low_stock(self):
        self.entry("3")
        Stock.objects.filter(product=self.product).update(min_quantity=5)
        self.assertEqual(services.low_stock_queryset().count(), 1)

    def test_inactive_product_rejected(self):
        self.product.is_active = False
        self.product.save()
        with self.assertRaises(ValidationError):
            self.entry("1")


class InventoryConcurrencyTests(TransactionTestCase):
    """Verifica que las salidas simultáneas no dejen existencias negativas (bloqueo de fila)."""

    def test_parallel_exits(self):
        import threading

        from django.db import connection

        sync_roles()
        if connection.vendor == "sqlite":
            self.skipTest("SQLite serializa escrituras; la prueba concurrente aplica a PostgreSQL.")
        user = make_user("almacen", ROLE_WAREHOUSE)
        UnitOfMeasure.objects.get_or_create(code="PZA", defaults={"name": "Pieza"})
        product = make_product("CONC-1")
        wh = Warehouse.objects.create(code="C1", name="Concurrencia")
        services.register_entry(product=product, warehouse=wh, quantity=Decimal("10"), user=user, reason="Inicial")
        errors = []

        def worker():
            try:
                services.register_exit(product=product, warehouse=wh, quantity=Decimal("3"), user=user, reason="x")
            except ValidationError:
                errors.append(1)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(Stock.objects.get(product=product).quantity, Decimal("1"))
        self.assertEqual(len(errors), 2)


class InventoryViewTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin", ROLE_ADMIN)
        self.clerk = make_user("almacen", ROLE_WAREHOUSE)
        self.sales = make_user("ventas", ROLE_SALES)
        self.product = make_product("INV-2")
        self.wh = Warehouse.objects.create(code="MAT", name="Matriz")
        self.wh2 = Warehouse.objects.create(code="SUC", name="Sucursal")

    def test_clerk_registers_entry_exit_transfer(self):
        self.client.login(username="almacen", password=PASSWORD)
        r = self.client.post(
            reverse("inventory:movement_create"),
            {
                "kind": "entrada",
                "product": self.product.pk,
                "warehouse": self.wh.pk,
                "quantity": "50",
                "reason": "Compra",
            },
        )
        self.assertEqual(r.status_code, 302)
        r = self.client.post(
            reverse("inventory:movement_create"),
            {
                "kind": "salida",
                "product": self.product.pk,
                "warehouse": self.wh.pk,
                "quantity": "80",
                "reason": "Venta",
            },
        )
        self.assertContains(r, "Existencia insuficiente")
        r = self.client.post(
            reverse("inventory:transfer_create"),
            {
                "product": self.product.pk,
                "source": self.wh.pk,
                "target": self.wh2.pk,
                "quantity": "20",
                "reason": "Reabasto",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Stock.objects.get(warehouse=self.wh2).quantity, Decimal("20"))
        self.assertEqual(self.client.get(reverse("inventory:stock_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("inventory:movement_list"), {"tipo": "entrada"}).status_code, 200)
        self.assertEqual(self.client.get(reverse("inventory:stock_export")).status_code, 200)

    def test_clerk_cannot_adjust_or_create_warehouse(self):
        self.client.login(username="almacen", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("inventory:adjustment_create")).status_code, 403)
        self.assertEqual(self.client.get(reverse("inventory:warehouse_create")).status_code, 403)

    def test_sales_read_only(self):
        self.client.login(username="ventas", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("inventory:stock_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("inventory:movement_create")).status_code, 403)
        self.assertEqual(self.client.get(reverse("inventory:movement_list")).status_code, 403)

    def test_admin_adjust_and_reverse(self):
        self.client.login(username="admin", password=PASSWORD)
        self.client.post(
            reverse("inventory:movement_create"),
            {
                "kind": "entrada",
                "product": self.product.pk,
                "warehouse": self.wh.pk,
                "quantity": "10",
                "reason": "Compra",
            },
        )
        r = self.client.post(
            reverse("inventory:adjustment_create"),
            {
                "product": self.product.pk,
                "warehouse": self.wh.pk,
                "counted": "7",
                "reason": "Conteo mensual",
            },
        )
        self.assertEqual(r.status_code, 302)
        adj = StockMovement.objects.get(kind="ajuste")
        self.client.post(reverse("inventory:movement_reverse", args=[adj.pk]), {"reason": "Error de conteo"})
        self.assertEqual(Stock.objects.get(warehouse=self.wh).quantity, Decimal("10"))
        self.assertEqual(self.client.get(reverse("inventory:movement_detail", args=[adj.pk])).status_code, 200)
        r = self.client.post(reverse("inventory:warehouse_create"), {"code": "nvo", "name": "Nuevo", "is_active": "on"})
        self.assertEqual(r.status_code, 302)
        w = Warehouse.objects.get(code="NVO")
        self.client.post(reverse("inventory:location_create", args=[w.pk]), {"code": "a-01", "is_active": "on"})
        self.assertEqual(w.locations.get().code, "A-01")
