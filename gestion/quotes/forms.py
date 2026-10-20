from decimal import Decimal

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from catalog.models import Product
from core.forms import BootstrapFormMixin
from crm.models import Party

from .models import Quote, QuoteFollowUp
from .services import validate_line

TAX_CHOICES = [("16", "16 %"), ("8", "8 % (región fronteriza)"), ("0", "0 %")]


class QuoteForm(BootstrapFormMixin, forms.ModelForm):
    tax_rate = forms.TypedChoiceField(label="IVA", choices=TAX_CHOICES, coerce=Decimal)

    class Meta:
        model = Quote
        fields = ["customer", "valid_until", "currency", "tax_rate", "conditions", "notes"]
        widgets = {
            "valid_until": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "conditions": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        customers = Party.objects.filter(is_active=True, party_type__in=["cliente", "ambos"])
        if self.instance.customer_id:
            customers = customers | Party.objects.filter(pk=self.instance.customer_id)
        self.fields["customer"].queryset = customers.order_by("name")
        if not self.instance.pk:
            self.initial.setdefault("tax_rate", str(Decimal(settings.QUOTE_DEFAULT_TAX_RATE).normalize()))
        else:
            self.initial["tax_rate"] = str(self.instance.tax_rate.normalize())

    def clean_valid_until(self):
        value = self.cleaned_data["valid_until"]
        issue = self.instance.issue_date if self.instance.pk else None
        from django.utils import timezone

        if value < (issue or timezone.localdate()):
            raise ValidationError("La vigencia no puede ser anterior a la fecha de la cotización.")
        return value


class QuoteItemForm(BootstrapFormMixin, forms.Form):
    product = forms.ModelChoiceField(label="Producto", queryset=Product.objects.none())
    quantity = forms.DecimalField(label="Cantidad", max_digits=12, decimal_places=3, min_value=Decimal("0.001"))
    unit_price = forms.DecimalField(
        label="Precio unitario",
        max_digits=14,
        decimal_places=4,
        min_value=0,
        required=False,
        help_text="Vacío = precio de lista del cliente o, si no hay, de referencia.",
    )
    discount_pct = forms.DecimalField(
        label="Desc. %", max_digits=5, decimal_places=2, min_value=0, max_value=100, initial=0, required=False
    )

    def __init__(self, *args, user=None, customer=None, currency=None, **kwargs):
        self.user, self.customer, self.currency = user, customer, currency
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.filter(is_active=True).select_related("unit")

    def clean(self):
        data = super().clean()
        product = data.get("product")
        if product is None or data.get("quantity") is None or self.errors:
            return data
        data["discount_pct"] = data.get("discount_pct") or Decimal("0")
        try:
            data["unit_price"] = validate_line(
                self.user,
                product,
                data.get("unit_price"),
                data["discount_pct"],
                customer=self.customer,
                quantity=data["quantity"],
                currency=self.currency,
            )
        except ValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return data


class BaseQuoteItemFormSet(forms.BaseFormSet):
    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        for key in ("user", "customer", "currency"):
            kwargs[key] = self.form_kwargs.get(key)
        return kwargs

    def clean(self):
        if any(self.errors):
            return
        lines = [f.cleaned_data for f in self.forms if f.cleaned_data and not f.cleaned_data.get("DELETE")]
        if not lines:
            raise ValidationError("Agrega al menos una partida.")

    @property
    def lines(self):
        return [f.cleaned_data for f in self.forms if f.cleaned_data and not f.cleaned_data.get("DELETE")]


QuoteItemFormSet = forms.formset_factory(
    QuoteItemForm, formset=BaseQuoteItemFormSet, extra=0, can_delete=True, max_num=200, validate_max=True
)


class FollowUpForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = QuoteFollowUp
        fields = ["kind", "notes", "next_action_date"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
            "next_action_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["kind"].choices = [c for c in QuoteFollowUp.Kind.choices if c[0] != QuoteFollowUp.Kind.STATUS]


class StatusForm(forms.Form):
    status = forms.ChoiceField(choices=Quote.Status.choices)
    reason = forms.CharField(required=False, max_length=1000)
