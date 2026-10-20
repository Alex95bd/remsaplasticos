from decimal import Decimal

from django import forms

from catalog.models import Product
from core.choices import Currency
from core.forms import BootstrapFormMixin
from crm.models import Party

from .models import PriceList

QTY = {"max_digits": 12, "decimal_places": 3}
PRICE = {"max_digits": 14, "decimal_places": 4}


class PriceListForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = PriceList
        fields = ["code", "name", "currency", "customer", "valid_from", "valid_until", "is_active", "notes"]
        widgets = {
            "valid_from": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "valid_until": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = Party.objects.filter(is_active=True, party_type__in=["cliente", "ambos"])


class PriceItemForm(BootstrapFormMixin, forms.Form):
    product = forms.ModelChoiceField(label="Producto", queryset=Product.objects.none())
    min_quantity = forms.DecimalField(label="Cantidad mínima", min_value=0, initial=1, **QTY)
    unit_price = forms.DecimalField(label="Precio unitario", min_value=0, **PRICE)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.filter(is_active=True).select_related("unit")


class DictationForm(BootstrapFormMixin, forms.Form):
    transcript = forms.CharField(
        label="Transcripción o texto",
        max_length=500,
        widget=forms.Textarea(
            attrs={"rows": 3, "placeholder": "Ej.: BOT-500 a 3 pesos con 50 centavos, mínimo mil piezas, lista mayoreo"}
        ),
    )
    source = forms.ChoiceField(choices=[("voz", "voz"), ("texto", "texto")], widget=forms.HiddenInput, initial="texto")


class PriceReviewForm(PriceItemForm):
    """Datos interpretados que la persona revisa y corrige antes de la vista previa."""

    price_list = forms.ModelChoiceField(label="Lista de precios", queryset=PriceList.objects.none())
    currency = forms.ChoiceField(
        label="Moneda dictada", choices=[("", "No mencionada")] + Currency.choices, required=False
    )
    transcript = forms.CharField(widget=forms.HiddenInput, required=False, max_length=500)
    source = forms.ChoiceField(choices=[("voz", "voz"), ("texto", "texto")], widget=forms.HiddenInput)

    field_order = ["price_list", "product", "min_quantity", "unit_price", "currency"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["price_list"].queryset = PriceList.objects.filter(is_active=True)
        self.order_fields(self.field_order)

    def clean(self):
        data = super().clean()
        pl, currency = data.get("price_list"), data.get("currency")
        if pl and currency and currency != pl.currency:
            self.add_error(
                "currency", f"La lista {pl.code} está en {pl.currency}; corrige la moneda o elige otra lista."
            )
        if data.get("unit_price") is not None and data["unit_price"] <= Decimal("0"):
            self.add_error("unit_price", "El precio debe ser mayor que cero.")
        return data
