from django.conf import settings
from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from audit.models import AuditLog
from audit.services import log_action
from core.mixins import AuditedModelFormMixin, PermissionRequiredMixin

from .forms import CategoryForm, ProductForm, ProductImportForm, UnitOfMeasureForm
from .models import Category, Product, UnitOfMeasure
from .services import ImportFileError, apply_import, export_products, import_template, read_workbook, validate_rows

IMPORT_SESSION_KEY = "catalog_import"
XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def filter_products(queryset, params):
    """Aplica búsqueda y filtros comunes a la lista, la exportación y la API."""
    if q := (params.get("q") or "").strip():
        queryset = queryset.filter(
            Q(name__icontains=q) | Q(sku__icontains=q) | Q(description__icontains=q) | Q(external_code__icontains=q)
        )
    if (category := params.get("categoria") or "").isdigit():
        queryset = queryset.filter(category_id=int(category))
    if (product_type := params.get("tipo")) in Product.ProductType.values:
        queryset = queryset.filter(product_type=product_type)
    estado = params.get("estado") or "activos"
    if estado == "activos":
        queryset = queryset.filter(is_active=True)
    elif estado == "inactivos":
        queryset = queryset.filter(is_active=False)
    return queryset


def xlsx_response(content: bytes, filename: str) -> HttpResponse:
    response = HttpResponse(content, content_type=XLSX_TYPE)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


