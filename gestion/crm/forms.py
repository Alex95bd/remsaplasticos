from django import forms

from core.forms import BootstrapFormMixin

from .models import Party


class PartyForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Party
        fields = [
            "party_type",
            "person_type",
            "name",
            "trade_name",
            "rfc",
            "tax_regime",
            "contact_name",
            "contact_position",
            "phone",
            "email",
            "fiscal_address",
            "fiscal_postal_code",
            "commercial_address",
            "payment_terms_days",
            "credit_limit",
            "commercial_conditions",
            "notes",
            "external_code",
            "is_active",
        ]
        widgets = {
            "fiscal_address": forms.Textarea(attrs={"rows": 2}),
            "commercial_address": forms.Textarea(attrs={"rows": 2}),
            "commercial_conditions": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_external_code(self):
        return (self.cleaned_data.get("external_code") or "").strip()
