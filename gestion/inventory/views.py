from datetime import date

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from accounts.models import User
from audit.models import AuditLog
from audit.services import log_action
from catalog.views import xlsx_response
from core.mixins import AuditedModelFormMixin, PermissionRequiredMixin

from . import services
from .exports import export_stock
from .forms import (
    AdjustmentForm,
    LocationForm,
    MovementForm,
    ReverseForm,
    StockSettingsForm,
    TransferForm,
    WarehouseForm,
)
from .models import Location, Stock, StockMovement, Warehouse


def _valid_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def filter_stock(queryset, params):
    if q := (params.get("q") or "").strip():
        queryset = queryset.filter(Q(product__sku__icontains=q) | Q(product__name__icontains=q))
    if (wh := params.get("almacen") or "").isdigit():
        queryset = queryset.filter(warehouse_id=int(wh))
    if params.get("bajo"):
        queryset = queryset.filter(pk__in=services.low_stock_queryset().values("pk"))
    return queryset


class StockListView(PermissionRequiredMixin, ListView):
    permission_required = "inventory.view_stock"
    template_name = "inventory/stock_list.html"
    context_object_name = "stocks"
    paginate_by = 50

    def get_queryset(self):
        qs = Stock.objects.select_related("product__unit", "warehouse", "location").filter(product__is_active=True)
        return filter_stock(qs, self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["warehouses"] = Warehouse.objects.all()
        context["low_count"] = services.low_stock_queryset().count()
        return context


class StockExportView(PermissionRequiredMixin, View):
    permission_required = "inventory.export_stock"

    def get(self, request):
        qs = filter_stock(Stock.objects.select_related("product__unit", "warehouse", "location"), request.GET)
        log_action(AuditLog.Action.EXPORT, request=request, message=f"Exportación de {qs.count()} existencias")
        return xlsx_response(export_stock(qs), f"existencias-remsa-{timezone.localdate():%Y%m%d}.xlsx")


class StockUpdateView(PermissionRequiredMixin, AuditedModelFormMixin, UpdateView):
    permission_required = "inventory.change_stock"
    model = Stock
    form_class = StockSettingsForm
    template_name = "inventory/form.html"
    success_message = "Parámetros de existencia actualizados."

    def get_success_url(self):
        return reverse("inventory:stock_list") + f"?q={self.object.product.sku}"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Stock mínimo · {self.object.product.sku} en {self.object.warehouse.code}"
        return context


class MovementListView(PermissionRequiredMixin, ListView):
    permission_required = "inventory.view_stockmovement"
    template_name = "inventory/movement_list.html"
    context_object_name = "movements"
    paginate_by = 50

    def get_queryset(self):
        qs = StockMovement.objects.select_related("product", "warehouse", "user")
        params = self.request.GET
        if q := (params.get("q") or "").strip():
            qs = qs.filter(
                Q(product__sku__icontains=q)
                | Q(product__name__icontains=q)
                | Q(reference__icontains=q)
                | Q(reason__icontains=q)
            )
        if (wh := params.get("almacen") or "").isdigit():
            qs = qs.filter(warehouse_id=int(wh))
        if params.get("tipo") in StockMovement.Kind.values:
            qs = qs.filter(kind=params["tipo"])
        if (uid := params.get("usuario") or "").isdigit():
            qs = qs.filter(user_id=int(uid))
        if d := _valid_date(params.get("desde")):
            qs = qs.filter(created_at__date__gte=d)
        if d := _valid_date(params.get("hasta")):
            qs = qs.filter(created_at__date__lte=d)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["warehouses"] = Warehouse.objects.all()
        context["kinds"] = StockMovement.Kind.choices
        context["users"] = User.objects.filter(stockmovement__isnull=False).distinct()
        return context


class MovementDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "inventory.view_stockmovement"
    model = StockMovement
    template_name = "inventory/movement_detail.html"
    context_object_name = "movement"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        m = self.object
        context["reversal"] = StockMovement.objects.filter(reverses=m).first()
        context["siblings"] = (
            StockMovement.objects.filter(transfer_id=m.transfer_id).exclude(pk=m.pk) if m.transfer_id else []
        )
        context["can_reverse"] = (
            self.request.user.has_perm("inventory.authorize_adjustment")
            and not m.transfer_id
            and m.kind != StockMovement.Kind.REVERSAL
            and context["reversal"] is None
        )
        context["reverse_form"] = ReverseForm()
        return context


class ServiceFormView(PermissionRequiredMixin, View):
    """Formulario que delega en un servicio transaccional y muestra sus errores de negocio."""

    form_class = None
    title = ""
    icon = "bi-box-seam"

    def render_form(self, form):
        return render(self.request, "inventory/form.html", {"form": form, "title": self.title, "icon": self.icon})

    def get(self, request):
        initial = {k: v for k, v in request.GET.items() if k in ("product", "warehouse", "source", "kind")}
        return self.render_form(self.form_class(initial=initial))

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            try:
                result = self.perform(form.cleaned_data)
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(request, self.success_message(result))
                return redirect(self.success_url(result))
        return self.render_form(form)

    def success_url(self, movement):
        return reverse("inventory:movement_detail", args=[movement.pk])


class MovementCreateView(ServiceFormView):
    permission_required = "inventory.add_stockmovement"
    form_class = MovementForm
    title = "Entrada / salida de inventario"

    def perform(self, data):
        fn = services.register_entry if data["kind"] == "entrada" else services.register_exit
        return fn(
            product=data["product"],
            warehouse=data["warehouse"],
            quantity=data["quantity"],
            user=self.request.user,
            reason=data["reason"],
            reference=data["reference"],
            notes=data["notes"],
            location=data.get("location"),
            request=self.request,
        )

    def success_message(self, m):
        return f"{m.get_kind_display()} registrada. Existencia de {m.product.sku} en {m.warehouse.code}: {m.balance_after.normalize():f}."  # noqa: E501


class AdjustmentCreateView(ServiceFormView):
    permission_required = "inventory.authorize_adjustment"
    form_class = AdjustmentForm
    title = "Ajuste autorizado por conteo físico"
    icon = "bi-clipboard-check"

    def perform(self, data):
        return services.register_adjustment(
            product=data["product"],
            warehouse=data["warehouse"],
            counted=data["counted"],
            user=self.request.user,
            reason=data["reason"],
            reference=data["reference"],
            notes=data["notes"],
            request=self.request,
        )

    def success_message(self, m):
        return f"Ajuste registrado ({m.quantity:+f}). Nueva existencia: {m.balance_after.normalize():f}."


class TransferCreateView(ServiceFormView):
    permission_required = "inventory.transfer_stock"
    form_class = TransferForm
    title = "Transferencia entre almacenes"
    icon = "bi-arrow-left-right"

    def perform(self, data):
        return services.transfer(
            product=data["product"],
            source=data["source"],
            target=data["target"],
            quantity=data["quantity"],
            user=self.request.user,
            reason=data["reason"],
            reference=data["reference"],
            notes=data["notes"],
            request=self.request,
        )

    def success_message(self, result):
        return "Transferencia registrada."

    def success_url(self, result):
        return reverse("inventory:movement_detail", args=[result[0].pk])


class MovementReverseView(PermissionRequiredMixin, View):
    permission_required = "inventory.authorize_adjustment"
    http_method_names = ["post"]

    def post(self, request, pk):
        movement = get_object_or_404(StockMovement, pk=pk)
        form = ReverseForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Indica el motivo de la cancelación.")
            return redirect("inventory:movement_detail", pk=pk)
        try:
            reversal = services.reverse_movement(
                movement=movement, user=request.user, reason=form.cleaned_data["reason"], request=request
            )
        except (ValidationError, PermissionDenied) as exc:
            messages.error(request, " ".join(getattr(exc, "messages", [str(exc)])))
            return redirect("inventory:movement_detail", pk=pk)
        messages.success(request, "Movimiento cancelado con un movimiento inverso.")
        return redirect("inventory:movement_detail", pk=reversal.pk)


class WarehouseListView(PermissionRequiredMixin, ListView):
    permission_required = "inventory.view_warehouse"
    model = Warehouse
    template_name = "inventory/warehouse_list.html"
    context_object_name = "warehouses"


class WarehouseDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "inventory.view_warehouse"
    model = Warehouse
    template_name = "inventory/warehouse_detail.html"
    context_object_name = "warehouse"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["locations"] = self.object.locations.all()
        context["location_form"] = LocationForm()
        return context


class WarehouseFormMixin(PermissionRequiredMixin, AuditedModelFormMixin):
    model = Warehouse
    form_class = WarehouseForm
    template_name = "inventory/form.html"

    def get_success_url(self):
        return reverse("inventory:warehouse_detail", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Editar almacén {self.object}" if self.object else "Nuevo almacén"
        return context


class WarehouseCreateView(WarehouseFormMixin, CreateView):
    permission_required = "inventory.add_warehouse"
    success_message = "Almacén creado."


class WarehouseUpdateView(WarehouseFormMixin, UpdateView):
    permission_required = "inventory.change_warehouse"
    success_message = "Almacén actualizado."


class LocationCreateView(PermissionRequiredMixin, View):
    permission_required = "inventory.add_location"
    http_method_names = ["post"]

    def post(self, request, pk):
        warehouse = get_object_or_404(Warehouse, pk=pk)
        form = LocationForm(request.POST, instance=Location(warehouse=warehouse))
        if form.is_valid():
            if Location.objects.filter(warehouse=warehouse, code=form.cleaned_data["code"].strip().upper()).exists():
                messages.error(request, "Esa ubicación ya existe en el almacén.")
            else:
                location = form.save()
                log_action(AuditLog.Action.CREATE, request=request, obj=location)
                messages.success(request, f"Ubicación {location.code} agregada.")
        else:
            messages.error(request, "Revisa los datos de la ubicación.")
        return redirect("inventory:warehouse_detail", pk=pk)