class ProductListView(PermissionRequiredMixin, ListView):
    permission_required = "catalog.view_product"
    template_name = "catalog/product_list.html"
    context_object_name = "products"
    paginate_by = 25

    def get_queryset(self):
        return filter_products(Product.objects.select_related("category", "unit"), self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.all()
        context["product_types"] = Product.ProductType.choices
        context["estado"] = self.request.GET.get("estado") or "activos"
        context["show_prices"] = self.request.user.has_perm("catalog.view_reference_price")
        return context


class ProductDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "catalog.view_product"
    model = Product
    template_name = "catalog/product_detail.html"
    context_object_name = "product"

    def get_queryset(self):
        return Product.objects.select_related("category", "unit", "created_by", "updated_by")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_prices"] = self.request.user.has_perm("catalog.view_reference_price")
        if self.request.user.has_perm("audit.view_auditlog"):
            context["history"] = AuditLog.objects.filter(
                content_type__app_label="catalog", content_type__model="product", object_id=str(self.object.pk)
            )[:20]
        return context


class ProductFormMixin(PermissionRequiredMixin, AuditedModelFormMixin):
    model = Product
    form_class = ProductForm
    template_name = "catalog/product_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse_lazy("catalog:product_detail", args=[self.object.pk])


class ProductCreateView(ProductFormMixin, CreateView):
    permission_required = "catalog.add_product"
    success_message = "Producto creado correctamente."


class ProductUpdateView(ProductFormMixin, UpdateView):
    permission_required = "catalog.change_product"
    success_message = "Producto actualizado correctamente."


class ProductToggleActiveView(PermissionRequiredMixin, View):
    permission_required = "catalog.change_product"
    http_method_names = ["post"]

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.is_active = not product.is_active
        product.updated_by = request.user
        product.save(update_fields=["is_active", "updated_by", "updated_at"])
        action = AuditLog.Action.ACTIVATE if product.is_active else AuditLog.Action.DEACTIVATE
        log_action(action, request=request, obj=product)
        messages.success(request, f"Producto {'activado' if product.is_active else 'desactivado'}: {product.sku}.")
        return redirect("catalog:product_detail", pk=product.pk)


class ProductExportView(PermissionRequiredMixin, View):
    permission_required = "catalog.export_product"

    def get(self, request):
        queryset = filter_products(Product.objects.all(), request.GET)
        include_prices = request.user.has_perm("catalog.view_reference_price")
        content = export_products(queryset, include_prices=include_prices)
        log_action(
            AuditLog.Action.EXPORT,
            request=request,
            message=f"Exportación de {queryset.count()} productos a Excel"
            + ("" if include_prices else " (sin precios)"),
        )
        return xlsx_response(content, f"productos-remsa-{timezone.localdate():%Y%m%d}.xlsx")


class ProductImportTemplateView(PermissionRequiredMixin, View):
    permission_required = "catalog.import_product"

    def get(self, request):
        include_prices = request.user.has_perm("catalog.view_reference_price")
        return xlsx_response(import_template(include_prices=include_prices), "plantilla-productos-remsa.xlsx")


class ProductImportView(PermissionRequiredMixin, View):
    """Paso 1: carga y lectura del archivo. Las filas leídas se guardan en la sesión."""

    permission_required = "catalog.import_product"
    template_name = "catalog/product_import.html"

    def get(self, request):
        return render(request, self.template_name, {"form": ProductImportForm()})

    def post(self, request):
        form = ProductImportForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.cleaned_data["file"]
            try:
                rows, ignored = read_workbook(uploaded, settings.CATALOG_IMPORT_MAX_ROWS)
            except ImportFileError as exc:
                form.add_error("file", str(exc))
            else:
                request.session[IMPORT_SESSION_KEY] = {
                    "filename": uploaded.name[:120],
                    "update_existing": form.cleaned_data["update_existing"],
                    "ignored_columns": ignored,
                    "rows": rows,
                }
                return redirect("catalog:product_import_preview")
        return render(request, self.template_name, {"form": form})


class ProductImportPreviewView(PermissionRequiredMixin, View):
    """Paso 2: vista previa con validación y confirmación explícita."""

    permission_required = "catalog.import_product"
    template_name = "catalog/product_import_preview.html"

    def get_pending(self, request):
        return request.session.get(IMPORT_SESSION_KEY)

    def get(self, request):
        pending = self.get_pending(request)
        if not pending:
            messages.info(request, "No hay una importación pendiente. Carga un archivo.")
            return redirect("catalog:product_import")
        include_prices = request.user.has_perm("catalog.view_reference_price")
        preview = validate_rows(
            pending["rows"], update_existing=pending["update_existing"], include_prices=include_prices
        )
        return render(request, self.template_name, {"pending": pending, "preview": preview})

    def post(self, request):
        pending = self.get_pending(request)
        if not pending:
            return redirect("catalog:product_import")
        if "cancelar" in request.POST:
            request.session.pop(IMPORT_SESSION_KEY, None)
            messages.info(request, "Importación cancelada. No se guardó ningún cambio.")
            return redirect("catalog:product_list")
        include_prices = request.user.has_perm("catalog.view_reference_price")
        try:
            preview, created, updated = apply_import(
                pending["rows"],
                update_existing=pending["update_existing"],
                include_prices=include_prices,
                request=request,
                filename=pending["filename"],
            )
        except ImportFileError as exc:
            messages.error(request, str(exc))
            return redirect("catalog:product_import_preview")
        request.session.pop(IMPORT_SESSION_KEY, None)
        messages.success(
            request,
            f"Importación terminada: {len(created)} productos nuevos, {len(updated)} actualizados"
            + (f", {preview.errors} filas omitidas por errores." if preview.errors else "."),
        )
        return redirect("catalog:product_list")


class CategoryListView(PermissionRequiredMixin, ListView):
    permission_required = "catalog.view_category"
    template_name = "catalog/category_list.html"
    context_object_name = "categories"
    paginate_by = 50

    def get_queryset(self):
        queryset = Category.objects.annotate(product_count=Count("products"))
        if q := self.request.GET.get("q", "").strip():
            queryset = queryset.filter(name__icontains=q)
        return queryset


class CategoryFormMixin(PermissionRequiredMixin, AuditedModelFormMixin):
    model = Category
    form_class = CategoryForm
    template_name = "catalog/simple_form.html"
    success_url = reverse_lazy("catalog:category_list")
    extra_context = {"section_title": "Categoría", "back_url": reverse_lazy("catalog:category_list")}


class CategoryCreateView(CategoryFormMixin, CreateView):
    permission_required = "catalog.add_category"
    success_message = "Categoría creada correctamente."


class CategoryUpdateView(CategoryFormMixin, UpdateView):
    permission_required = "catalog.change_category"
    success_message = "Categoría actualizada correctamente."


class UnitListView(PermissionRequiredMixin, ListView):
    permission_required = "catalog.view_unitofmeasure"
    template_name = "catalog/unit_list.html"
    context_object_name = "units"
    paginate_by = 50

    def get_queryset(self):
        return UnitOfMeasure.objects.annotate(product_count=Count("products"))


class UnitFormMixin(PermissionRequiredMixin, AuditedModelFormMixin):
    model = UnitOfMeasure
    form_class = UnitOfMeasureForm
    template_name = "catalog/simple_form.html"
    success_url = reverse_lazy("catalog:unit_list")
    extra_context = {"section_title": "Unidad de medida", "back_url": reverse_lazy("catalog:unit_list")}


class UnitCreateView(UnitFormMixin, CreateView):
    permission_required = "catalog.add_unitofmeasure"
    success_message = "Unidad creada correctamente."


class UnitUpdateView(UnitFormMixin, UpdateView):
    permission_required = "catalog.change_unitofmeasure"
    success_message = "Unidad actualizada correctamente."
