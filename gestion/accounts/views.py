from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import CreateView, FormView, ListView, UpdateView

from audit.models import AuditLog
from audit.services import log_action
from core.mixins import AuditedModelFormMixin, PermissionRequiredMixin

from .forms import (
    AdminSetPasswordForm,
    LoginForm,
    ProfileForm,
    StyledPasswordChangeForm,
    StyledPasswordResetForm,
    StyledSetPasswordForm,
    UserCreateForm,
    UserUpdateForm,
)
from .models import User
from .roles import ROLE_DESCRIPTIONS, role_groups

USER_AUDIT_FIELDS = ["username", "first_name", "last_name", "email", "job_title", "phone", "groups", "is_active"]


def editable_users(user):
    """Usuarios que ``user`` puede modificar: nadie que no sea superusuario edita a un superusuario."""
    qs = User.objects.all()
    if not user.is_superuser:
        qs = qs.filter(is_superuser=False)
    return qs


class LoginView(auth_views.LoginView):
    template_name = "registration/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class UserListView(PermissionRequiredMixin, ListView):
    permission_required = "accounts.view_user"
    model = User
    paginate_by = 25
    template_name = "accounts/user_list.html"
    context_object_name = "users"

    def get_queryset(self):
        qs = User.objects.prefetch_related(Prefetch("groups", queryset=role_groups()))
        params = self.request.GET
        if q := params.get("q", "").strip():
            qs = qs.filter(
                Q(username__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(email__icontains=q)
            )
        if role := params.get("rol", "").strip():
            qs = qs.filter(groups__name=role)
        estado = params.get("estado", "activos")
        if estado == "activos":
            qs = qs.filter(is_active=True)
        elif estado == "inactivos":
            qs = qs.filter(is_active=False)
        return qs.order_by("username").distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["roles"] = role_groups()
        context["role_descriptions"] = ROLE_DESCRIPTIONS
        context["estado"] = self.request.GET.get("estado", "activos")
        return context


@method_decorator(sensitive_post_parameters("password1", "password2"), name="dispatch")
class UserCreateView(PermissionRequiredMixin, AuditedModelFormMixin, CreateView):
    permission_required = "accounts.add_user"
    model = User
    form_class = UserCreateForm
    template_name = "accounts/user_form.html"
    success_url = reverse_lazy("accounts:user_list")
    success_message = "Usuario creado correctamente."

    def get_audit_fields(self, form):
        return USER_AUDIT_FIELDS


class UserUpdateView(PermissionRequiredMixin, AuditedModelFormMixin, UpdateView):
    permission_required = "accounts.change_user"
    form_class = UserUpdateForm
    template_name = "accounts/user_form.html"
    success_url = reverse_lazy("accounts:user_list")
    success_message = "Usuario actualizado correctamente."
    context_object_name = "target"

    def get_queryset(self):
        return editable_users(self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["editor"] = self.request.user
        return kwargs

    def get_audit_fields(self, form):
        return USER_AUDIT_FIELDS


class UserToggleActiveView(PermissionRequiredMixin, View):
    permission_required = "accounts.change_user"
    http_method_names = ["post"]

    def post(self, request, pk):
        target = get_object_or_404(editable_users(request.user), pk=pk)
        if target.pk == request.user.pk:
            messages.error(request, "No puedes desactivar tu propio usuario.")
            return redirect("accounts:user_list")
        target.is_active = not target.is_active
        target.save(update_fields=["is_active"])
        action = AuditLog.Action.ACTIVATE if target.is_active else AuditLog.Action.DEACTIVATE
        log_action(action, request=request, obj=target)
        messages.success(request, f"Usuario {'activado' if target.is_active else 'desactivado'}: {target}.")
        return redirect("accounts:user_list")


@method_decorator(sensitive_post_parameters("new_password1", "new_password2"), name="dispatch")
class UserSetPasswordView(PermissionRequiredMixin, FormView):
    permission_required = "accounts.change_user"
    form_class = AdminSetPasswordForm
    template_name = "accounts/user_set_password.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.target = get_object_or_404(editable_users(request.user), pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.target
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["target"] = self.target
        return context

    def form_valid(self, form):
        form.save()
        if self.target.pk == self.request.user.pk:
            update_session_auth_hash(self.request, self.target)
        log_action(AuditLog.Action.PASSWORD_SET, request=self.request, obj=self.target)
        messages.success(self.request, f"Contraseña actualizada para {self.target}.")
        return redirect("accounts:user_list")


class ProfileView(AuditedModelFormMixin, UpdateView):
    form_class = ProfileForm
    template_name = "accounts/profile.html"
    success_message = "Tu perfil se actualizó correctamente."

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        return reverse("accounts:profile")


class PasswordChangeView(auth_views.PasswordChangeView):
    form_class = StyledPasswordChangeForm
    template_name = "registration/password_change_form.html"
    success_url = reverse_lazy("accounts:password_change_done")

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(AuditLog.Action.PASSWORD_CHANGE, request=self.request, obj=self.request.user)
        return response


class PasswordResetView(auth_views.PasswordResetView):
    form_class = StyledPasswordResetForm
    template_name = "registration/password_reset_form.html"
    email_template_name = "registration/password_reset_email.txt"
    subject_template_name = "registration/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    form_class = StyledSetPasswordForm
    template_name = "registration/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(AuditLog.Action.PASSWORD_RESET, request=self.request, user=form.user, obj=form.user)
        return response
