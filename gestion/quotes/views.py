from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from accounts.models import User
from audit.models import AuditLog
from audit.services import log_action
from core.mixins import PermissionRequiredMixin
from crm.models import Party

from .forms import FollowUpForm, QuoteForm, QuoteItemFormSet, StatusForm
from .models import Quote
from .pdf import quote_pdf
from .services import can_edit, change_status, default_validity, duplicate_quote, max_discount, save_quote


def filter_quotes(queryset, params):
    if q := (params.get("q") or "").strip():
        queryset = queryset.filter(
            Q(folio__icontains=q) | Q(customer__name__icontains=q) | Q(customer__rfc__icontains=q)
        )
    if (status := params.get("estado")) in Quote.Status.values:
        queryset = queryset.filter(status=status)
    elif status == "abiertas":
        queryset = queryset.filter(status__in=Quote.OPEN_STATUSES)
    if (owner := params.get("responsable") or "").isdigit():
        queryset = queryset.filter(owner_id=int(owner))
    if (customer := params.get("cliente") or "").isdigit():
        queryset = queryset.filter(customer_id=int(customer))
    if desde := params.get("desde"):
        queryset = queryset.filter(issue_date__gte=desde) if _is_date(desde) else queryset
    if hasta := params.get("hasta"):
        queryset = queryset.filter(issue_date__lte=hasta) if _is_date(hasta) else queryset
    return queryset


def _is_date(value):
    from datetime import date

    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


class QuoteListView(PermissionRequiredMixin, ListView):
    permission_required = "quotes.view_quote"
    template_name = "quotes/quote_list.html"
    context_object_name = "quotes"
    paginate_by = 25

    def get_queryset(self):
        return filter_quotes(Quote.objects.select_related("customer", "owner"), self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = Quote.Status.choices
        context["owners"] = User.objects.filter(quotes__isnull=False).distinct().order_by("username")
        return context


class QuoteDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "quotes.view_quote"
    model = Quote
    template_name = "quotes/quote_detail.html"
    context_object_name = "quote"

    def get_queryset(self):
        return Quote.objects.select_related("customer", "owner", "duplicated_from")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["items"] = self.object.items.all()
        context["follow_ups"] = self.object.follow_ups.select_related("user")
        context["can_edit"] = can_edit(user, self.object)
        context["can_manage"] = user.has_perm("quotes.change_quote") and (
            self.object.owner_id == user.pk or user.has_perm("quotes.change_any_quote")
        )
        context["transitions"] = [(s, Quote.Status(s).label) for s in self.object.allowed_transitions]
        context["follow_up_form"] = FollowUpForm()
        if user.has_perm("audit.view_auditlog"):
            context["history"] = AuditLog.objects.filter(
                content_type__app_label="quotes", content_type__model="quote", object_id=str(self.object.pk)
            )[:30]
        return context


class QuoteEditView(PermissionRequiredMixin, View):
    """Alta y edición con partidas. Precios y totales se validan y calculan en el servidor."""

    template_name = "quotes/quote_form.html"

    def get_permission_required(self):
        return ["quotes.change_quote"] if "pk" in self.kwargs else ["quotes.add_quote"]

    def get_quote(self):
        if "pk" not in self.kwargs:
            return Quote(valid_until=default_validity())
        quote = get_object_or_404(Quote, pk=self.kwargs["pk"])
        if not can_edit(self.request.user, quote):
            raise PermissionDenied("Solo se pueden editar cotizaciones en borrador propias o con autorización.")
        return quote

    def render_form(self, form, formset, quote):
        from catalog.models import Product

        products = Product.objects.filter(is_active=True).select_related("unit")
        return render(
            self.request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "quote": quote,
                "products": products,
                "max_discount": max_discount(),
                "show_prices": self.request.user.has_perm("catalog.view_reference_price"),
            },
        )

    def get(self, request, pk=None):
        quote = self.get_quote()
        initial = {}
        if quote.pk is None and (cid := request.GET.get("cliente", "")).isdigit():
            initial["customer"] = Party.objects.filter(pk=int(cid)).first()
        form = QuoteForm(instance=quote, initial=initial)
        items = (
            [
                {
                    "product": i.product_id,
                    "quantity": i.quantity,
                    "unit_price": i.unit_price,
                    "discount_pct": i.discount_pct,
                }
                for i in quote.items.all()
            ]
            if quote.pk
            else []
        )
        formset = QuoteItemFormSet(initial=items, prefix="items", form_kwargs={"user": request.user})
        if not items:
            formset.extra = 1
        return self.render_form(form, formset, quote)

    def post(self, request, pk=None):
        quote = self.get_quote()
        form = QuoteForm(request.POST, instance=quote)
        formset = QuoteItemFormSet(request.POST, prefix="items", form_kwargs={"user": request.user})
        if form.is_valid() and formset.is_valid():
            try:
                quote = save_quote(
                    quote=form.save(commit=False), lines=formset.lines, user=request.user, request=request
                )
            except PermissionDenied:
                raise
            messages.success(request, f"Cotización {quote.folio} guardada. Total ${quote.total:,.2f} {quote.currency}.")
            return redirect("quotes:quote_detail", pk=quote.pk)
        return self.render_form(form, formset, quote)


