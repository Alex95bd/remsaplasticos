from django.contrib.auth.decorators import login_not_required
from django.db import connection
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import TemplateView

from accounts.models import User
from audit.models import AuditLog
from catalog.models import Category, Product

UPCOMING_MODULES = [
    ("bi-people", "Clientes, proveedores y cotizaciones", "Fase 2"),
    ("bi-box-seam", "Inventarios y movimientos", "Fase 3"),
    ("bi-mic", "Listas de precios con dictado por voz", "Fase 4"),
    ("bi-calendar3", "Calendario comercial y tareas", "Fase 5"),
    ("bi-diagram-3", "Integración con Intelisis", "Fase 6"),
]


class DashboardView(TemplateView):
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.has_perm("catalog.view_product"):
            stats = Product.objects.aggregate(
                active=Count("pk", filter=Q(is_active=True)),
                inactive=Count("pk", filter=Q(is_active=False)),
                without_price=Count("pk", filter=Q(is_active=True, reference_price__isnull=True)),
            )
            context["product_stats"] = stats
            context["category_count"] = Category.objects.filter(is_active=True).count()
            context["recent_products"] = Product.objects.select_related("category").order_by("-updated_at")[:6]
        if user.has_perm("accounts.view_user"):
            context["active_users"] = User.objects.filter(is_active=True).count()
        if user.has_perm("audit.view_auditlog"):
            context["activity"] = AuditLog.objects.select_related("user")[:10]
            context["activity_scope"] = "all"
        else:
            context["activity"] = AuditLog.objects.filter(user=user)[:10]
            context["activity_scope"] = "own"
        context["upcoming_modules"] = UPCOMING_MODULES
        return context


@login_not_required
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ok"})
    except Exception:
        return JsonResponse({"status": "error"}, status=503)


def permission_denied(request, exception=None):
    return render(request, "errors/403.html", status=403)


@login_not_required
def page_not_found(request, exception=None):
    return render(request, "errors/404.html", status=404)


@login_not_required
def server_error(request):
    return render(request, "errors/500.html", status=500)
