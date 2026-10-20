from django import forms


class BootstrapFormMixin:
    """Agrega las clases de Bootstrap 5 a los widgets y marca los campos inválidos."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput | forms.CheckboxSelectMultiple | forms.RadioSelect):
                css = "form-check-input"
            elif isinstance(widget, forms.Select | forms.SelectMultiple):
                css = "form-select"
            else:
                css = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()

    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                widget = self.fields[name].widget
                if "is-invalid" not in widget.attrs.get("class", ""):
                    widget.attrs["class"] = f"{widget.attrs.get('class', '')} is-invalid".strip()
