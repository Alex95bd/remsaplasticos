from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)

from core.forms import BootstrapFormMixin

from .models import User
from .roles import role_groups


class RolesField(forms.ModelMultipleChoiceField):
    def __init__(self, **kwargs):
        super().__init__(
            queryset=role_groups(),
            required=False,
            widget=forms.CheckboxSelectMultiple,
            label="Roles",
            help_text="Los permisos de cada rol se describen en docs/roles-y-permisos.md.",
            **kwargs,
        )


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    pass


class UserCreateForm(BootstrapFormMixin, UserCreationForm):
    groups = RolesField()

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "job_title", "phone", "groups", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["groups"].queryset = role_groups()
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True


class UserUpdateForm(BootstrapFormMixin, forms.ModelForm):
    groups = RolesField()

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "job_title", "phone", "groups", "is_active")

    def __init__(self, *args, editor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["groups"].queryset = role_groups()
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        if editor is not None and editor.pk == self.instance.pk:
            # Un usuario no puede cambiar sus propios roles ni desactivarse.
            for name in ("groups", "is_active"):
                self.fields[name].disabled = True
                self.fields[name].help_text = "No puedes modificar este dato en tu propio usuario."


class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone")


class AdminSetPasswordForm(BootstrapFormMixin, SetPasswordForm):
    pass


class StyledPasswordChangeForm(BootstrapFormMixin, PasswordChangeForm):
    pass


class StyledPasswordResetForm(BootstrapFormMixin, PasswordResetForm):
    pass


class StyledSetPasswordForm(BootstrapFormMixin, SetPasswordForm):
    pass
