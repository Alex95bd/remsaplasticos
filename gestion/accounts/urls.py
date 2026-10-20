from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("perfil/", views.ProfileView.as_view(), name="profile"),
    path("contrasena/", views.PasswordChangeView.as_view(), name="password_change"),
    path(
        "contrasena/lista/",
        auth_views.PasswordChangeDoneView.as_view(template_name="registration/password_change_done.html"),
        name="password_change_done",
    ),
    path("recuperar/", views.PasswordResetView.as_view(), name="password_reset"),
    path(
        "recuperar/enviado/",
        auth_views.PasswordResetDoneView.as_view(template_name="registration/password_reset_done.html"),
        name="password_reset_done",
    ),
    path("recuperar/<uidb64>/<token>/", views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path(
        "recuperar/completo/",
        auth_views.PasswordResetCompleteView.as_view(template_name="registration/password_reset_complete.html"),
        name="password_reset_complete",
    ),
    path("usuarios/", views.UserListView.as_view(), name="user_list"),
    path("usuarios/nuevo/", views.UserCreateView.as_view(), name="user_create"),
    path("usuarios/<int:pk>/editar/", views.UserUpdateView.as_view(), name="user_update"),
    path("usuarios/<int:pk>/estado/", views.UserToggleActiveView.as_view(), name="user_toggle_active"),
    path("usuarios/<int:pk>/contrasena/", views.UserSetPasswordView.as_view(), name="user_set_password"),
]
