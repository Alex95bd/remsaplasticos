from decimal import Decimal

from django import forms

from catalog.models import Product
from core.forms import BootstrapFormMixin

from .models import Location, Stock, Warehouse

QTY = {"max_digits": 14, "decimal_places": 3}


def active_products():
    return Product.objects.filter(is_active=True).order_by("sku")


def active_warehouses():
    return Warehouse.objects.filter(is_active=True)


class BaseMovementForm(BootstrapFormMixin, forms.Form):
    product = forms.ModelChoiceField(label="Producto", queryset=Product.objects.none())
    reason = forms.CharField(label="Motivo", max_length=200)
    reference = forms.CharField(
        label="Referencia", max_length=100, required=False, help_text="Factura, pedido, remisión…"
    )
    notes = forms.CharField(label="Observaciones", required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = active_products()
        self.order_fields(["kind", "product", "warehouse", "source", "target", "location", "quantity", "counted"])


class MovementForm(BaseMovementForm):
    kind = forms.ChoiceField(label="Tipo", choices=[("entrada", "Entrada"), ("salida", "Salida")])
    warehouse = forms.ModelChoiceField(label="Almacén", queryset=Warehouse.objects.none())
    location = forms.ModelChoiceField(label="Ubicación", queryset=Location.objects.none(), required=False)
    quantity = forms.DecimalField(label="Cantidad", min_value=Decimal("0.001"), **QTY)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["warehouse"].queryset = active_warehouses()
        self.fields["location"].queryset = Location.objects.filter(is_active=True).select_related("warehouse")

    def clean(self):
        data = super().clean()
        location, warehouse = data.get("location"), data.get("warehouse")
        if location and warehouse and location.warehouse_id != warehouse.pk:
            self.add_error("location", "La ubicación no pertenece al almacén seleccionado.")
        return data


class AdjustmentForm(BaseMovementForm):
    warehouse = forms.ModelChoiceField(label="Almacén", queryset=Warehouse.objects.none())
    counted = forms.DecimalField(label="Existencia física contada", min_value=0, **QTY)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["warehouse"].queryset = active_warehouses()


class TransferForm(BaseMovementForm):
    source = forms.ModelChoiceField(label="Almacén origen", queryset=Warehouse.objects.none())
    target = forms.ModelChoiceField(label="Almacén destino", queryset=Warehouse.objects.none())
    quantity = forms.DecimalField(label="Cantidad", min_value=Decimal("0.001"), **QTY)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["source"].queryset = active_warehouses()
        self.fields["target"].queryset = active_warehouses()

    def clean(self):
        data = super().clean()
        if data.get("source") and data.get("source") == data.get("target"):
            self.add_error("target", "El destino debe ser distinto del origen.")
        return data


class ReverseForm(BootstrapFormMixin, forms.Form):
    reason = forms.CharField(label="Motivo de la cancelación", max_length=200)


class WarehouseForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ["code", "name", "address", "external_code", "is_active"]
        widgets = {"address": forms.Textarea(attrs={"rows": 2})}


class LocationForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Location
        fields = ["code", "description", "is_active"]


class StockSettingsForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Stock
        fields = ["min_quantity", "location"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["location"].queryset = Location.objects.filter(warehouse=self.instance.warehouse, is_active=True)