class QuoteManageMixin(PermissionRequiredMixin):
    permission_required = "quotes.change_quote"
    http_method_names = ["post"]

    def get_managed_quote(self, pk):
        quote = get_object_or_404(Quote, pk=pk)
        user = self.request.user
        if quote.owner_id != user.pk and not user.has_perm("quotes.change_any_quote"):
            raise PermissionDenied
        return quote


class QuoteStatusView(QuoteManageMixin, View):
    def post(self, request, pk):
        quote = self.get_managed_quote(pk)
        form = StatusForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Estado no válido.")
            return redirect("quotes:quote_detail", pk=pk)
        try:
            change_status(
                quote=quote,
                new_status=form.cleaned_data["status"],
                user=request.user,
                reason=form.cleaned_data["reason"],
                request=request,
            )
            messages.success(request, "Estado actualizado.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("quotes:quote_detail", pk=pk)


class QuoteFollowUpView(QuoteManageMixin, View):
    def post(self, request, pk):
        quote = self.get_managed_quote(pk)
        form = FollowUpForm(request.POST)
        if form.is_valid():
            follow_up = form.save(commit=False)
            follow_up.quote, follow_up.user = quote, request.user
            follow_up.save()
            log_action(
                AuditLog.Action.UPDATE,
                request=request,
                obj=quote,
                message=f"Seguimiento ({follow_up.get_kind_display()}): {follow_up.notes}"[:255],
            )
            messages.success(request, "Seguimiento registrado.")
        else:
            messages.error(request, "Escribe el comentario del seguimiento.")
        return redirect("quotes:quote_detail", pk=pk)


class QuoteDuplicateView(PermissionRequiredMixin, View):
    permission_required = ["quotes.add_quote", "quotes.view_quote"]
    http_method_names = ["post"]

    def post(self, request, pk):
        original = get_object_or_404(Quote, pk=pk)
        try:
            copy, skipped = duplicate_quote(quote=original, user=request.user, request=request)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
            return redirect("quotes:quote_detail", pk=pk)
        messages.success(request, f"Se creó {copy.folio} como copia de {original.folio}.")
        if skipped:
            messages.warning(request, "Se omitieron partidas de productos inactivos o eliminados.")
        return redirect("quotes:quote_detail", pk=copy.pk)


class QuotePdfView(PermissionRequiredMixin, View):
    permission_required = "quotes.view_quote"

    def get(self, request, pk):
        quote = get_object_or_404(Quote.objects.select_related("customer", "owner"), pk=pk)
        content = quote_pdf(quote)
        log_action(AuditLog.Action.PRINT, request=request, obj=quote, message="PDF de cotización")
        response = HttpResponse(content, content_type="application/pdf")
        disposition = "attachment" if request.GET.get("descargar") else "inline"
        response["Content-Disposition"] = f'{disposition}; filename="{quote.folio}.pdf"'
        return response
