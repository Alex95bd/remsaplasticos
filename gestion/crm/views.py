from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from audit.models import AuditLog
from audit.services import log_action
from core.mixins import AuditedModelFormMixin, PermissionRequiredMixin

from .forms import PartyForm
from .models import Party


def filter_parties(queryset, params):
    if q := (params.get("q") or "").strip():
        queryset = queryset.filter(
            Q(name__icontains=q)
            | Q(trade_name__icontains=q)
            | Q(rfc__icontains=q)
            | Q(contact_name__icontains=q)
            | Q(email__icontains=q)
            | Q(external_code__icontains=q)
        )
    tipo = params.get("tipo")
    if tipo == Party.PartyType.CUSTOMER:
        queryset = queryset.filter(party_type__in=[Party.PartyType.CUSTOMER, Party.PartyType.BOTH])
    elif tipo == Party.PartyType.SUPPLIER:
        queryset = queryset.filter(party_type__in=[Party.PartyType.SUPPLIER, Party.PartyType.BOTH])
    estado = params.get("estado") or "activos"
    if estado == "activos":
        queryset = queryset.filter(is_active=True)
    elif estado == "inactivos":
        queryset = queryset.filter(is_active=False)
    return queryset


class PartyListView(PermissionRequiredMixin, ListView):
    permission_required = "crm.view_party"
    template_name = "crm/party_list.html"
    context_object_name = "parties"
    paginate_by = 25

    def get_queryset(self):
        return filter_parties(Party.objects.all(), self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["estado"] = self.request.GET.get("estado") or "activos"
        return context


class PartyDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "crm.view_party"
    model = Party
    template_name = "crm/party_detail.html"
    context_object_name = "party"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.has_perm("quotes.view_quote") and self.object.is_customer:
            context["quotes"] = self.object.quotes.select_related("owner").order_by("-created_at")[:15]
        if user.has_perm("agenda.view_event"):
            from agenda.services import visible_events

            context["events"] = visible_events(user).filter(party=self.object).order_by("-start")[:10]
        if user.has_perm("audit.view_auditlog"):
            context["history"] = AuditLog.objects.filter(
                content_type__app_label="crm", content_type__model="party", object_id=str(self.object.pk)
            )[:20]
        return context


class PartyFormMixin(PermissionRequiredMixin, AuditedModelFormMixin):
    model = Party
    form_class = PartyForm
    template_name = "crm/party_form.html"

    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get("tipo") in Party.PartyType.values:
            initial["party_type"] = self.request.GET["tipo"]
        return initial

    def get_success_url(self):
        return reverse("crm:party_detail", args=[self.object.pk])


class PartyCreateView(PartyFormMixin, CreateView):
    permission_required = "crm.add_party"
    success_message = "Registro creado correctamente."


class PartyUpdateView(PartyFormMixin, UpdateView):
    permission_required = "crm.change_party"
    success_message = "Registro actualizado correctamente."


class PartyToggleActiveView(PermissionRequiredMixin, View):
    permission_required = "crm.change_party"
    http_method_names = ["post"]

    def post(self, request, pk):
        party = get_object_or_404(Party, pk=pk)
        party.is_active = not party.is_active
        party.updated_by = request.user
        party.save(update_fields=["is_active", "updated_by", "updated_at"])
        log_action(
            AuditLog.Action.ACTIVATE if party.is_active else AuditLog.Action.DEACTIVATE, request=request, obj=party
        )
        messages.success(request, f"Registro {'activado' if party.is_active else 'desactivado'}.")
        return redirect("crm:party_detail", pk=party.pk)
