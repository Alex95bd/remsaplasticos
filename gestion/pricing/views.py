from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from audit.models import AuditLog
from audit.services import log_action
from catalog.views import xlsx_response
from core.mixins import AuditedModelFormMixin, PermissionRequiredMixin

from . import services
from .exports import price_list_pdf, price_list_xlsx
from .forms import DictationForm, PriceItemForm, PriceListForm, PriceReviewForm
from .models import PriceChange, PriceList, PriceListItem
from .parser import parse_dictation


class PriceListListView(PermissionRequiredMixin, ListView):
    permission_required = "pricing.view_pricelist"
    template_name = "pricing/pricelist_list.html"
    context_object_name = "price_lists"

    def get_queryset(self):
        return PriceList.objects.select_related("customer").order_by("-is_active", "code")


class PriceListDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "pricing.view_pricelist"
    model = PriceList
    template_name = "pricing/pricelist_detail.html"
    context_object_name = "price_list"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        items = self.object.items.select_related("product__unit", "updated_by")
        if q := (self.request.GET.get("q") or "").strip():
            items = items.filter(Q(product__sku__icontains=q) | Q(product__name__icontains=q))
        context["items"] = items
        context["item_form"] = PriceItemForm()
        context["changes"] = self.object.changes.select_related("product", "user")[:30]
        return context


