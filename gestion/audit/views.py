from django.db.models import Q
from django.utils.dateparse import parse_date
from django.views.generic import ListView

from core.mixins import PermissionRequiredMixin

from .models import AuditLog


class AuditLogListView(PermissionRequiredMixin, ListView):
    permission_required = "audit.view_auditlog"
    model = AuditLog
    paginate_by = 50
    template_name = "audit/auditlog_list.html"
    context_object_name = "entries"

    def get_queryset(self):
        qs = AuditLog.objects.select_related("content_type")
        params = self.request.GET
        if q := params.get("q", "").strip():
            qs = qs.filter(Q(username__icontains=q) | Q(object_repr__icontains=q) | Q(message__icontains=q))
        if (action := params.get("accion")) in AuditLog.Action.values:
            qs = qs.filter(action=action)
        if desde := parse_date(params.get("desde", "") or ""):
            qs = qs.filter(created_at__date__gte=desde)
        if hasta := parse_date(params.get("hasta", "") or ""):
            qs = qs.filter(created_at__date__lte=hasta)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["actions"] = AuditLog.Action.choices
        return context
