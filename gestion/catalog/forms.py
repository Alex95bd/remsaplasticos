from django import forms

from core.forms import BootstrapFormMixin

from .models import Category, Product, UnitOfMeasure, normalize_sku


class ProductForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "sku",
            "name",
            "description",
            "category",
            "product_type",
            "unit",
            "presentation",
            "capacity_ml",
            "height_mm",
            "diameter_mm",
            "weight_g",
            "reference_price",
            "currency",
            "external_code",
            "is_active",
        ]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        current = self.instance if self.instance.pk else None
        self.fields["category"].queryset = Category.objects.filter(is_active=True) | Category.objects.filter(
            pk=getattr(current, "category_id", None)
        )
        self.fields["unit"].queryset = UnitOfMeasure.objects.filter(is_active=True) | UnitOfMeasure.objects.filter(
            pk=getattr(current, "unit_id", None)
        )
        if user is not None and not user.has_perm("catalog.view_reference_price"):
            del self.fields["reference_price"]
            del self.fields["currency"]

    def clean_sku(self):
        return normalize_sku(self.cleaned_data.get("sku"))

    def clean_external_code(self):
        return (self.cleaned_data.get("external_code") or "").strip()


class CategoryForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def clean_name(self):
        return " ".join((self.cleaned_data.get("name") or "").split())


class UnitOfMeasureForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = UnitOfMeasure
        fields = ["code", "name", "is_active"]

    def clean_code(self):
        return (self.cleaned_data.get("code") or "").strip().upper()


class ProductImportForm(BootstrapFormMixin, forms.Form):
    file = forms.FileField(
        label="Archivo de Excel (.xlsx)",
        help_text="Máximo 5 MB. Usa la plantilla para respetar los nombres de columna.",
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx"}),
    )
    update_existing = forms.BooleanField(
        label="Actualizar productos existentes con el mismo SKU",
        required=False,
        help_text="Si no se marca, los SKU que ya existen se reportan como error.",
    )

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        if not uploaded.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("El archivo debe tener extensión .xlsx.")
        if uploaded.size > 5 * 1024 * 1024:
            raise forms.ValidationError("El archivo excede 5 MB.")
        return uploaded