class PriceListFormMixin(PermissionRequiredMixin, AuditedModelFormMixin):
    model = PriceList
    form_class = PriceListForm
    template_name = "inventory/form.html"

    def get_success_url(self):
        return reverse("pricing:pricelist_detail", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Editar {self.object}" if self.object else "Nueva lista de precios"
        context["icon"] = "bi-tags"
        return context


class PriceListCreateView(PriceListFormMixin, CreateView):
    permission_required = "pricing.add_pricelist"
    success_message = "Lista de precios creada."


class PriceListUpdateView(PriceListFormMixin, UpdateView):
    permission_required = "pricing.change_pricelist"
    success_message = "Lista de precios actualizada."


class PriceItemSetView(PermissionRequiredMixin, View):
    permission_required = ["pricing.add_pricelistitem", "pricing.change_pricelistitem"]
    http_method_names = ["post"]

    def post(self, request, pk):
        price_list = get_object_or_404(PriceList, pk=pk)
        form = PriceItemForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            _, change = services.set_price(
                price_list=price_list,
                product=d["product"],
                min_quantity=d["min_quantity"],
                unit_price=d["unit_price"],
                user=request.user,
                request=request,
            )
            messages.success(request, "Precio guardado." if change else "El precio no cambió.")
        else:
            messages.error(request, "Revisa producto, cantidad mínima y precio.")
        return redirect("pricing:pricelist_detail", pk=pk)


class PriceItemDeleteView(PermissionRequiredMixin, View):
    permission_required = "pricing.delete_pricelistitem"
    http_method_names = ["post"]

    def post(self, request, pk, item_pk):
        item = get_object_or_404(PriceListItem, pk=item_pk, price_list_id=pk)
        services.remove_price(item=item, user=request.user, request=request)
        messages.success(request, "Precio eliminado de la lista.")
        return redirect("pricing:pricelist_detail", pk=pk)


class PriceListExportView(PermissionRequiredMixin, View):
    permission_required = "pricing.export_pricelist"

    def get(self, request, pk, fmt):
        price_list = get_object_or_404(PriceList.objects.select_related("customer"), pk=pk)
        items = price_list.items.select_related("product__unit")
        stamp = f"{price_list.code}-{timezone.localdate():%Y%m%d}"
        log_action(AuditLog.Action.EXPORT, request=request, obj=price_list, message=f"Exportación {fmt.upper()}")
        if fmt == "pdf":
            response = HttpResponse(price_list_pdf(price_list, items), content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="lista-{stamp}.pdf"'
            return response
        return xlsx_response(price_list_xlsx(price_list, items), f"lista-{stamp}.xlsx")


class DictationView(PermissionRequiredMixin, View):
    """Captura por voz o texto en tres pasos: interpretar → revisar/corregir → vista previa y confirmación.

    Nada se guarda hasta el paso de confirmación, que vuelve a validar todos los datos en el servidor.
    """

    permission_required = ["pricing.add_pricelistitem", "pricing.change_pricelistitem"]
    template_name = "pricing/dictation.html"

    def render_step(self, step, **context):
        context.setdefault("dictation_form", DictationForm())
        return render(self.request, self.template_name, {"step": step, **context})

    def get(self, request):
        return self.render_step("capture")

    def post(self, request):
        step = request.POST.get("step")
        if step == "interpret":
            return self.interpret()
        if step == "review":
            return self.render_step("review", form=PriceReviewForm(self.request.POST), candidates=[], parsed=None)
        if step in ("preview", "confirm"):
            form = PriceReviewForm(request.POST)
            if not form.is_valid():
                return self.render_step("review", form=form, candidates=[], parsed=None)
            return self.preview(form) if step == "preview" else self.confirm(form)
        return redirect("pricing:dictation")

    def interpret(self):
        dictation = DictationForm(self.request.POST)
        if not dictation.is_valid():
            return self.render_step("capture", dictation_form=dictation)
        transcript = dictation.cleaned_data["transcript"]
        parsed = parse_dictation(transcript, today=timezone.localdate())
        candidates, exact = services.find_products(parsed.sku, parsed.product_text)
        price_list = services.find_price_list(parsed.price_list)
        initial = {
            "transcript": transcript,
            "source": dictation.cleaned_data["source"],
            "product": candidates[0].pk if exact else None,
            "price_list": price_list.pk if price_list else None,
            "min_quantity": parsed.min_quantity or 1,
            "unit_price": parsed.unit_price,
            "currency": parsed.currency,
        }
        warnings = list(parsed.warnings)
        if not exact:
            warnings.append("El producto no coincide exactamente con un SKU: elige el correcto de la lista.")
        if parsed.price_list and not price_list:
            warnings.append(f"No se encontró la lista «{parsed.price_list}»: elige una.")
        if parsed.valid_until:
            warnings.append(
                f"Se dictó una vigencia ({parsed.valid_until:%d/%m/%Y}); la vigencia se edita en la lista, no aquí."
            )
        return self.render_step(
            "review", form=PriceReviewForm(initial=initial), parsed=parsed, candidates=candidates, warnings=warnings
        )

    def preview(self, form):
        d = form.cleaned_data
        current = services.current_item(d["price_list"], d["product"], d["min_quantity"])
        reference = d["product"].reference_price
        warnings = []
        if current and current.unit_price:
            delta = (d["unit_price"] - current.unit_price) / current.unit_price * 100
            if abs(delta) >= 30:
                warnings.append(
                    f"El precio cambia {delta:+.1f}% respecto al actual. Verifica que el dictado sea correcto."
                )
        if reference and d["unit_price"] < reference / 2:
            warnings.append("El precio es menor a la mitad del precio de referencia del catálogo.")
        return self.render_step("preview", form=form, data=d, current=current, warnings=warnings)

    def confirm(self, form):
        d = form.cleaned_data
        source = PriceChange.Source.VOICE if d["source"] == "voz" else PriceChange.Source.TEXT
        _, change = services.set_price(
            price_list=d["price_list"],
            product=d["product"],
            min_quantity=d["min_quantity"],
            unit_price=d["unit_price"],
            user=self.request.user,
            source=source,
            transcript=d.get("transcript", ""),
            request=self.request,
        )
        messages.success(
            self.request, "Precio actualizado." if change else "El precio ya tenía ese valor; no hubo cambios."
        )
        return redirect("pricing:pricelist_detail", pk=d["price_list"].pk)
